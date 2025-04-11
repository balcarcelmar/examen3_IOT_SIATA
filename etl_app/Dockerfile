# Usa una imagen base de Python (en este caso, Python 3.9-slim)
FROM python:3.9-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de dependencias e instálalo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el contenido del proyecto al directorio de trabajo en el contenedor
COPY . .

# Define el comando que se ejecutará al iniciar el contenedor (ejecuta el script etl.py)
CMD ["python", "etl.py"]
