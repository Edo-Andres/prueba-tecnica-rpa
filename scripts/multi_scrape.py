import argparse
import sys
import os
from datetime import datetime
from dotenv import load_dotenv # Importar load_dotenv

# Ajustar la ruta para importar desde app y webdriver
# Esto asume que ejecutas el script desde la raíz del proyecto (ej. python scripts/multi_scrape.py)
# Si lo ejecutas desde dentro de scripts/, necesitarás ajustar la ruta de forma diferente.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.banco_estado_scraper import BancoEstadoScraper
# Importar el gestor de BD 
from app.utils.database_manager import save_movements, connect_db, close_db_connection

# Cargar variables de entorno desde .env
load_dotenv()

def parse_date_range(date_range_str):
    """Parsea el string 'YYYY-MM-DD:YYYY-MM-DD' a fechas inicio y fin en formato ddmmyyyy."""
    try:
        since_str, until_str = date_range_str.split(':')
        # Convertir a objeto datetime para validar y luego al formato requerido (ddmmyyyy)
        since_dt = datetime.strptime(since_str, '%Y-%m-%d')
        until_dt = datetime.strptime(until_str, '%Y-%m-%d')
        
        # Validar que since_dt no sea posterior a until_dt (opcional pero recomendado)
        if since_dt > until_dt:
            raise ValueError("La fecha 'since' no puede ser posterior a la fecha 'until'.")
            
        # Formatear a ddmmyyyy para el scraper
        since_formatted = since_dt.strftime('%d%m%Y')
        until_formatted = until_dt.strftime('%d%m%Y')
        
        return since_formatted, until_formatted
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Formato de fecha inválido ({date_range_str}). Use 'YYYY-MM-DD:YYYY-MM-DD'. Detalles: {e}")
    except Exception as e:
         raise argparse.ArgumentTypeError(f"Error procesando el rango de fechas: {e}")

def main():
    parser = argparse.ArgumentParser(description='Scraper de movimientos bancarios para Banco Estado.')
    parser.add_argument('--date-range', required=True, type=parse_date_range, 
                        help="Rango de fechas para buscar movimientos. Formato: 'YYYY-MM-DD:YYYY-MM-DD'")
    # Hacer argumentos de credenciales opcionales
    parser.add_argument('--username', help='RUT del usuario (sin puntos ni guion). Si no se provee, se lee de RUT en .env')
    parser.add_argument('--password', help='Clave de acceso del usuario. Si no se provee, se lee de CLAVE en .env')
    parser.add_argument('--account', help='Número de cuenta (opcional, no usado actualmente por BancoEstadoScraper)')
    # Podríamos añadir argumento para la URI de MongoDB o leerla de .env

    args = parser.parse_args()

    # --- Obtener credenciales --- 
    username = args.username
    password = args.password

    if not username:
        username = os.getenv('RUT')
        if username:
            print("Username (RUT) leído desde el archivo .env")
        else:
            parser.error("El argumento --username es requerido si RUT no está definido en .env")
            
    if not password:
        password = os.getenv('CLAVE')
        if password:
            print("Password (CLAVE) leído desde el archivo .env")
        else:
             parser.error("El argumento --password es requerido si CLAVE no está definido en .env")
    # ---------------------------

    # Extraer fechas formateadas del resultado del parseo
    since_date, until_date = args.date_range 

    print(f'------------------ RUN START ------------------')
    print(f"Usuario: {username}") # Usar la variable obtenida
    print(f"Rango de fechas: {since_date} - {until_date}")
    print(f"Cuenta: {args.account if args.account else 'No especificada'}")
    
    # Crear instancia del scraper con las credenciales obtenidas
    scraper = BancoEstadoScraper(username=username, password=password, account=args.account)
    
    movements = []
    login_successful = False
    # db_connected = False # Comentado temporalmente para pruebas de scraper
    
    try:
        # Conectar a la BD al inicio (Comentado temporalmente)
        # db_connected = connect_db()
        # if not db_connected:
        #      print("Error crítico: No se pudo conectar a la base de datos. Abortando.")
        #      return 
             
        login_successful = scraper.login()

        if login_successful:
            print("Login exitoso, procediendo a extraer movimientos...")
            movements = scraper.extract_movements(since_date, until_date)
            
            if movements:
                print(f"Se extrajeron {len(movements)} movimientos.")
                # --- Guardar en la base de datos (Comentado temporalmente) ---
                # print("Guardando movimientos en la base de datos...")
                # try:
                #     if save_movements(movements):
                #         print("Movimientos guardados exitosamente en MongoDB.")
                #     else:
                #          print("Fallo al guardar movimientos en MongoDB.")
                # except Exception as db_error:
                #     print(f"Error al guardar en MongoDB: {db_error}")
                # ------------------------------------
                # Imprimir movimientos en consola para depuración
                print("--- Movimientos Extraídos (para depuración) ---")
                for mov in movements:
                    print(mov)
                print("---------------------------------------------")
            else:
                print("No se encontraron movimientos para el rango especificado o ocurrió un error durante la extracción.")
                
        else:
            print("El login falló. Revisa las credenciales o el estado de la página del banco.")

    except Exception as e:
        print(f"Ocurrió un error general durante la ejecución: {e}")
    finally:
        if scraper:
            scraper.close()
        # Cerrar conexión a BD si se estableció (Comentado temporalmente)
        # if db_connected:
        #     close_db_connection()
            
    print(f'------------------ RUN ENDED ------------------\n')

if __name__ == '__main__':
    main()
