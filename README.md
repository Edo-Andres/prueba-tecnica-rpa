# Desafío rpa Scraper (Clay) con Almacenamiento en MongoDB

## Descripción General

Este proyecto implementa un scraper en Python utilizando Selenium y Undetected-Chromedriver para automatizar el inicio de sesión en la plataforma online de Banco Estado. Una vez autenticado, extrae los movimientos bancarios para un rango de fechas especificado, descarga estos movimientos temporalmente en un archivo Excel, procesa los datos relevantes (fecha, descripción, monto) y los almacena en una base de datos MongoDB.

## Funcionalidades Principales

1.  **Login Seguro:** Automatiza el proceso de inicio de sesión en la plataforma web de Banco Estado, manejando credenciales de forma segura a través de variables de entorno.
2.  **Extracción de Movimientos:** Navega hasta la sección de cartola histórica, filtra por un rango de fechas proporcionado, e inicia la descarga de los movimientos en formato Excel.
3.  **Procesamiento de Datos:** Lee el archivo Excel descargado, identifica y extrae las columnas de fecha, descripción y montos (cargos/abonos), calculando un monto neto por transacción.
4.  **Almacenamiento en MongoDB:** Guarda los datos procesados de los movimientos en una colección MongoDB especificada, permitiendo un fácil acceso y análisis posterior.

## Prerrequisitos

*   **Python:** Versión 3.8 o superior recomendada. (creado con version 3.12)
*   **pip:** Gestor de paquetes de Python.
*   **Google Chrome:** Navegador web instalado.
*   **MongoDB:** Instancia de MongoDB corriendo (localmente por defecto en `mongodb://localhost:27017/` o configurada vía `.env`).
*   **Configurar y Ejecutar Base de Datos MongoDB (Docker):** Si prefieres usar Docker para gestionar MongoDB, puedes levantar un contenedor fácilmente:
    ```bash
    # Descarga la imagen oficial de MongoDB
    docker pull mongo

    # Ejecuta un contenedor de MongoDB en segundo plano
    # Mapea el puerto 27017 del contenedor al puerto 27017 de tu máquina
    # Nombra el contenedor como 'mongodb-clay' para fácil referencia
    docker run --name mongodb-clay -p 27017:27017 -d mongo
    ```
    Esto iniciará una instancia de MongoDB accesible en `mongodb://localhost:27017/`. Puedes detener el contenedor con `docker stop mongodb-clay` y reiniciarlo con `docker start mongodb-clay`.

## Instalación

1.  **Clonar el Repositorio:**
    ```bash
    git clone https://github.com/Edo-Andres/prueba-tecnica-rpa
    cd prueba-tecnica-rpa
    ```

2.  **Crear y Activar un Entorno Virtual (Recomendado):**
    ```bash
    python -m venv env_rpa
    # En Windows
    .\env_rpa\Scripts\activate
    # En macOS/Linux
    source env_rpa/bin/activate
    ```

3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno:**
    *   Crea un archivo llamado `.env` en la raíz del proyecto (`prueba-tecnica-rpa/`).
    *   Añade las siguientes variables (dejando los valores vacíos si subes el código a un repositorio público):
        ```dotenv
        # Credenciales Banco Estado (NO SUBIR A GIT CON VALORES REALES)
        RUT=
        CLAVE=

        # Configuración MongoDB (Opcional - si no se definen, usará valores por defecto)
        # MONGO_URI=mongodb://tu_usuario:tu_password@host:puerto/
        # MONGO_DB_NAME=mi_base_de_datos
        # MONGO_COLLECTION=mis_movimientos
        ```
    *   **Importante:** Añade `.env` a tu archivo `.gitignore` si aún no está para evitar subir credenciales accidentalmente.

## Ejecución

El script principal para ejecutar el scraper es `multi_scrape.py` ubicado en la carpeta `scripts/`. Este script está diseñado para obtener las credenciales (`RUT` y `CLAVE`) de forma segura desde el archivo `.env` configurado en el paso de instalación.

**Ejecución Principal (Recomendada, usando `.env`):**

Asegúrate de que tu archivo `.env` contiene las credenciales correctas. Luego, ejecuta el script desde la raíz del proyecto (`prueba-tecnica-rpa/`) proporcionando el rango de fechas:

```bash
# Ejemplo con formato YYYY-MM-DD
python scripts/multi_scrape.py --date-range "2025-04-01:2025-04-08"

```

Pasar las credenciales directamente como argumentos, **no se recomienda** por razones de seguridad en archivo `.env` está configurado.

El script iniciará el navegador, utilizará las credenciales (preferentemente de `.env`), realizará el login, descargará los movimientos para el rango de fechas, los procesará y los guardará en MongoDB, mostrando el progreso en la consola.

## Demostración Visual

La carpeta `demo_img/` contiene:

*   `demo_terminal.jpg`: Una captura de pantalla de la terminal después de una ejecución exitosa del script.
*   `MongoDB.jpg`: Una imagen mostrando los datos guardados en la colección de MongoDB, accedida mediante Docker (`docker exec -it mongodb-clay mongosh`).
