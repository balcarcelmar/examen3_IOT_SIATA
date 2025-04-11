# Usa una imagen oficial de Python
FROM python:3.10

# Establece el directorio de trabajo
WORKDIR /app

# Copia todos los archivos del proyecto al contenedor
COPY . /app

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto que usará Streamlit
EXPOSE 8501

# Comando para iniciar la app de Streamlit
CMD ["streamlit", "run", "visualizacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
