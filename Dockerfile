# Python imajını kullan
FROM python:3.11.2

# Gerekli bağımlılıkları yükle
RUN apt-get update && apt-get install -y \
    unixodbc \
    unixodbc-dev \
    odbcinst \
    curl \
    gnupg \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17

# Çalışma dizinini ayarla
WORKDIR /app

# Gerekli Python paketlerini yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Flask uygulamasını kopyala
COPY . .

# Uygulamayı başlat
CMD ["python", "ibo.py"]
