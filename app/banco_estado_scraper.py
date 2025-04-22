import time
import random
import os
import glob
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from webdriver.scraper_base import ScraperBase
import undetected_chromedriver as uc # Añadir import para uc
from .utils.mongo_handler import save_movements, close_mongo_client # Importar funciones de MongoDB
# Se necesitará instalar pandas si no está: pip install pandas
# import pandas as pd # O procesar los datos manualmente

# Definir directorio de descargas consistente con driver_factory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "downloads")

class BancoEstadoScraper(ScraperBase):
    """
    Scraper para Banco Estado que realiza login y extrae movimientos.
    Hereda de ScraperBase para utilizar sus funcionalidades de manejo de driver y esperas.
    """
    LOGIN_URL = 'https://nwm.bancoestado.cl/content/bancoestado-public/cl/es/home/home.html#/'
    # Selectores (pueden necesitar ajustes)
    BANCA_EN_LINEA_BTN_XPATH = "//span[contains(@class, 'cmp-button__text') and text()='Banca en Línea']"
    RUT_INPUT_ID = 'rut'
    PASS_INPUT_ID = 'pass'
    LOGIN_BTN_ID = 'btnLogin'
    # Selector para validar login exitoso (ej. botón de saldos o nombre de usuario)
    # Ajustar este selector a un elemento fiable que solo aparezca post-login
    POST_LOGIN_VALIDATION_XPATH = "//button[contains(@class, 'ver-detalle') and contains(@aria-label, 'Ver movimientos')]" 
    SALDOS_MOVS_BTN_XPATH = "//button[contains(@class, 'ver-detalle') and contains(@aria-label, 'Ver movimientos')]"
    BUSCAR_FECHAS_XPATH = "//span[contains(@class, 'only_desktop') and text()='Buscar por fechas']"
    FECHA_DESDE_ID = 'date_from'
    FECHA_HASTA_ID = 'hasta'
    BUSCAR_BTN_XPATH = "//button[contains(@class, 'search_btn') and contains(., 'Buscar')]"
    # --- Selectores para Descarga (adaptados de v3) ---
    # Intentar con selectores más robustos si estos fallan
    DESCARGAR_DROPDOWN_BTN_XPATH = "//*[@id='tab_panel0']//msd-download-dropdown//button" # XPath más general para el botón dropdown
    # DESCARGAR_DROPDOWN_BTN_XPATH = "//*[@id='tab_panel0']/msd-tab[1]/div/app-movimiento-detalle/app-listado-movimientos/msd-data-table-mambu/div/div[3]/div[1]/msd-download-dropdown/div/button" # XPath específico de v3
    DESCARGAR_EXCEL_OPTION_XPATH = "//li[@role='button' and contains(., 'Descargar Excel')]"
    # --- Fin Selectores Descarga ---
    DOWNLOAD_DIR = DOWNLOAD_DIR # Hacer accesible la constante de clase como atributo de instancia

    def __init__(self, username, password, account=None):
        """
        Inicializa el scraper con las credenciales.
        Args:
            username (str): RUT del usuario (sin puntos ni guion).
            password (str): Clave del usuario.
            account (str, optional): Número de cuenta (actualmente no usado para B.Estado). Defaults to None.
        """
        super().__init__() # Llama al init de ScraperBase si lo tuviera
        self.username = username
        self.password = password
        self.account = account
        # El driver se inicializará en login() ahora
        # print(f"BancoEstadoScraper inicializado para RUT: {username}")
        # self._clear_download_dir() # Mover limpieza a justo antes de la descarga si es necesario

    def _human_type(self, element, text):
        """Simula escritura humana."""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))

    def _clear_download_dir(self):
        """Elimina archivos .xlsx previos del directorio de descargas."""
        print(f"Limpiando archivos .xlsx de: {DOWNLOAD_DIR}")
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx"))
        files.extend(glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload"))) # Incluir descargas parciales
        for f in files:
            try:
                os.remove(f)
                print(f"  Eliminado: {os.path.basename(f)}")
            except OSError as e:
                print(f"Error eliminando {f}: {e}")

    def _wait_for_download(self, timeout=60):
        """Espera a que un archivo .xlsx aparezca en el directorio de descargas."""
        print(f"Esperando descarga de archivo .xlsx en {DOWNLOAD_DIR} (timeout={timeout}s)")
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Buscar archivos .xlsx que NO sean temporales
            xlsx_files = [f for f in glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx")) 
                          if not f.endswith('.tmp') and not f.endswith('.crdownload')]
            if xlsx_files:
                # Devolver el archivo más reciente (asumiendo uno por descarga)
                latest_file = max(xlsx_files, key=os.path.getctime)
                print(f"Archivo descargado detectado: {os.path.basename(latest_file)}")
                # Espera breve adicional para asegurar que la escritura haya finalizado
                time.sleep(2) 
                return latest_file
            # Esperar un poco antes de volver a comprobar
            time.sleep(1) 
        print("Error: Timeout esperando la descarga del archivo Excel.")
        return None

    def login(self):
        """
        Realiza el proceso de login en Banco Estado inicializando el driver directamente.
        Returns:
            bool: True si el login fue exitoso, False en caso contrario.
        """
        try:
            # Limpiar directorio de descargas antes de iniciar el driver (opcional, puede ir antes de descargar)
            self._clear_download_dir()
            print("Inicializando driver uc.Chrome directamente...")

            # --- Configuración directa del driver ---
            # Asegurarse de que el directorio de descargas exista
            if not os.path.exists(self.DOWNLOAD_DIR):
                print(f"Creando directorio de descargas en: {self.DOWNLOAD_DIR}")
                os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
            else:
                print(f"Directorio de descargas ya existe: {self.DOWNLOAD_DIR}")

            prefs = {
                # Usar el DOWNLOAD_DIR definido a nivel de clase
                "download.default_directory": self.DOWNLOAD_DIR,
                "download.prompt_for_download": False, # No preguntar dónde guardar
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True # O False si causa problemas
            }
            options = uc.ChromeOptions()
            # Añadir opciones mínimas similares a b_estado_v3.py
            options.add_argument("--disable-infobars")
            options.add_argument("--start-maximized") # Reemplaza self.driver.maximize_window() más adelante
            # Considerar añadir --no-sandbox si se ejecuta en ciertos entornos Linux/Docker
            # options.add_argument('--no-sandbox')
            options.add_experimental_option("prefs", prefs)
            print(f"Configurando directorio de descargas en: {self.DOWNLOAD_DIR}")

            # Reemplazar self.get_driver() de ScraperBase
            # self.get_driver() # Ya no se llama a la factory
            self.driver = uc.Chrome(options=options, use_subprocess=True)
            print("Driver uc.Chrome inicializado.")
            # Ya no es necesario maximizar explícitamente si se usa --start-maximized
            # self.driver.maximize_window()

            # --- Resto del proceso de login ---
            print(f"Navegando a: {self.LOGIN_URL}")
            self.driver.get(self.LOGIN_URL)
            time.sleep(random.uniform(1.5, 3.0))

            print("Esperando 'Banca en Línea'...")
            banca_en_linea_btn = self.driver_wait_by_clickable(self.BANCA_EN_LINEA_BTN_XPATH, 'XPATH', time=20)
            time.sleep(random.uniform(0.5, 1.5))
            print("Haciendo clic en 'Banca en Línea'...")
            banca_en_linea_btn.click()
            time.sleep(random.uniform(1.0, 2.5))

            print("Esperando campo RUT...")
            rut_input = self.driver_wait_by_visibility(self.RUT_INPUT_ID, 'ID', time=15)
            time.sleep(random.uniform(0.5, 1.2))
            print("Ingresando RUT...")
            self._human_type(rut_input, self.username)
            time.sleep(random.uniform(0.5, 1.5))

            print("Esperando campo Clave...")
            clave_input = self.driver_wait_by_visibility(self.PASS_INPUT_ID, 'ID', time=10)
            time.sleep(random.uniform(0.3, 0.9))
            print("Ingresando Clave...")
            self._human_type(clave_input, self.password)
            time.sleep(random.uniform(0.8, 2.0))

            print("Esperando botón 'Ingresar'...")
            ingresar_btn = self.driver_wait_by_clickable(self.LOGIN_BTN_ID, 'ID', time=10)
            time.sleep(random.uniform(0.6, 1.8))
            print("Haciendo clic en 'Ingresar'...")
            ingresar_btn.click()

            # Validación post-login
            print("Validando login...")
            try:
                self.driver_wait_by_visibility(self.POST_LOGIN_VALIDATION_XPATH, 'XPATH', time=30) # Espera más larga post-login
                print("Login exitoso.")
                return True
            except TimeoutException:
                print("Error: No se pudo validar el login (elemento post-login no encontrado). Verifica credenciales o el selector de validación.")
                # No cerramos el driver aquí para permitir depuración, pero sí en el except externo
                return False

        except TimeoutException as e:
            print(f"Error de Timeout durante el login: {e}")
            if self.driver: self.free_driver() # Asegurarse de cerrar el driver
            return False
        except NoSuchElementException as e:
            print(f"Error: Elemento no encontrado durante el login: {e}")
            if self.driver: self.free_driver() # Asegurarse de cerrar el driver
            return False
        except Exception as e:
            print(f"Error inesperado durante el login: {e}")
            if self.driver: self.free_driver() # Asegurarse de cerrar el driver
            return False

    def extract_movements(self, since_date, until_date):
        """
        Extrae los movimientos bancarios para el rango de fechas especificado.
        Args:
            since_date (str): Fecha desde en formato 'ddmmyyyy'.
            until_date (str): Fecha hasta en formato 'ddmmyyyy'.
        Returns:
            list: Lista de diccionarios con los movimientos [{'fecha': str, 'descripcion': str, 'monto': float}], 
                  o lista vacía si no se encuentran o hay error.
        """
        if not self.driver:
            print("Error: El driver no está inicializado. Llama a login() primero.")
            return []

        downloaded_file_path = None
        movements = []
        try:
            print("Navegando a la sección de movimientos...")
            # 6. Clic en "Saldos y movs."
            saldos_movs_btn = self.driver_wait_by_clickable(self.SALDOS_MOVS_BTN_XPATH, 'XPATH', time=30)
            time.sleep(random.uniform(1.0, 2.5))
            print("Haciendo clic en 'Saldos y movs.'...")
            saldos_movs_btn.click()
            time.sleep(random.uniform(1.5, 3.0))

            # 7. Clic en "Buscar por fechas"
            buscar_fechas_span = self.driver_wait_by_clickable(self.BUSCAR_FECHAS_XPATH, 'XPATH', time=20)
            time.sleep(random.uniform(0.8, 2.0))
            print("Haciendo clic en 'Buscar por fechas'...")
            self.driver.execute_script("arguments[0].click();", buscar_fechas_span) 
            time.sleep(random.uniform(1.0, 2.5))

            # 8. Ingresar fecha desde
            fecha_desde_input = self.driver_wait_by_visibility(self.FECHA_DESDE_ID, 'ID', time=15)
            time.sleep(random.uniform(0.5, 1.2))
            print(f"Ingresando 'Fecha desde': {since_date}")
            self.clean_and_fill_input(fecha_desde_input, since_date)
            time.sleep(random.uniform(0.5, 1.0))

            # 9. Ingresar fecha hasta
            fecha_hasta_input = self.driver_wait_by_visibility(self.FECHA_HASTA_ID, 'ID', time=10)
            time.sleep(random.uniform(0.5, 1.2))
            print(f"Ingresando 'Fecha hasta': {until_date}")
            self.clean_and_fill_input(fecha_hasta_input, until_date)
            time.sleep(random.uniform(0.5, 1.0))

            # 10. Clic en "Buscar"
            buscar_btn = self.driver_wait_by_clickable(self.BUSCAR_BTN_XPATH, 'XPATH', time=10)
            time.sleep(random.uniform(0.8, 1.8))
            print("Haciendo clic en 'Buscar'...")
            buscar_btn.click()
            time.sleep(random.uniform(3.0, 5.0))

            # 11. Descargar el archivo Excel
            print("Intentando descargar archivo Excel...")
            try:
                # Clic en el botón dropdown "Descargar"
                print("Esperando botón dropdown 'Descargar'...")
                descargar_dropdown = self.driver_wait_by_clickable(self.DESCARGAR_DROPDOWN_BTN_XPATH, 'XPATH', time=25)
                time.sleep(random.uniform(1.0, 2.5))
                print("Haciendo clic en dropdown 'Descargar'...")
                try:
                    descargar_dropdown.click()
                except ElementClickInterceptedException:
                    print("Clic normal interceptado, intentando con JavaScript...")
                    self.driver.execute_script("arguments[0].click();", descargar_dropdown)
                
                time.sleep(random.uniform(1.0, 2.0)) # Espera a que aparezca el menú

                # Clic en la opción "Descargar Excel"
                print("Esperando opción 'Descargar Excel'...")
                descargar_excel_option = self.driver_wait_by_clickable(self.DESCARGAR_EXCEL_OPTION_XPATH, 'XPATH', time=15)
                time.sleep(random.uniform(0.5, 1.5))
                print("Haciendo clic en 'Descargar Excel'...")
                try:
                    descargar_excel_option.click()
                except ElementClickInterceptedException:
                     print("Clic normal interceptado en opción Excel, intentando con JavaScript...")
                     self.driver.execute_script("arguments[0].click();", descargar_excel_option)
                
                # Esperar a que la descarga termine
                downloaded_file_path = self._wait_for_download(timeout=90) # Aumentar timeout si es necesario

            except TimeoutException as e_click:
                print(f"Error: Timeout esperando algún botón de descarga: {e_click}")
                return [] # No se puede continuar sin descarga
            except Exception as e_click_general:
                 print(f"Error inesperado durante el proceso de clic para descarga: {e_click_general}")
                 return []
            
            # 12. Procesar el archivo Excel si se descargó
            if downloaded_file_path:
                print(f"Procesando archivo: {os.path.basename(downloaded_file_path)}")
                try:
                    # Leer el Excel con pandas
                    # Puede necesitar ajustes como header=..., skiprows=...
                    # df = pd.read_excel(downloaded_file_path, engine='openpyxl') # Llamada original
                    # --- Ajuste Tentativo: Saltar las primeras 5 filas (0 a 4) --- 
                    # print("Intentando leer Excel saltando 5 filas...")
                    # df = pd.read_excel(downloaded_file_path, engine='openpyxl', skiprows=5) # Ajuste anterior
                    # --- Ajuste Final: Usar fila 15 (índice 14) como encabezado --- 
                    print("Intentando leer Excel con encabezado en fila 15 (índice 14)...")
                    df = pd.read_excel(downloaded_file_path, engine='openpyxl', header=14)
                    
                    # --- Identificar y renombrar columnas --- 
                    # ¡¡IMPORTANTE!! Reemplaza 'Fecha Real', 'Descripción Real', 'Monto Real' 
                    # con los nombres EXACTOS de las columnas en tu archivo Excel.
                    # Inspecciona un archivo descargado para obtener estos nombres.
                    column_map = {
                        'Fecha': 'fecha', # Nombre esperado vs nombre en el script
                        'Descripción': 'descripcion',
                        # Si Excel tiene columnas separadas para Cargo/Abono:
                        'Cheques / Cargos $': 'cargo_excel', # Actualizado según imagen
                        'Depósitos / Abonos $': 'abono_excel', # Actualizado según imagen
                        # O si tiene una sola columna de Monto (con +/- o formato especial):
                        # 'Monto': 'monto_excel' # Ya no aplica
                    }
                    
                    # Renombrar columnas para consistencia
                    df.rename(columns=column_map, inplace=True)

                    # --- Detener extracción si no hay fecha --- 
                    print("Verificando la integridad de la columna 'fecha'...")
                    nan_indices = df.index[df['fecha'].isna()]

                    if not nan_indices.empty:
                        first_invalid_index = nan_indices[0]
                        print(f"Primera fecha inválida/vacía encontrada en el índice (original del Excel leído): {first_invalid_index}. Se detendrá la extracción en esta fila.")
                        # Mantener solo las filas ANTES de la primera fila inválida
                        df = df[df.index < first_invalid_index]
                        print(f"Se conservarán {len(df)} filas con fechas válidas.")
                    else:
                        print("Todas las filas tienen fecha válida. Se procesará toda la tabla.")

                    # Si el DataFrame queda vacío después del filtro, no hay nada que procesar
                    if df.empty:
                        print("No se encontraron filas válidas con fecha después del filtrado.")
                        # Aún así, eliminamos el archivo descargado si existe
                        # El bloque finally se encargará de la eliminación
                        return [] 
                    # --- Fin de la lógica de detener extracción ---
                    
                    # Verificar qué columnas existen después de renombrar
                    required_cols = ['fecha', 'descripcion']
                    # has_monto_col = 'monto_excel' in df.columns # Ya no aplica
                    has_cargo_col = 'cargo_excel' in df.columns
                    has_abono_col = 'abono_excel' in df.columns
                    
                    # Añadir la columna de monto requerida a la lista
                    # if has_monto_col:
                    #     required_cols.append('monto_excel')
                    if has_cargo_col and has_abono_col:
                        required_cols.extend(['cargo_excel', 'abono_excel'])
                    else:
                         print("Error: Columnas de cargo/abono no encontradas en el Excel con los nombres esperados.")
                         # Podrías imprimir df.columns aquí para depurar
                         print(f"Columnas encontradas: {df.columns.tolist()}")
                         return []
                         
                    # Filtrar solo las columnas necesarias
                    df = df[required_cols]
                    
                    # --- Limpieza y Transformación --- 
                    # Convertir columna de fecha a string (o a datetime si se prefiere)
                    df['fecha'] = df['fecha'].astype(str) 
                    df['descripcion'] = df['descripcion'].astype(str)
                    
                    # Función para limpiar y convertir montos (adaptada para DataFrame)
                    def clean_monto(monto_val):
                        if pd.isna(monto_val): return 0.0
                        # Si los montos ya vienen como números (ej. -5000.0), convertirlos a str
                        monto_str = str(monto_val) 
                        try:
                            # Eliminar $, puntos de miles, signo +, espacios
                            # Mantener el signo negativo (-) 
                            monto_str_clean = monto_str.replace('$', '') \
                                                     .replace('.', '') \
                                                     .replace('+', '') \
                                                     .replace(' ', '') \
                                                     .strip()
                            # Reemplazar coma decimal si existe
                            monto_str_clean = monto_str_clean.replace(',', '.') 
                            # Asegurarse de que un string vacío o solo '-' se convierta en 0.0
                            return float(monto_str_clean) if monto_str_clean and monto_str_clean != '-' else 0.0
                        except ValueError:
                            print(f"Advertencia: No se pudo convertir el valor de monto '{monto_val}' a número.")
                            return 0.0
                            
                    # Aplicar limpieza a la columna de monto
                    if has_cargo_col and has_abono_col:
                        # Limpiar ambas columnas
                        df['cargo_limpio'] = df['cargo_excel'].apply(clean_monto)
                        df['abono_limpio'] = df['abono_excel'].apply(clean_monto)
                        # Combinar en una sola columna 'monto'
                        # El cargo ya viene negativo en la imagen, así que simplemente sumamos
                        # Si el cargo viniera positivo, usaríamos df['abono_limpio'] - df['cargo_limpio']
                        df['monto'] = df['abono_limpio'] + df['cargo_limpio'] 
                    # if has_monto_col:
                    #      df['monto'] = df['monto_excel'].apply(clean_monto)

                    # Seleccionar columnas finales y convertir a lista de diccionarios
                    final_cols = ['fecha', 'descripcion', 'monto']
                    movements = df[final_cols].to_dict('records')
                    
                    print(f"Procesamiento de Excel completado. {len(movements)} movimientos extraídos.")
                    
                    # --- Guardar en MongoDB ---
                    if movements:
                        print("Intentando guardar movimientos en MongoDB...")
                        if save_movements(movements):
                             print("Movimientos guardados en MongoDB exitosamente.")
                        else:
                             print("Fallo al guardar movimientos en MongoDB.")
                    else:
                        print("No hay movimientos válidos para guardar en MongoDB.")
                    # --- Fin Guardar en MongoDB ---

                except FileNotFoundError:
                    print(f"Error: Archivo Excel no encontrado en la ruta: {downloaded_file_path}")
                except ImportError:
                     print("Error: Falta la librería 'openpyxl'. Instálala con: pip install openpyxl")
                except KeyError as e:
                    print(f"Error: Columna esperada no encontrada en el Excel: {e}. Revisa los nombres en column_map.")
                    # Imprimir columnas para ayudar a depurar
                    try: 
                        temp_df = pd.read_excel(downloaded_file_path, engine='openpyxl')
                        print(f"Columnas reales en el archivo: {temp_df.columns.tolist()}")
                    except Exception as read_err:
                         print(f"No se pudo releer el archivo para mostrar columnas: {read_err}")
                except Exception as e_process:
                    print(f"Error inesperado procesando el archivo Excel: {e_process}")

        except TimeoutException as e:
            print(f"Error de Timeout durante la extracción de movimientos: {e}")
            return []
        except NoSuchElementException as e:
            print(f"Error: Elemento no encontrado durante la extracción: {e}")
            return []
        except Exception as e:
            print(f"Error inesperado durante la extracción de movimientos: {e}")
            return []
        finally:
             # Limpiar archivo descargado
             if downloaded_file_path and os.path.exists(downloaded_file_path):
                 try:
                     os.remove(downloaded_file_path)
                     print(f"Archivo descargado eliminado: {os.path.basename(downloaded_file_path)}")
                 except OSError as e_remove:
                      print(f"Error eliminando archivo descargado {downloaded_file_path}: {e_remove}")
        
        return movements

    def close(self):
        """Cierra el driver del navegador y la conexión a MongoDB."""
        print("Cerrando el navegador...")
        self.free_driver()
        print("Navegador cerrado.")
        # Cerrar conexión MongoDB al final
        close_mongo_client()

# Ejemplo de uso (para pruebas rápidas, se moverá a multi_scrape.py)
if __name__ == '__main__':
    # Cargar credenciales desde .env para prueba local
    from dotenv import load_dotenv
    import os
    load_dotenv(dotenv_path='../../.env') # Asume que .env está dos niveles arriba
    
    test_rut = os.getenv('RUT')
    test_clave = os.getenv('CLAVE')

    if not test_rut or not test_clave:
        print("Error: Define RUT y CLAVE en el archivo .env en la raíz del proyecto para probar.")
    else:
        # Fechas de ejemplo (formato ddmmyyyy)
        fecha_inicio = "01042024" # Cambiar a fechas reales con movimientos
        fecha_fin = "30042024"   # Cambiar a fechas reales con movimientos

        scraper = BancoEstadoScraper(username=test_rut, password=test_clave)
        movimientos = [] # Inicializar aquí para satisfacer al linter
        
        if scraper.login():
            print("--- Iniciando extracción de movimientos ---")
            movimientos = scraper.extract_movements(fecha_inicio, fecha_fin)
            
            if movimientos:
                print("--- Movimientos Extraídos (desde Excel) ---")
                # for mov in movimientos:
                #     print(mov)
                # Usar pandas para una mejor visualización si está instalado
                try:
                    df = pd.DataFrame(movimientos)
                    print(df)
                except ImportError:
                     for mov in movimientos:
                         print(mov)
            else:
                print("No se extrajeron movimientos.")
                
        else:
            print("El login falló. No se procederá a la extracción.")
            
        scraper.close() 