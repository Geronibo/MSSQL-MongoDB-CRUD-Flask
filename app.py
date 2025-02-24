from flask import Flask, render_template, request, redirect, url_for, session,jsonify
import pyodbc
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Oturum yönetimi için gerekli
mssql_conn = None
mongo_collection = None

# 📌 MSSQL Bağlantısı Alma (Kullanıcıdan alınan bilgilerle)
def get_mssql_connection(server, database, username, password):
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=yes;"
    return pyodbc.connect(conn_str)

def init_mongo():
    # MongoDB'ye ilk bağlantı
   global mongo_collection
   try:
        musername = session.get("musername")
        mpassword = session.get("mpassword")
        mdatabase = session.get("mdatabase")

        # MongoDB bağlantı dizesini oluştur
        mongo_uri = f"mongodb://{musername}:{mpassword}@localhost:27017/{mdatabase}"
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client[mdatabase]
        
        # MongoDB koleksiyonuna bağlan
        mongo_collection = mongo_db["employee"]  # Koleksiyona bağlantı

   except Exception as e:
        print(f"MongoDB Bağlantı Hatası: {e}")

@app.route("/", methods=["GET", "POST"])
def first_page():
    return redirect(url_for("login"))

# 📌 Kullanıcı giriş kontrolü ve MSSQL bilgilerini alma
@app.route("/login", methods=["GET", "POST"])
def login():
    global mssql_conn  # Global değişkeni kullanıyoruz
    if request.method == "POST":
        # MSSQL Bağlantı Bilgileri
        server = request.form["server"]
        database = request.form["database"]
        username = request.form["username"]
        password = request.form["password"]
        
        # MongoDB Bağlantı Bilgileri
        musername = request.form["musername"]
        mpassword = request.form["mpassword"]
        mdatabase = request.form["mdatabase"]
        
        try:
            # MSSQL bağlantısını kuruyoruz
            mssql_conn = get_mssql_connection(server, database, username, password)
            cursor = mssql_conn.cursor()
            cursor.execute("SELECT 1")  # Bağlantıyı test et

            # MongoDB bağlantısını başlat
            session["musername"] = musername
            session["mpassword"] = mpassword
            session["mdatabase"] = mdatabase
            init_mongo()  # MongoDB'yi başlat

            # Bağlantı başarılı, oturum bilgilerini sakla
            session["server"] = server
            session["database"] = database
            session["username"] = username
            session["password"] = password

            # Kullanıcıyı ana sayfaya yönlendir
            return redirect(url_for("index"))
        except Exception as e:
            return render_template("login.html", error=f"Bağlantı hatası: {e}")
    
    return render_template("login.html")


# 📌 Eğer deneme_table1 yoksa oluştur
def create_mssql_table():
    cursor = mssql_conn.cursor()
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
    mssql_conn.commit()
    

# 📌 Ana Sayfa (Verileri Listeleme)
@app.route("/index")
def index():
    try:
        create_mssql_table()
        cursor = mssql_conn.cursor()
        cursor.execute("SELECT user_id, ad, soyad, mail, telno FROM deneme_table1")
        columns = [column[0] for column in cursor.description]
        mssql_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        

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
            cursor = mssql_conn.cursor()
            cursor.execute(f"UPDATE deneme_table1 SET {column} = ? WHERE user_id = ?", (value, int(row_id)))
            mssql_conn.commit()
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
       
        cursor = mssql_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM deneme_table1 WHERE mail = ? OR telno = ?", (email, telno))
        if cursor.fetchone()[0] > 0:
            return jsonify({"message": "Bu Kullanici Zaten Mevcut"}), 400
        
        cursor.execute("INSERT INTO deneme_table1 (ad, soyad, mail, telno) VALUES (?, ?, ?, ?)", (ad, soyad, email, telno))
        mssql_conn.commit()
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
       
        cursor = mssql_conn.cursor()
        cursor.execute("DELETE FROM deneme_table1 WHERE user_id = ?", (user_id,))
        mssql_conn.commit()
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

