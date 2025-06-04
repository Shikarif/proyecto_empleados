"""
Configuración de la conexión a la base de datos MySQL para el sistema de Asignación de Tareas Equitativas.

Este módulo proporciona la funcionalidad para establecer conexiones con la base de datos MySQL.
Utiliza mysql-connector-python para manejar las conexiones de manera segura y eficiente.

La función get_connection() crea y retorna una nueva conexión a la base de datos con los
parámetros configurados. Es importante cerrar la conexión después de usarla para liberar
recursos.

Parámetros de conexión:
- host: Dirección del servidor de base de datos (localhost)
- user: Usuario de la base de datos (root)
- password: Contraseña del usuario (vacía por defecto)
- database: Nombre de la base de datos (testdb)

Nota: En un entorno de producción, se recomienda:
1. Usar variables de entorno para las credenciales
2. Implementar un pool de conexiones
3. Manejar errores de conexión
4. Usar un usuario con permisos limitados
"""

import mysql.connector

def get_connection():
    """
    Crea y retorna una nueva conexión a la base de datos MySQL.
    
    Returns:
        mysql.connector.connection.MySQLConnection: Objeto de conexión a la base de datos
        
    Raises:
        mysql.connector.Error: Si hay un error al conectar con la base de datos
    """
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='testdb'
    )

