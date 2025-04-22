import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from dotenv import load_dotenv

# Cargar variables de entorno (buscará .env en el directorio actual o superior)
# Asegúrate de que .env esté en la raíz del proyecto (prueba-tecnica-rpa)
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "banco_movimientos") # Nombre de BD por defecto
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "movimientos") # Nombre de colección por defecto

client = None
db = None

def connect_db():
    """Establece la conexión con MongoDB usando la URI del .env."""
    global client, db
    if not MONGO_URI:
        print("Error: La variable de entorno MONGO_URI no está definida en .env")
        return False
        
    if client is None:
        print(f"Conectando a MongoDB (DB: {DB_NAME})...")
        try:
            client = MongoClient(MONGO_URI)
            # The ismaster command is cheap and does not require auth.
            client.admin.command('ismaster') 
            db = client[DB_NAME]
            print("Conexión a MongoDB establecida exitosamente.")
            return True
        except ConnectionFailure as e:
            print(f"Error de conexión a MongoDB: {e}")
            client = None
            db = None
            return False
        except Exception as e:
            print(f"Error inesperado al conectar a MongoDB: {e}")
            client = None
            db = None
            return False
    else:
        # Ya conectado
        return True

def save_movements(movements_list):
    """
    Guarda una lista de movimientos en la colección de MongoDB.
    Args:
        movements_list (list): Lista de diccionarios, donde cada diccionario es un movimiento.
    Returns:
        bool: True si la inserción fue exitosa, False en caso contrario.
    """
    global db
    if db is None:
        print("Error: No hay conexión a la base de datos. Llama a connect_db() primero.")
        if not connect_db(): # Intenta reconectar
             return False

    if not movements_list:
        print("Advertencia: La lista de movimientos está vacía. No se insertará nada.")
        return True # Considerar True ya que no hubo error de BD

    collection = db[COLLECTION_NAME]
    print(f"Insertando {len(movements_list)} documentos en la colección '{COLLECTION_NAME}'...")
    
    try:
        result = collection.insert_many(movements_list)
        print(f"Inserción completada. IDs de los documentos insertados: {result.inserted_ids}")
        return True
    except OperationFailure as e:
        print(f"Error de operación al insertar en MongoDB: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado al insertar en MongoDB: {e}")
        return False

def close_db_connection():
    """Cierra la conexión a MongoDB si está abierta."""
    global client, db
    if client:
        print("Cerrando conexión a MongoDB...")
        client.close()
        client = None
        db = None
        print("Conexión a MongoDB cerrada.")

# Ejemplo de uso (opcional, para pruebas)
if __name__ == '__main__':
    print("Probando conexión a la base de datos...")
    if connect_db():
        print("\nProbando inserción...")
        # Datos de ejemplo
        test_data = [
            {'fecha': '01/04/2024', 'descripcion': 'Transferencia recibida', 'monto': 50000.0},
            {'fecha': '02/04/2024', 'descripcion': 'Compra con tarjeta', 'monto': -15000.0}
        ]
        if save_movements(test_data):
            print("\nPrueba de inserción exitosa.")
        else:
            print("\nPrueba de inserción fallida.")
        
        close_db_connection()
    else:
        print("No se pudo establecer la conexión para la prueba.") 