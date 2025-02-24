FROM python:3.11

# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    gnupg2 \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/10/prod.list | tee /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get install -y unixodbc-dev

# Çalışma dizinini ayarla
WORKDIR /app

# Uygulama dosyalarını kopyala
COPY . /app

# Gerekli Python paketlerini yükle
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Uygulamayı başlat
EXPOSE 5000
CMD ["python", "app.py"]
