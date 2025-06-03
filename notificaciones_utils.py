"""
Utilidades para el sistema de notificaciones en tiempo real.

Este módulo proporciona funciones para:
- Crear notificaciones en la base de datos
- Emitir notificaciones en tiempo real usando Socket.IO
- Gestionar el estado de las notificaciones

Las notificaciones pueden ser de diferentes tipos:
- info: Información general
- exito: Operaciones exitosas
- alerta: Advertencias importantes
- error: Errores o problemas

El sistema utiliza una combinación de almacenamiento persistente (MySQL)
y comunicación en tiempo real (Socket.IO) para garantizar que las
notificaciones lleguen a los usuarios incluso si no están conectados
en el momento de su creación.
"""

from db_config import get_connection
from flask_socketio import SocketIO
from flask import current_app
from datetime import datetime

def crear_y_emitir_notificacion(usuario_id, mensaje, tipo='info'):
    """
    Crea una notificación y la emite en tiempo real al usuario.
    
    Esta función realiza dos operaciones principales:
    1. Almacena la notificación en la base de datos MySQL
    2. Emite la notificación en tiempo real usando Socket.IO
    
    Args:
        usuario_id (int): ID del usuario destinatario
        mensaje (str): Contenido de la notificación
        tipo (str, optional): Tipo de notificación. Por defecto 'info'.
            Valores posibles: 'info', 'exito', 'alerta', 'error'
            
    Returns:
        int: ID de la notificación creada
        
    Ejemplo:
        crear_y_emitir_notificacion(
            usuario_id=1,
            mensaje='Nueva tarea asignada',
            tipo='info'
        )
    """
    # Insertar notificación en la base de datos MySQL
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    fecha = datetime.now()
    cursor.execute("""
        INSERT INTO notificaciones (mensaje, tipo, leido, fecha, usuario_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (mensaje, tipo, False, fecha, usuario_id))
    notif_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    # Emitir por socket solo al usuario si socketio está disponible
    socketio = current_app.extensions['socketio'] if 'socketio' in current_app.extensions else None
    if socketio:
        socketio.emit(f'notificacion_{usuario_id}', {
            'id': notif_id,
            'mensaje': mensaje,
            'tipo': tipo,
            'leido': False,
            'fecha': fecha.strftime('%Y-%m-%d %H:%M')
        }) 