import requests
import os
from pymongo import MongoClient


url = "https://siata.gov.co/EntregaData1/Datos_SIATA_Aire_AQ_pm25_Last.json"
os.environ['MONGO_URI'] = "mongodb+srv://balcarcelmar:20051413Mar@siatadatos.rkyypad.mongodb.net/datos_siata?retryWrites=true&w=majority&appName=SIATAdatos"


def extraer_datos(url):
    """
    Realiza una petición GET a la URL y retorna la respuesta en formato JSON.
    """
    respuesta = requests.get(url)
    respuesta.raise_for_status()  # Lanza un error si ocurre algo en la petición
    datos = respuesta.json()
    return datos

def limpiar_datos(datos):
    """
    Aplica calidad y limpieza a los datos:
      - Se espera que 'datos' sea un diccionario con una clave 'measurements'.
      - Se eliminan las claves 'sourceType' y 'mobile' de cada registro.
      - Se filtran los registros con 'value' igual a -9999 (indicando dato inválido).
    Retorna una lista de registros limpios.
    """
    measurements = datos.get("measurements", [])
    registros_limpios = []

    for registro in measurements:
        # Elimina la clave 'sourceType' si existe (la clave puede diferir en mayúsculas/minúsculas según la estructura)
        registro.pop("sourceType", None)
        # Elimina la clave 'mobile'
        registro.pop("mobile", None)

        # Filtra aquellos registros donde el valor es -9999 (dato inválido)
        if "value" in registro and registro["value"] == -9999:
            continue

        registros_limpios.append(registro)

    return registros_limpios

def cargar_datos(documentos):
    """
    Conecta a MongoDB usando la variable de entorno MONGO_URI y carga los documentos en la colección 'datos_siata'.
    """
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise Exception("La variable de entorno MONGO_URI no está definida.")

    # Conecta a MongoDB
    client = MongoClient(mongo_uri)
    # Se accede a la base de datos definida en la cadena de conexión
    db = client.get_database()
    # Selecciona (o crea) la colección 'datos_siata'
    coleccion = db['datos_siata']

    # Limpia la colección antes de insertar nuevos datos (opcional)
    coleccion.delete_many({})

    # Inserta los documentos limpios
    coleccion.insert_many(documentos)
    print("Carga completada.")

if __name__ == "__main__":
    try:
        # Paso 1: Extraer datos
        datos_crudos = extraer_datos(url)
        print("Datos extraídos con éxito. Estructura:", type(datos_crudos))

        # Paso 2: Limpiar datos (aplica calidad eliminando 'sourceType' y 'mobile', y filtra registros inválidos)
        documentos_limpios = limpiar_datos(datos_crudos)
        print(f"Total de registros limpios: {len(documentos_limpios)}")

        # Paso 3: Cargar los datos limpios en MongoDB
        cargar_datos(documentos_limpios)
        print("Proceso ETL finalizado con calidad y limpieza aplicadas.")

    except Exception as e:
        print("Ocurrió un error durante el proceso ETL:", e)

