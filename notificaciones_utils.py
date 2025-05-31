from db_config import get_connection
from flask_socketio import SocketIO
from flask import current_app
from datetime import datetime

def crear_y_emitir_notificacion(usuario_id, mensaje, tipo='info'):
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