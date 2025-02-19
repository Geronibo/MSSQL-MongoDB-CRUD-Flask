from flask import Flask, render_template, request, jsonify
import pyodbc
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

# 📌 MSSQL Bağlantı Ayarları
MSSQL_CONFIG = {
    "server": "IBO\\SQLEXPRESS",
    "database": "ibo",
    "driver": "ODBC Driver 17 for SQL Server"
}

# 📌 MongoDB Bağlantısı
MONGO_URI = "mongodb://localhost:27017/"
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["veriler"]
mongo_collection = mongo_db["employee"]

# 📌 MSSQL Bağlantısı Alma
def get_mssql_connection():
    conn_str = f"DRIVER={MSSQL_CONFIG['driver']};SERVER={MSSQL_CONFIG['server']};DATABASE={MSSQL_CONFIG['database']};Trusted_Connection=yes;"
    return pyodbc.connect(conn_str)

# 📌 Eğer deneme_table1 yoksa oluştur
def create_mssql_table():
    conn = get_mssql_connection()
    cursor = conn.cursor()
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'deneme_table1')
        BEGIN
            CREATE TABLE deneme_table1 (
                user_id INT IDENTITY(1,1) PRIMARY KEY,
                ad NVARCHAR(50),
                soyad NVARCHAR(50),
                mail NVARCHAR(100),
                telno NVARCHAR(20)
            );
        END
    """)
    conn.commit()
    conn.close()

# 📌 Ana Sayfa (Verileri Listeleme)
@app.route("/")
def index():
    try:
        create_mssql_table()

        # MSSQL Verilerini Getir
        conn = get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, ad, soyad, mail, telno FROM deneme_table1")
        columns = [column[0] for column in cursor.description]
        mssql_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()

        # MongoDB Verilerini Getir
        mongodb_rows = list(mongo_collection.find({}, {"_id": 1, "name": 1, "email": 1, "phone": 1}))
        for row in mongodb_rows:
            row["_id"] = str(row["_id"])  # _id'yi string yap

        return render_template("index.html", mssql_rows=mssql_rows, mongodb_rows=mongodb_rows)
    except Exception as e:
        return f"Bağlantı hatası: {e}"

# 📌 Veri Güncelleme
@app.route("/update", methods=["POST"])
def update_data():
    data = request.json
    row_id, column, value, db_type = data.get("id"), data.get("column"), data.get("value"), data.get("db")

    if db_type == "mssql":
        try:
            conn = get_mssql_connection()
            cursor = conn.cursor()
            cursor.execute(f"UPDATE deneme_table1 SET {column} = ? WHERE user_id = ?", (value, int(row_id)))
            conn.commit()
            conn.close()
            return jsonify({"message": "MSSQL güncellendi"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif db_type == "mongodb":
        try:
            mongo_collection.update_one({"_id": ObjectId(row_id)}, {"$set": {column: value}})
            return jsonify({"message": "MongoDB güncellendi"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# 📌 MSSQL Kullanıcı Ekleme
@app.route("/add_mssql", methods=["POST"])
def add_mssql_user():
    data = request.json
    ad, soyad, email, telno = data.get("ad"), data.get("soyad"), data.get("email"), data.get("telno")

    try:
        conn = get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM deneme_table1 WHERE mail = ? OR telno = ?", (email, telno))
        if cursor.fetchone()[0] > 0:
            return jsonify({"message": "Bu Kullanici Zaten Mevcut"}), 400
        
        cursor.execute("INSERT INTO deneme_table1 (ad, soyad, mail, telno) VALUES (?, ?, ?, ?)", (ad, soyad, email, telno))
        conn.commit()
        conn.close()
        return jsonify({"message": "MSSQL Kullanıcı Eklendi"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 MongoDB Kullanıcı Ekleme
@app.route("/add_mongodb", methods=["POST"])
def add_mongodb_user():
    data = request.json
    name, email, phone = data.get("name"), data.get("email"), data.get("phone")

    try:
        if mongo_collection.find_one({"$or": [{"email": email}, {"phone": phone}]}):
            return jsonify({"message": "Bu Kullanici Zaten Mevcut"}), 400
        
        mongo_collection.insert_one({"name": name, "email": email, "phone": phone})
        return jsonify({"message": "MongoDB Kullanıcı Eklendi"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 MSSQL Kullanıcı Silme
@app.route("/delete_mssql", methods=["POST"])
def delete_mssql_user():
    data = request.json
    user_id = data.get("user_id")

    try:
        conn = get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM deneme_table1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "MSSQL Kullanıcı Silindi"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500   

# 📌 MongoDB Kullanıcı Silme
@app.route("/delete_mongodb", methods=["POST"])
def delete_mongodb_user():
    data = request.json
    user_id = data.get("_id")

    try:
        mongo_collection.delete_one({"_id": ObjectId(user_id)})
        return jsonify({"message": "MongoDB Kullanıcı Silindi"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Uygulama Çalıştırma
if __name__ == "__main__":
    app.run(debug=True)
