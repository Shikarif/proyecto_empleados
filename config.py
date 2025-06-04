"""
Archivo de configuración principal del sistema de Asignación de Tareas Equitativas.

Este archivo maneja todas las configuraciones globales del sistema, incluyendo:
- Claves de API para servicios externos (Trello)
- Variables de entorno
- Configuraciones de seguridad

El archivo utiliza python-dotenv para cargar variables de entorno desde un archivo .env,
lo que permite mantener las claves sensibles fuera del código fuente.

Variables de entorno requeridas:
- TRELLO_API_KEY: Clave de API de Trello para autenticación
- TRELLO_API_TOKEN: Token de acceso de Trello para operaciones autenticadas

Nota: Es importante mantener el archivo .env en .gitignore para no exponer las claves.
"""

import os
from dotenv import load_dotenv

# Carga las variables del archivo .env al entorno
load_dotenv()

# Configuración de Trello
TRELLO_API_KEY = os.getenv('TRELLO_API_KEY')  # Clave de API de Trello
TRELLO_API_TOKEN = os.getenv('TRELLO_API_TOKEN')  # Token de acceso de Trello
