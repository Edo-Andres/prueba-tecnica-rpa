import os
from .constants import (
    SERVER_ENVS,
    TEMP_FOLDER
)
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from .mime_type import MIME_TYPE
import undetected_chromedriver as uc
# Definir la ruta base del proyecto para construir la ruta de descargas
# __file__ se refiere a driver_factory.py
# dirname(__file__) es webdriver/
# dirname(dirname(__file__)) es prueba-tecnica-rpa/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "downloads")


class Singleton(type):
    _instances = {}

    def __call__(self, *args, **kwargs):
        if self not in self._instances:
            self._instances[self] = super(Singleton, self).__call__(*args, **kwargs)
        return self._instances[self]


class DriverFactory:

    __metaclass__ = Singleton

    server_envs = SERVER_ENVS

    def get_driver(self,
                   browser: str,
                   options: webdriver.ChromeOptions = None,
                   prefs: dict = None
                   ) -> webdriver:
        if os.environ.get('ENV') in self.server_envs:
            self.setup()
        driver = None
        if browser == 'chrome':
            driver = self.build_chrome(options=options, prefs=prefs, download_directory=DOWNLOAD_DIR)
        if browser == 'firefox':
            driver = self.build_firefox(download_directory=DOWNLOAD_DIR)
        if not driver:
            raise ValueError(f'{browser} is not supported')
        return driver

    def setup(self):
        for dir in ['/tmp/bin', '/tmp/bin/lib', '/tmp/download']:
            if not os.path.exists(dir):
                os.makedirs(dir)

        self.tmp_folder = TEMP_FOLDER

        for dir in ['', '/user-data', '/data-path',  '/cache-dir']:
            if not os.path.exists(f'{self.tmp_folder}{dir}'):
                os.makedirs(f'{self.tmp_folder}{dir}')

        # Asegurarse de que el directorio de descargas exista
        if not os.path.exists(DOWNLOAD_DIR):
            print(f"Creando directorio de descargas en: {DOWNLOAD_DIR}")
            os.makedirs(DOWNLOAD_DIR)
        else:
             print(f"Directorio de descargas ya existe: {DOWNLOAD_DIR}")

        # La creación de /tmp/bin etc. podría eliminarse si solo se usa Windows y uc
        for dir in ['/tmp/bin', '/tmp/bin/lib']:
            if not os.path.exists(dir):
                try: os.makedirs(dir) 
                except OSError: pass # Ignorar si falla en Windows
        # Mantener /tmp/download como fallback si no se pasan prefs?
        if not os.path.exists("/tmp/download"):
            try: os.makedirs("/tmp/download") 
            except OSError: pass # Ignorar si falla en Windows

        self.tmp_folder = TEMP_FOLDER
        for dir in ['', '/user-data', '/data-path', '/cache-dir']:
            if not os.path.exists(f'{self.tmp_folder}{dir}'):
                try: os.makedirs(f'{self.tmp_folder}{dir}')
                except OSError: pass # Ignorar si falla en Windows

    def build_firefox(self, download_directory: str = None):
        if not download_directory:
            download_directory = "/tmp/download" # Fallback
        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference("browser.download.dir", download_directory) # Usar directorio
        profile.set_preference("plugins.always_open_pdf_externally,", True)
        profile.set_preference("browser.download.manager.useWindow", False)
        profile.set_preference("pdfjs.disabled", True)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", MIME_TYPE)
        options = Options()
        if os.environ.get('ENV') in self.server_envs:
            options.headless = bool(os.environ.get('HEADLESS'))
            return webdriver.Firefox(
                firefox_profile=profile,
                options=options,
                executable_path='/opt/drivers/geckodriver',
                service_log_path='/tmp/geckodriver.log')
        else:
            return webdriver.Firefox(
                firefox_profile=profile,
                options=options,
                executable_path='/usr/share/geckodriver')

    def build_chrome(self, options: webdriver.ChromeOptions = None, prefs: dict = None, download_directory: str = None):
        if not download_directory:
            download_directory = DOWNLOAD_DIR # Usar el directorio por defecto si no se pasa
        
        # Preparar las preferencias de descarga
        effective_prefs = {
            "download.default_directory": download_directory,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True, # Mantener activado o considerar desactivar si interfiere
            "profile.default_content_setting_values.automatic_downloads": 1,
        }
        # Si se pasaron prefs explícitamente, fusionarlas (dando prioridad a las explícitas)
        if prefs:
            effective_prefs.update(prefs)

        if not options:
            options = uc.ChromeOptions()
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--window-size=1280,768')
            options.add_argument('--disable-popup-blocking')
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--remote-debugging-port=9222")
            options.add_argument("--start-maximized")
            options.add_argument('--enable-logging')
            options.add_argument('--log-level=0')
            options.add_argument('--v=99')
            options.add_argument("--incognito")
        
        # Añadir las preferencias de descarga a las opciones existentes o nuevas
        options.add_experimental_option('prefs', effective_prefs)
        
        print(f"Configurando directorio de descargas en: {download_directory}")
        print("Inicializando driver con undetected-chromedriver...")
        try:
            chrome = uc.Chrome(options=options, use_subprocess=True)
            print("Driver uc.Chrome inicializado.")
        except Exception as e:
            print(f"Error al inicializar undetected-chromedriver: {e}")
            print("Asegúrate de que Google Chrome esté instalado y que uc pueda descargar el driver.")
            raise e
        return chrome
