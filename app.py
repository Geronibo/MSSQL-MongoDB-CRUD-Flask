from flask import Flask, render_template, request, jsonify
import pyodbc
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

# 📌 MSSQL Bağlantısı
MSSQL_CONFIG = {
    "server": "IBO\\SQLEXPRESS",
    "database": "ibo",
    "driver": "ODBC Driver 17 for SQL Server"
}
#deneme 

def get_mssql_connection():
    conn_str = f"DRIVER={MSSQL_CONFIG['driver']};SERVER={MSSQL_CONFIG['server']};DATABASE={MSSQL_CONFIG['database']};Trusted_Connection=yes;"
    return pyodbc.connect(conn_str)

# 📌 MongoDB Bağlantısı
MONGO_URI = "mongodb://localhost:27017/"
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["veriler"]
mongo_collection = mongo_db["employee"]

# 📌 Ana Sayfa: MSSQL ve MongoDB verilerini getir
@app.route("/")
def index():
    try:
        # MSSQL'den veri çek
        conn = get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, ad, soyad, mail, telno FROM deneme_table1")  # ID'yi sadece backend'de tutuyoruz
        columns = [column[0] for column in cursor.description]
        mssql_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()

        # MongoDB'den veri çek (_id hariç diğer alanlar)
        mongodb_rows = list(mongo_collection.find({}, {"_id": 1, "name": 1, "email": 1, "phone": 1}))
        for row in mongodb_rows:
            row["_id"] = str(row["_id"])  # _id'yi string yap

        return render_template("index.html", mssql_rows=mssql_rows, mongodb_rows=mongodb_rows)
    except Exception as e:
        return f"Bağlantı hatası: {e}"

# 📌 AJAX ile veri güncelleme
@app.route("/update", methods=["POST"])
def update_data():
    data = request.json
    row_id = data.get("id")
    column = data.get("column")
    value = data.get("value")
    db_type = data.get("db")

    if db_type == "mssql":
        try:
            if not str(row_id).isdigit():
                return jsonify({"error": "MSSQL için geçersiz ID formatı"}), 400

            conn = get_mssql_connection()
            cursor = conn.cursor()
            query = f"UPDATE deneme_table1 SET {column} = ? WHERE user_id = ?"  
            cursor.execute(query, (value, int(row_id)))  
            conn.commit()
            conn.close()
            return jsonify({"message": "MSSQL güncellendi"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif db_type == "mongodb":
        try:
            mongo_collection.update_one(
                {"_id": ObjectId(row_id)},  
                {"$set": {column: value}}
            )
            return jsonify({"message": "MongoDB güncellendi"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
@app.route("/add_mssql", methods=["POST"])
def add_mssql_user():
    data = request.json
    ad = data.get("ad")
    soyad = data.get("soyad")
    email = data.get("email")
    telno = data.get("telno")
    
    try:
        conn = get_mssql_connection()
        cursor = conn.cursor()

        # 📌 Aynı e-posta veya telefon var mı kontrol et
        cursor.execute("SELECT COUNT(*) FROM deneme_table1 WHERE mail = ? OR telno = ?", (email, telno))
        count = cursor.fetchone()[0]

        if count > 0:
            return jsonify({"message": "Bu Kullanici Zaten Mevcut"}), 400
        
        # 📌 Kullanıcıyı ekle
        cursor.execute("INSERT INTO deneme_table1 (ad, soyad, mail, telno) VALUES (?, ?, ?, ?)", (ad, soyad, email, telno))
        conn.commit()
        conn.close()
        return jsonify({"message": "MSSQL Kullanıcı Eklendi"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/add_mongodb", methods=["POST"])
def add_mongodb_user():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    
    try:
        # 📌 Aynı e-posta veya telefon numarası olup olmadığını kontrol et
        existing_user = mongo_collection.find_one({"$or": [{"email": email}, {"phone": phone}]})
        
        if existing_user:
            return jsonify({"message": "Bu Kullanici Zaten Mevcut"}), 400
        
        # 📌 Kullanıcıyı ekle
        mongo_collection.insert_one({"name": name, "email": email, "phone": phone})
        return jsonify({"message": "MongoDB Kullanıcı Eklendi"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/delete_mssql", methods=["POST"])
def delete_mssql_user():
    data = request.json
    user_id = data.get("user_id")
    
    try:
        conn = get_mssql_connection()
        cursor = conn.cursor()
        # MSSQL'de kullanıcının user_id'sine göre silme işlemi yapılıyor
        cursor.execute("DELETE FROM deneme_table1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "MSSQL Kullanıcı Silindi"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500   
        
@app.route("/delete_mongodb", methods=["POST"])
def delete_mongodb_user():
    data = request.json
    user_id = data.get("_id")
    
    
    try:
        # Delete the user from MongoDB by _id
        mongo_collection.delete_one({"_id": ObjectId(user_id)})
        return jsonify({"message": "MongoDB Kullanıcı Silindi"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
