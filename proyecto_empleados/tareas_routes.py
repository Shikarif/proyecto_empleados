# Eliminar todas las funciones y rutas relacionadas con comentarios y sincronización de comentarios, incluyendo:
# - listar_comentarios_tarea
# - agregar_comentario_tarea
# - eliminar_comentario_tarea
# - editar_comentario_tarea
# - sincronizar_comentarios_tarea
# - resincronizar_comentarios_tarea
# - agregar_comentario_trello, editar_comentario_trello, eliminar_comentario_trello
# (Dejar solo la estructura base para implementar la nueva lógica desde cero) 

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from db_config import get_connection
import requests
from config import TRELLO_API_KEY, TRELLO_API_TOKEN
from datetime import datetime

tareas_bp = Blueprint('tareas', __name__)

# --- Utilidades Trello ---
def agregar_comentario_trello(idCardTrello, comentario):
    url = f"https://api.trello.com/1/cards/{idCardTrello}/actions/comments"
    params = {"text": comentario, "key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
    resp = requests.post(url, params=params)
    if resp.status_code == 200:
        return resp.json().get('id'), resp.json().get('memberCreator', {}).get('fullName', 'Trello')
    return None, 'Trello'

def obtener_comentarios_trello(idCardTrello):
    url = f"https://api.trello.com/1/cards/{idCardTrello}/actions"
    params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN, "filter": "commentCard"}
    resp = requests.get(url, params=params)
    if resp.status_code == 200:
        return resp.json()
    return []

# --- API Comentarios ---
@tareas_bp.route('/tareas/<int:tarea_id>/comentarios', methods=['GET'])
@login_required
def listar_comentarios_tarea(tarea_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener idCardTrello
        cursor.execute('SELECT idCardTrello FROM tareas_trello WHERE id = %s', (tarea_id,))
        row = cursor.fetchone()
        idCardTrello = row['idCardTrello'] if row else None
        # Traer comentarios del sistema
        cursor.execute('''
            SELECT c.id, c.comentario, c.fecha_creacion, c.usuario_id, e.nombre, e.apellido, e.rol, c.id_comment_trello
            FROM comentarios_tarea c
            LEFT JOIN empleados e ON c.usuario_id = e.id
            WHERE c.tarea_id = %s
            ORDER BY c.fecha_creacion ASC
        ''', (tarea_id,))
        comentarios = []
        ids_trello_db = set()
        for c in cursor.fetchall():
            if c['id_comment_trello']:
                ids_trello_db.add(c['id_comment_trello'])
            if c['usuario_id'] is None:
                c['fuente'] = 'trello'
                c['nombre'] = c['nombre'] or 'Trello'
                c['apellido'] = c['apellido'] or ''
                c['rol'] = c['rol'] or 'Trello'
                c['puede_editar'] = False
                c['puede_eliminar'] = False
            else:
                c['fuente'] = 'sistema'
                c['puede_editar'] = (c['usuario_id'] == current_user.id or current_user.rol == 'jefe')
                c['puede_eliminar'] = (c['usuario_id'] == current_user.id or current_user.rol == 'jefe')
            comentarios.append({
                'id': c['id'],
                'comentario': c['comentario'],
                'fecha': c['fecha_creacion'],
                'usuario_id': c['usuario_id'],
                'fuente': c['fuente'],
                'nombre': c['nombre'],
                'apellido': c['apellido'],
                'rol': c['rol'],
                'id_comment_trello': c['id_comment_trello'],
                'puede_editar': c['puede_editar'],
                'puede_eliminar': c['puede_eliminar']
            })
        # Traer comentarios de Trello y agregar los que no estén
        if idCardTrello:
            for action in obtener_comentarios_trello(idCardTrello):
                id_comment_trello = action['id']
                if id_comment_trello in ids_trello_db:
                    continue
                nombre_trello = action['memberCreator']['fullName']
                fecha_creacion = action['date']
                comentarios.append({
                    'id': None,
                    'comentario': action['data']['text'],
                    'fecha': fecha_creacion,
                    'usuario_id': None,
                    'nombre': nombre_trello,
                    'apellido': '',
                    'rol': 'Trello',
                    'id_comment_trello': id_comment_trello,
                    'fuente': 'trello',
                    'puede_editar': False,
                    'puede_eliminar': False
                })
        comentarios.sort(key=lambda x: x['fecha'])
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'comentarios': comentarios})
    except Exception as e:
        return jsonify({'success': False, 'comentarios': [], 'message': str(e)}), 500

@tareas_bp.route('/tareas/<int:tarea_id>/comentarios', methods=['POST'])
@login_required
def agregar_comentario_tarea(tarea_id):
    try:
        data = request.get_json()
        comentario = data.get('comentario', '').strip()
        if not comentario:
            return jsonify({'success': False, 'message': 'El comentario no puede estar vacío.'}), 400
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT idCardTrello FROM tareas_trello WHERE id = %s', (tarea_id,))
        row = cursor.fetchone()
        idCardTrello = row['idCardTrello'] if row else None
        idCommentTrello, nombre_trello = None, None
        if idCardTrello:
            idCommentTrello, nombre_trello = agregar_comentario_trello(idCardTrello, comentario)
        cursor.execute('''
            INSERT INTO comentarios_tarea (tarea_id, usuario_id, comentario, fecha_creacion, id_comment_trello, nombre, apellido, rol)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (tarea_id, current_user.id, comentario, datetime.now(), idCommentTrello, current_user.nombre, current_user.apellido, current_user.rol))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@tareas_bp.route('/tareas/<int:tarea_id>/sincronizar_comentarios', methods=['POST'])
@login_required
def sincronizar_comentarios_tarea(tarea_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT idCardTrello FROM tareas_trello WHERE id = %s', (tarea_id,))
        row = cursor.fetchone()
        idCardTrello = row['idCardTrello'] if row else None
        # Obtener ids ya existentes
        cursor.execute('SELECT id_comment_trello FROM comentarios_tarea WHERE tarea_id = %s AND id_comment_trello IS NOT NULL', (tarea_id,))
        ids_trello_db = set(row['id_comment_trello'] for row in cursor.fetchall())
        nuevos = 0
        if idCardTrello:
            for action in obtener_comentarios_trello(idCardTrello):
                id_comment_trello = action['id']
                if id_comment_trello in ids_trello_db:
                    continue
                nombre_trello = action['memberCreator']['fullName']
                fecha_creacion = action['date']
                cursor2 = conn.cursor()
                cursor2.execute('''
                    INSERT IGNORE INTO comentarios_tarea (tarea_id, usuario_id, comentario, fecha_creacion, id_comment_trello, nombre, apellido, rol)
                    VALUES (%s, NULL, %s, %s, %s, %s, %s, %s)
                ''', (tarea_id, action['data']['text'], fecha_creacion, id_comment_trello, nombre_trello, '', 'Trello'))
                conn.commit()
                cursor2.close()
                nuevos += 1
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'nuevos': nuevos})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@tareas_bp.route('/comentarios/<int:comentario_id>', methods=['DELETE'])
@login_required
def eliminar_comentario_tarea(comentario_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT usuario_id FROM comentarios_tarea WHERE id = %s', (comentario_id,))
        row = cursor.fetchone()
        if not row or row['usuario_id'] != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso para eliminar este comentario.'}), 403
        cursor.execute('DELETE FROM comentarios_tarea WHERE id = %s', (comentario_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@tareas_bp.route('/comentarios/<int:comentario_id>', methods=['PUT'])
@login_required
def editar_comentario_tarea(comentario_id):
    try:
        data = request.get_json()
        nuevo_comentario = data.get('comentario', '').strip()
        if not nuevo_comentario:
            return jsonify({'success': False, 'message': 'El comentario no puede estar vacío.'}), 400
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT usuario_id FROM comentarios_tarea WHERE id = %s', (comentario_id,))
        row = cursor.fetchone()
        if not row or row['usuario_id'] != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso para editar este comentario.'}), 403
        cursor.execute('UPDATE comentarios_tarea SET comentario = %s WHERE id = %s', (nuevo_comentario, comentario_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500 