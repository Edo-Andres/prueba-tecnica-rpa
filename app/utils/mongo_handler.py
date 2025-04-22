import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from dotenv import load_dotenv

# Cargar variables de entorno (buscará .env en niveles superiores si es necesario)
# Asume que .env está en la raíz del proyecto (prueba-tecnica-rpa)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Variables de entorno cargadas desde: {dotenv_path}")
else:
    # Si no está en la raíz, intentar cargar desde el directorio actual o superior (comportamiento por defecto de load_dotenv)
    load_dotenv() 
    print("Intentando cargar variables de entorno desde ubicación por defecto.")


# Configuración de MongoDB - Prioriza .env, luego usa valores por defecto
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'banco_estado_db')
MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', 'movimientos_cuenta')

_client = None

def get_mongo_client():
    """Obtiene una instancia del cliente de MongoDB, reutilizando si ya existe."""
    global _client
    if _client is None:
        try:
            print(f"Conectando a MongoDB en: {MONGO_URI}")
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) # Timeout de 5 segundos
            # Forzar la conexión para verificar que funciona.
            _client.admin.command('ping') 
            print("Conexión a MongoDB exitosa.")
        except ConnectionFailure as e:
            print(f"Error: No se pudo conectar a MongoDB en {MONGO_URI}. Verifica que MongoDB esté corriendo.")
            print(f"Detalle del error: {e}")
            _client = None # Asegurar que no se reutilice un cliente fallido
        except Exception as e:
            print(f"Error inesperado al conectar a MongoDB: {e}")
            _client = None
    return _client

def close_mongo_client():
    """Cierra la conexión global del cliente MongoDB si está abierta."""
    global _client
    if _client:
        print("Cerrando conexión a MongoDB.")
        _client.close()
        _client = None

def save_movements(movements_list: list):
    """
    Guarda una lista de diccionarios de movimientos en la colección de MongoDB.

    Args:
        movements_list (list): Lista de diccionarios, donde cada diccionario representa un movimiento.
    """
    if not movements_list:
        print("No hay movimientos para guardar en MongoDB.")
        return False

    client = get_mongo_client()
    if not client:
        print("Error: No se pudo obtener el cliente de MongoDB. No se guardarán los movimientos.")
        return False

    try:
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION]
        
        print(f"Insertando {len(movements_list)} movimientos en la colección '{MONGO_DB_NAME}.{MONGO_COLLECTION}'...")
        result = collection.insert_many(movements_list)
        print(f"Inserción completada. {len(result.inserted_ids)} documentos insertados.")
        # No cerramos el cliente aquí para permitir reutilización en ejecuciones futuras del scraper
        # La conexión se cerrará explícitamente si es necesario o al finalizar la aplicación principal
        return True
        
    except OperationFailure as e:
        print(f"Error de operación al insertar en MongoDB: {e}")
        # Podría ser un problema de permisos, estructura de datos, etc.
        # close_mongo_client() # Considerar cerrar si el error es grave
        return False
    except Exception as e:
        print(f"Error inesperado al guardar movimientos en MongoDB: {e}")
        # close_mongo_client() # Considerar cerrar si el error es grave
        return False

# Ejemplo de uso (opcional, para pruebas)
# if __name__ == '__main__':
#     test_movements = [
#         {'fecha': '2024-01-15', 'descripcion': 'Test 1', 'monto': -100.0},
#         {'fecha': '2024-01-16', 'descripcion': 'Test 2', 'monto': 250.5},
#     ]
#     if save_movements(test_movements):
#         print("Guardado de prueba exitoso.")
#     else:
#         print("Guardado de prueba fallido.")
#     close_mongo_client() # Cerrar cliente después de la prueba 