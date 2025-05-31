from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, abort, send_from_directory
from db_config import get_connection
from datetime import datetime, timedelta
from flask_login import current_user, login_required
import requests
from config import TRELLO_API_KEY, TRELLO_API_TOKEN
import os
from werkzeug.utils import secure_filename
from flask import current_app
from notificaciones_utils import crear_y_emitir_notificacion

tareas_bp = Blueprint('tareas', __name__)

# Rutas para gestión de tareas
@tareas_bp.route('/tareas/nueva', methods=['GET', 'POST'])
def nueva_tarea():
    return redirect(url_for('equipos.lista_equipos'))

def crear_tarjeta_trello(idBoard, nombre_tarea, descripcion):
    url_listas = f"https://api.trello.com/1/boards/{idBoard}/lists"
    params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
    resp = requests.get(url_listas, params=params)
    if resp.status_code == 200 and resp.json():
        idList = resp.json()[0]['id']
    else:
        print("No se pudo obtener la lista del tablero.")
        return None
    url_card = "https://api.trello.com/1/cards"
    params = {
        "idList": idList,
        "name": nombre_tarea,
        "desc": descripcion,
        "key": TRELLO_API_KEY,
        "token": TRELLO_API_TOKEN
    }
    resp = requests.post(url_card, params=params)
    if resp.status_code == 200:
        return resp.json()['id']  # idCard de Trello
    else:
        print("Error al crear tarjeta:", resp.text)
        return None

@tareas_bp.route('/tareas/nueva-modal', methods=['POST'])
def nueva_tarea_modal():
    from flask import render_template_string
    try:
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        fecha_limite = request.form['fecha_limite']
        prioridad = request.form['prioridad']
        habilidades_requeridas = request.form['habilidades_requeridas']
        equipo_id = request.form.get('equipo_id')
        empleado_id = request.form.get('asignado_a')
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener idBoard del equipo
        cursor.execute('SELECT idBoard FROM equipos WHERE id = %s', (equipo_id,))
        row = cursor.fetchone()
        idBoard = row['idBoard'] if row else None
        idCardTrello = None
        if idBoard:
            idCardTrello = crear_tarjeta_trello(idBoard, titulo, descripcion)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tareas_trello (titulo, descripcion, fecha_creacion, fecha_limite, 
                              prioridad, horas_estimadas, habilidades_requeridas, tiempo_estimado, tiempo_real, temporizador_activo, inicio_temporizador, equipo_id, empleado_id, idCardTrello)
            VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (titulo, descripcion, fecha_limite, prioridad, 0, habilidades_requeridas, 0, 0, 0, None, equipo_id, empleado_id, idCardTrello))
        conn.commit()
        tarea_id = cursor.lastrowid
        cursor.execute("SELECT t.*, eq.nombre as equipo_nombre FROM tareas_trello t LEFT JOIN equipos eq ON t.equipo_id = eq.id WHERE t.id = %s", (tarea_id,))
        tarea = cursor.fetchone()
        cursor.close()
        conn.close()
        # Renderizar la nueva fila de la tabla como HTML
        tarea_html = render_template_string('''
        <tr class="modern-row-nueva">
            <td class="fw-semibold">{{ tarea.titulo }}</td>
            <td>
                <span class="badge bg-gradient-info text-white px-3 py-2 shadow-sm animate__animated animate__fadeInRight">
                    {{ tarea.estado|capitalize if tarea.estado else 'Pendiente' }}
                </span>
            </td>
            <td>
                <span class="badge px-3 py-2 shadow-sm animate__animated animate__fadeInRight {{ 'bg-gradient-danger' if tarea.prioridad=='alta' else 'bg-gradient-warning' if tarea.prioridad=='media' else 'bg-gradient-success' }}">
                    <i class="fas fa-{{ 'exclamation-triangle' if tarea.prioridad=='alta' else 'exclamation-circle' if tarea.prioridad=='media' else 'check-circle' }} me-1"></i>
                    {{ tarea.prioridad|capitalize }}
                </span>
            </td>
            <td>
                {% if tarea.equipo_nombre %}
                    <span class="badge bg-primary">{{ tarea.equipo_nombre }}</span>
                {% else %}
                    <span class="text-muted">Sin equipo</span>
                {% endif %}
            </td>
            <td>
                <button class="btn btn-sm btn-info modern-btn-action-nueva me-1" onclick="verDetalles({{ tarea.id }})" title="Ver detalles">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        </tr>
        ''', tarea=tarea)
        if empleado_id:
            crear_y_emitir_notificacion(int(empleado_id), f'Se te ha asignado una nueva tarea: {titulo}', 'tarea')
        return jsonify({'success': True, 'tarea_html': tarea_html})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Rutas para asignación automática
@tareas_bp.route('/tareas/asignar-automatico')
def asignar_automatico():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener tareas pendientes
    cursor.execute('SELECT * FROM tareas_trello WHERE estado = "pendiente"')
    tareas_pendientes = cursor.fetchall()
    
    # Obtener empleados disponibles
    cursor.execute('''
        SELECT e.*, 
               COUNT(a.id) as tareas_asignadas,
               SUM(t.horas_estimadas) as horas_asignadas
        FROM empleados e
        LEFT JOIN asignaciones a ON e.id = a.empleado_id
        LEFT JOIN tareas_trello t ON a.tarea_id = t.id
        GROUP BY e.id
    ''')
    empleados = cursor.fetchall()
    
    # Lógica de asignación automática
    for tarea in tareas_pendientes:
        mejor_empleado = None
        mejor_puntuacion = float('inf')
        
        for empleado in empleados:
            # Calcular puntuación basada en:
            # 1. Carga de trabajo actual
            # 2. Habilidades requeridas
            # 3. Disponibilidad de horas
            puntuacion = calcular_puntuacion(empleado, tarea)
            
            if puntuacion < mejor_puntuacion:
                mejor_puntuacion = puntuacion
                mejor_empleado = empleado
        
        if mejor_empleado:
            # Asignar tarea
            cursor.execute('''
                INSERT INTO asignaciones (empleado_id, tarea_id, fecha_asignacion)
                VALUES (%s, %s, %s)
            ''', (mejor_empleado['id'], tarea['id'], datetime.now()))
            
            # Actualizar estado de la tarea
            cursor.execute('''
                UPDATE tareas_trello SET estado = "en_progreso"
                WHERE id = %s
            ''', (tarea['id'],))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Tareas asignadas automáticamente', 'success')
    return redirect(url_for('equipos.lista_equipos'))

def calcular_puntuacion(empleado, tarea):
    # Implementar lógica de puntuación basada en:
    # - Carga de trabajo actual
    # - Habilidades requeridas
    # - Disponibilidad de horas
    puntuacion = 0
    
    # Factor de carga de trabajo
    carga_trabajo = empleado['horas_asignadas'] or 0
    puntuacion += carga_trabajo * 2
    
    # Factor de habilidades
    habilidades_requeridas = set(tarea['habilidades_requeridas'].split(','))
    habilidades_empleado = set(empleado['habilidades'].split(','))
    habilidades_faltantes = len(habilidades_requeridas - habilidades_empleado)
    puntuacion += habilidades_faltantes * 10
    
    return puntuacion 

@tareas_bp.route('/tareas/iniciar_temporizador/<int:tarea_id>', methods=['POST'])
def iniciar_temporizador(tarea_id):
    conn = get_connection()
    cursor = conn.cursor()
    # Marcar temporizador como activo y guardar hora de inicio
    cursor.execute('UPDATE tareas_trello SET temporizador_activo=1, inicio_temporizador=%s WHERE id=%s', (datetime.now(), tarea_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@tareas_bp.route('/tareas/pausar_temporizador/<int:tarea_id>', methods=['POST'])
def pausar_temporizador(tarea_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT inicio_temporizador, tiempo_real FROM tareas_trello WHERE id=%s', (tarea_id,))
    tarea = cursor.fetchone()
    if tarea and tarea['inicio_temporizador']:
        tiempo_transcurrido = int((datetime.now() - tarea['inicio_temporizador']).total_seconds() // 60)
        nuevo_tiempo_real = (tarea['tiempo_real'] or 0) + tiempo_transcurrido
        cursor.execute('UPDATE tareas_trello SET temporizador_activo=0, inicio_temporizador=NULL, tiempo_real=%s WHERE id=%s', (nuevo_tiempo_real, tarea_id))
        conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'tiempo_real': nuevo_tiempo_real})

@tareas_bp.route('/tareas/actualizar_tiempo_real/<int:tarea_id>', methods=['POST'])
def actualizar_tiempo_real(tarea_id):
    nuevo_tiempo = request.json.get('tiempo_real')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE tareas_trello SET tiempo_real=%s WHERE id=%s', (nuevo_tiempo, tarea_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@tareas_bp.route('/tareas/asignar-equitativamente', methods=['GET'])
def asignar_equitativamente():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # Obtener tareas pendientes
    cursor.execute('SELECT * FROM tareas_trello WHERE estado = "pendiente"')
    tareas_pendientes = cursor.fetchall()
    # Obtener empleados disponibles (líderes y practicantes)
    cursor.execute('''
        SELECT e.id, e.nombre, e.apellido, e.rol, e.equipo_id,
               COUNT(a.id) as tareas_asignadas
        FROM empleados e
        LEFT JOIN asignaciones a ON e.id = a.empleado_id AND a.estado != "completada"
        WHERE e.rol IN ("lider", "practicante")
        GROUP BY e.id
    ''')
    empleados = cursor.fetchall()
    # Reparto equitativo: asignar cada tarea al empleado con menos tareas activas
    sugerencia_plan = []
    for tarea in tareas_pendientes:
        empleado_menos_cargado = min(empleados, key=lambda e: e['tareas_asignadas'])
        sugerencia_plan.append({
            'tarea_id': tarea['id'],
            'tarea_titulo': tarea['titulo'],
            'empleado_id': empleado_menos_cargado['id'],
            'empleado_nombre': f"{empleado_menos_cargado['nombre']} {empleado_menos_cargado['apellido']}",
            'empleado_rol': empleado_menos_cargado['rol']
        })
        empleado_menos_cargado['tareas_asignadas'] += 1
    # Agrupar por empleado para el frontend
    agrupado = {}
    for asignacion in sugerencia_plan:
        nombre = asignacion['empleado_nombre']
        if nombre not in agrupado:
            agrupado[nombre] = {'nombre': nombre, 'tareas': []}
        agrupado[nombre]['tareas'].append(asignacion['tarea_titulo'])
    sugerencia = list(agrupado.values())
    cursor.close()
    conn.close()
    return jsonify({'sugerencia': sugerencia, 'sugerencia_plana': sugerencia_plan})

@tareas_bp.route('/tareas/confirmar-asignacion-equitativa', methods=['POST'])
def confirmar_asignacion_equitativa():
    data = request.json
    asignaciones = data.get('asignaciones', [])
    if not asignaciones:
        return jsonify({'success': False, 'message': 'No se recibieron asignaciones.'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for asignacion in asignaciones:
            tarea_id = asignacion['tarea_id']
            empleado_id = asignacion['empleado_id']
            # Insertar en la tabla de asignaciones
            cursor.execute('''
                INSERT INTO asignaciones (empleado_id, tarea_id, fecha_asignacion, estado)
                VALUES (%s, %s, %s, %s)
            ''', (empleado_id, tarea_id, datetime.now(), 'asignada'))
            # Actualizar estado de la tarea
            cursor.execute('UPDATE tareas_trello SET estado = %s WHERE id = %s', ('en_progreso', tarea_id))
            # Notificar a los asignados de la tarea
            cursor = get_connection().cursor(dictionary=True)
            cursor.execute('SELECT empleado_id FROM tareas_trello WHERE id = %s', (tarea_id,))
            tarea = cursor.fetchone()
            if tarea and tarea['empleado_id']:
                crear_y_emitir_notificacion(tarea['empleado_id'], f'Se te ha asignado una tarea: {tarea_id}', 'tarea')
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': f'Error al asignar tareas: {str(e)}'}), 500
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'message': 'Tareas asignadas exitosamente.'})

@tareas_bp.route('/tareas/detalles/<int:tarea_id>')
def detalles_tarea(tarea_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT t.*, eq.nombre as equipo_nombre, e.nombre as asignado_nombre, e.apellido as asignado_apellido
        FROM tareas_trello t
        LEFT JOIN equipos eq ON t.equipo_id = eq.id
        LEFT JOIN empleados e ON t.empleado_id = e.id
        WHERE t.id = %s
    ''', (tarea_id,))
    tarea = cursor.fetchone()
    cursor.execute('SELECT * FROM archivos_tarea WHERE tarea_id = %s ORDER BY fecha_subida DESC', (tarea_id,))
    adjuntos = cursor.fetchall()
    # Obtener adjuntos de Trello si corresponde
    adjuntos_trello = []
    if tarea and tarea.get('idCardTrello'):
        url = f"https://api.trello.com/1/cards/{tarea['idCardTrello']}/attachments"
        params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
        try:
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                for att in resp.json():
                    adjuntos_trello.append({
                        'id': att['id'],
                        'nombre_archivo': att['name'],
                        'tipo_archivo': att['mimeType'] if 'mimeType' in att else 'otro',
                        'url': att['url'],
                        'fuente': 'trello',
                        'fecha': att.get('date', None)
                    })
        except Exception as e:
            print('Error obteniendo adjuntos de Trello:', str(e))
    cursor.close()
    conn.close()
    return jsonify({
        'success': True,
        'tarea': tarea,
        'adjuntos': adjuntos,
        'adjuntos_trello': adjuntos_trello
    })

def mover_tarjeta_a_hecho(idCardTrello, equipo_id):
    # Obtener el idListDone del equipo
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT idBoard, idListDone FROM equipos WHERE id = %s', (equipo_id,))
    row = cursor.fetchone()
    conn.close()
    idListDone = row['idListDone'] if row else None
    idBoard = row['idBoard'] if row else None
    # Si no hay idListDone, buscar la lista 'Completado' en Trello
    if not idListDone and idBoard:
        url_lists = f"https://api.trello.com/1/boards/{idBoard}/lists"
        params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
        resp = requests.get(url_lists, params=params)
        if resp.status_code == 200:
            listas = resp.json()
            for lista in listas:
                if lista['name'].strip().lower() in ['completado', 'hecho', 'done']:
                    idListDone = lista['id']
                    break
    if not idListDone:
        print('No se encontró la lista Completado para este equipo.')
        return False
    url = f"https://api.trello.com/1/cards/{idCardTrello}"
    params = {
        "idList": idListDone,
        "key": TRELLO_API_KEY,
        "token": TRELLO_API_TOKEN
    }
    resp = requests.put(url, params=params)
    if resp.status_code == 200:
        return True
    else:
        print('Error al mover tarjeta en Trello:', resp.text)
        return False

@tareas_bp.route('/tareas/completar/<int:tarea_id>', methods=['POST'])
def completar_tarea(tarea_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT idCardTrello, equipo_id FROM tareas_trello WHERE id = %s', (tarea_id,))
    tarea = cursor.fetchone()
    if tarea and tarea['idCardTrello']:
        mover_tarjeta_a_hecho(tarea['idCardTrello'], tarea['equipo_id'])
    cursor = conn.cursor()
    cursor.execute('UPDATE tareas_trello SET estado = %s WHERE id = %s', ('completada', tarea_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Tarea marcada como completada y sincronizada con Trello.', 'success')
    cursor = get_connection().cursor(dictionary=True)
    cursor.execute('SELECT empleado_id FROM tareas_trello WHERE id = %s', (tarea_id,))
    tarea = cursor.fetchone()
    if tarea and tarea['empleado_id']:
        crear_y_emitir_notificacion(tarea['empleado_id'], f'Tu tarea ha sido marcada como completada.', 'tarea')
    return redirect(url_for('equipos')) 

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE_MB = 10
UPLOAD_FOLDER = 'uploads/archivos_tarea'

# Asegurar que la carpeta de uploads exista
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def subir_archivo_a_trello(idCardTrello, file_path, file_name):
    url = f"https://api.trello.com/1/cards/{idCardTrello}/attachments"
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_API_TOKEN
    }
    with open(file_path, 'rb') as f:
        files = {'file': (file_name, f)}
        resp = requests.post(url, params=params, files=files)
    if resp.status_code == 200:
        return resp.json().get('id')  # Devolver id del adjunto Trello
    return None

@tareas_bp.route('/tareas/<int:tarea_id>/adjuntos', methods=['POST'])
def subir_adjunto_tarea(tarea_id):
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'message': 'No se envió ningún archivo.'}), 400
        archivo = request.files['archivo']
        if archivo.filename == '':
            return jsonify({'success': False, 'message': 'Nombre de archivo vacío.'}), 400
        if not allowed_file(archivo.filename):
            return jsonify({'success': False, 'message': 'Tipo de archivo no permitido.'}), 400

        # Obtener información de la tarea y el usuario actual
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Verificar si la tarea existe y obtener su idCardTrello
        cursor.execute('SELECT idCardTrello, empleado_id FROM tareas_trello WHERE id = %s', (tarea_id,))
        tarea = cursor.fetchone()
        if not tarea:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'La tarea no existe.'}), 404

        # Crear directorio si no existe
        upload_folder = os.path.join('uploads', str(tarea_id))
        os.makedirs(upload_folder, exist_ok=True)
        # Guardar archivo localmente
        filename = secure_filename(archivo.filename)
        file_path = os.path.join(upload_folder, filename)
        archivo.save(file_path)
        # Subir a Trello si hay idCardTrello
        id_attachment_trello = None
        if tarea['idCardTrello']:
            id_attachment_trello = subir_archivo_a_trello(tarea['idCardTrello'], file_path, filename)
        # Obtener el tipo de archivo
        extension = os.path.splitext(filename)[1].lower()
        tipo_archivo = 'otro'
        if extension in ['.pdf']:
            tipo_archivo = 'pdf'
        elif extension in ['.doc', '.docx']:
            tipo_archivo = 'word'
        elif extension in ['.xls', '.xlsx']:
            tipo_archivo = 'excel'
        elif extension in ['.jpg', '.jpeg', '.png', '.gif']:
            tipo_archivo = 'image'
        # Insertar en la base de datos con usuario_id
        cursor.execute('''
            INSERT INTO archivos_tarea 
            (tarea_id, nombre_archivo, tipo_archivo, ruta_archivo, usuario_id, id_attachment_trello)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (tarea_id, filename, tipo_archivo, file_path, current_user.id, id_attachment_trello))
        conn.commit()
        adjunto_id = cursor.lastrowid
        # Obtener información del archivo recién subido
        cursor.execute('''
            SELECT id, nombre_archivo, tipo_archivo 
            FROM archivos_tarea 
            WHERE id = %s
        ''', (adjunto_id,))
        adjunto = cursor.fetchone()
        # Notificar a los asignados de la tarea (antes de cerrar la conexión)
        if tarea.get('empleado_id'):
            crear_y_emitir_notificacion(tarea['empleado_id'], f'Se ha subido un archivo a tu tarea.', 'archivo')
        cursor.close()
        conn.close()
        # Devolver HTML para el nuevo adjunto
        adjunto_html = f'''
        <li id="adjunto-{adjunto['id']}">
            <a href="/tareas/descargar-adjunto/{adjunto['id']}" target="_blank">
                <i class="fas fa-file-{adjunto['tipo_archivo']} me-1"></i>
                {adjunto['nombre_archivo']}
            </a>
            <button class="btn btn-sm btn-danger ms-2 btn-eliminar-adjunto" data-id="{adjunto['id']}">
                <i class="fas fa-trash"></i>
            </button>
        </li>
        '''
        return jsonify({
            'success': True, 
            'message': 'Archivo subido correctamente',
            'adjunto_html': adjunto_html
        })
    except Exception as e:
        print(f"Error al subir archivo: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error al subir archivo: {str(e)}'
        }), 500

def eliminar_adjunto_trello(idCardTrello, idAttachment):
    url = f"https://api.trello.com/1/cards/{idCardTrello}/attachments/{idAttachment}"
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_API_TOKEN
    }
    resp = requests.delete(url, params=params)
    return resp.status_code == 200

@tareas_bp.route('/tareas/eliminar-adjunto/<adjunto_id>', methods=['POST'])
@login_required
def eliminar_adjunto_universal(adjunto_id):
    origen = request.args.get('origen', 'sistema')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if origen == 'trello':
        # Buscar el idCardTrello en la base de datos usando el id_attachment_trello
        cursor.execute('SELECT t.idCardTrello FROM archivos_tarea a JOIN tareas_trello t ON a.tarea_id = t.id WHERE a.id_attachment_trello = %s', (adjunto_id,))
        row = cursor.fetchone()
        if not row or not row['idCardTrello']:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'No se encontró la tarjeta de Trello asociada.'}), 404
        idCardTrello = row['idCardTrello']
        # Eliminar adjunto en Trello
        eliminado = eliminar_adjunto_trello(idCardTrello, adjunto_id)
        if eliminado:
            # Eliminar de la base de datos
            cursor.execute('DELETE FROM archivos_tarea WHERE id_attachment_trello = %s', (adjunto_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Adjunto de Trello eliminado correctamente.'})
        else:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'No se pudo eliminar el adjunto de Trello.'}), 400
    else:
        # Lógica original para adjuntos del sistema
        try:
            adj_id = int(adjunto_id)
        except ValueError:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'ID de adjunto inválido.'}), 400
        cursor.close()
        conn.close()
        return eliminar_adjunto(adj_id)

def sync_trello_to_db():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # Obtener todos los equipos con idBoard
    cursor.execute('SELECT id, idBoard FROM equipos WHERE idBoard IS NOT NULL')
    equipos = cursor.fetchall()
    for equipo in equipos:
        idBoard = equipo['idBoard']
        equipo_id = equipo['id']
        # Obtener listas del tablero
        url_listas = f"https://api.trello.com/1/boards/{idBoard}/lists"
        params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
        resp = requests.get(url_listas, params=params)
        if resp.status_code != 200:
            continue
        listas = resp.json()
        lista_id_to_estado = {}
        for lista in listas:
            # Mapeo simple: nombre de la lista a estado
            nombre_lista = lista['name'].strip().lower()
            if 'pendiente' in nombre_lista:
                estado = 'pendiente'
            elif 'progreso' in nombre_lista:
                estado = 'en_progreso'
            elif 'completad' in nombre_lista or 'hecho' in nombre_lista:
                estado = 'completada'
            else:
                estado = 'pendiente'
            lista_id_to_estado[lista['id']] = estado
        for lista in listas:
            idList = lista['id']
            # Obtener tarjetas de la lista
            url_cards = f"https://api.trello.com/1/lists/{idList}/cards"
            resp_cards = requests.get(url_cards, params=params)
            if resp_cards.status_code != 200:
                continue
            cards = resp_cards.json()
            for card in cards:
                idCardTrello = card['id']
                nombre = card['name']
                descripcion = card.get('desc', '')
                estado = lista_id_to_estado.get(idList, 'pendiente')
                # Verificar si ya existe en tareas_trello
                cursor.execute('SELECT id, titulo, descripcion, estado FROM tareas_trello WHERE idCardTrello = %s', (idCardTrello,))
                row = cursor.fetchone()
                if not row:
                    # Insertar nueva tarea
                    cursor.execute('''
                        INSERT INTO tareas_trello (titulo, descripcion, fecha_creacion, estado, prioridad, equipo_id, idCardTrello)
                        VALUES (%s, %s, NOW(), %s, %s, %s, %s)
                    ''', (nombre, descripcion, estado, 'media', equipo_id, idCardTrello))
                else:
                    # Si existe, actualizar si hay cambios
                    if row['titulo'] != nombre or row['descripcion'] != descripcion or row['estado'] != estado:
                        cursor.execute('''
                            UPDATE tareas_trello SET titulo=%s, descripcion=%s, estado=%s WHERE id=%s
                        ''', (nombre, descripcion, estado, row['id']))
    conn.commit()
    cursor.close()
    conn.close()

@tareas_bp.route('/tareas', methods=['GET'])
@login_required
def listar_tareas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    buscar = request.args.get('buscar', '').strip()
    estado = request.args.get('estado', '')
    equipo_id = request.args.get('equipo_id', '')
    user_rol = current_user.rol
    user_equipo = current_user.equipo_id
    query = '''
        SELECT t.*, eq.nombre as equipo_nombre, e.nombre as asignado_nombre
        FROM tareas_trello t
        LEFT JOIN equipos eq ON t.equipo_id = eq.id
        LEFT JOIN empleados e ON t.empleado_id = e.id
        WHERE 1=1
    '''
    params = []
    if user_rol in ['practicante', 'lider']:
        query += ' AND t.equipo_id = %s'
        params.append(user_equipo)
    if buscar:
        query += ' AND t.titulo LIKE %s'
        params.append(f'%{buscar}%')
    if estado:
        query += ' AND t.estado = %s'
        params.append(estado)
    if equipo_id:
        query += ' AND t.equipo_id = %s'
        params.append(equipo_id)
    query += ' ORDER BY t.fecha_creacion DESC'
    cursor.execute(query, tuple(params))
    tareas = cursor.fetchall()
    cursor.execute('SELECT id, nombre FROM equipos ORDER BY nombre')
    equipos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('tareas_listar.html', tareas=tareas, equipos=equipos, user_rol=user_rol)

# Endpoint para sincronizar Trello manualmente o en background
@tareas_bp.route('/tareas/sincronizar_trello', methods=['POST'])
@login_required
def sincronizar_trello():
    try:
        sync_trello_to_db()
        return jsonify({'success': True, 'message': 'Sincronización con Trello completada.'})
    except Exception as e:
        import traceback
        print('Error en sincronizar_trello:', str(e))
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@tareas_bp.route('/tareas/sincronizar_trello_equipo/<int:equipo_id>', methods=['POST'])
@login_required
def sincronizar_trello_equipo(equipo_id):
    try:
        # Obtener idBoard del equipo
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT idBoard FROM equipos WHERE id = %s', (equipo_id,))
        row = cursor.fetchone()
        if not row or not row['idBoard']:
            conn.close()
            return jsonify({'success': False, 'message': 'El equipo no tiene tablero Trello vinculado.'}), 400
        idBoard = row['idBoard']
        # Obtener listas del tablero
        url_listas = f"https://api.trello.com/1/boards/{idBoard}/lists"
        params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
        resp = requests.get(url_listas, params=params)
        if resp.status_code != 200:
            conn.close()
            return jsonify({'success': False, 'message': 'No se pudieron obtener las listas de Trello.'}), 500
        listas = resp.json()
        lista_id_to_estado = {}
        for lista in listas:
            nombre_lista = lista['name'].strip().lower()
            if 'pendiente' in nombre_lista:
                estado = 'pendiente'
            elif 'progreso' in nombre_lista:
                estado = 'en_progreso'
            elif 'completad' in nombre_lista or 'hecho' in nombre_lista:
                estado = 'completada'
            else:
                estado = 'pendiente'
            lista_id_to_estado[lista['id']] = estado
        for lista in listas:
            idList = lista['id']
            url_cards = f"https://api.trello.com/1/lists/{idList}/cards"
            resp_cards = requests.get(url_cards, params=params)
            if resp_cards.status_code != 200:
                continue
            cards = resp_cards.json()
            for card in cards:
                idCardTrello = card['id']
                nombre = card['name']
                descripcion = card.get('desc', '')
                estado = lista_id_to_estado.get(idList, 'pendiente')
                cursor.execute('SELECT id, titulo, descripcion, estado FROM tareas_trello WHERE idCardTrello = %s', (idCardTrello,))
                row = cursor.fetchone()
                if not row:
                    cursor.execute('''
                        INSERT INTO tareas_trello (titulo, descripcion, fecha_creacion, estado, prioridad, equipo_id, idCardTrello)
                        VALUES (%s, %s, NOW(), %s, %s, %s, %s)
                    ''', (nombre, descripcion, estado, 'media', equipo_id, idCardTrello))
                else:
                    if row['titulo'] != nombre or row['descripcion'] != descripcion or row['estado'] != estado:
                        cursor.execute('''
                            UPDATE tareas_trello SET titulo=%s, descripcion=%s, estado=%s WHERE id=%s
                        ''', (nombre, descripcion, estado, row['id']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Sincronización con Trello completada.'})
    except Exception as e:
        import traceback
        print('Error en sincronizar_trello_equipo:', str(e))
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@tareas_bp.route('/tareas/nueva-form', methods=['GET', 'POST'])
def nueva_tarea_form():
    from flask_login import current_user
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        fecha_limite = request.form['fecha_limite']
        prioridad = request.form['prioridad']
        equipo_id = request.form['equipo_id']
        empleado_id = request.form.get('asignado_a') or None
        habilidades_requeridas = request.form.get('habilidades_requeridas', '')
        # Obtener idBoard del equipo
        cursor.execute('SELECT idBoard FROM equipos WHERE id = %s', (equipo_id,))
        row = cursor.fetchone()
        idBoard = row['idBoard'] if row else None
        idCardTrello = None
        if idBoard:
            idCardTrello = crear_tarjeta_trello(idBoard, titulo, descripcion)
        cursor.execute('''
            INSERT INTO tareas_trello (titulo, descripcion, fecha_creacion, fecha_limite, prioridad, horas_estimadas, habilidades_requeridas, tiempo_estimado, tiempo_real, temporizador_activo, inicio_temporizador, equipo_id, empleado_id, idCardTrello)
            VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (titulo, descripcion, fecha_limite, prioridad, 0, habilidades_requeridas, 0, 0, 0, None, equipo_id, empleado_id, idCardTrello))
        conn.commit()
        flash('Tarea creada y sincronizada con Trello.', 'success')
        return redirect(url_for('tareas.listar_tareas'))
    # GET: mostrar formulario
    user_rol = current_user.rol
    user_equipo = current_user.equipo_id
    if user_rol == 'lider':
        cursor.execute('SELECT id, nombre FROM equipos WHERE id = %s', (user_equipo,))
        equipos = cursor.fetchall()
        cursor.execute('SELECT id, nombre, apellido, equipo_id FROM empleados WHERE equipo_id = %s ORDER BY nombre', (user_equipo,))
        empleados = cursor.fetchall()
    else:  # jefe
        cursor.execute('SELECT id, nombre FROM equipos ORDER BY nombre')
        equipos = cursor.fetchall()
        cursor.execute('SELECT id, nombre, apellido, equipo_id FROM empleados ORDER BY nombre')
        empleados = cursor.fetchall()
    # Construir el diccionario equipo_usuarios
    equipo_usuarios = {}
    for emp in empleados:
        if emp['equipo_id']:
            equipo_usuarios.setdefault(emp['equipo_id'], []).append({'id': emp['id'], 'nombre': emp['nombre'], 'apellido': emp['apellido']})
    cursor.close()
    conn.close()
    return render_template('tareas_nueva.html', equipos=equipos, empleados=empleados, equipo_usuarios=equipo_usuarios, user_rol=user_rol, user_equipo=user_equipo)

@tareas_bp.route('/tareas/descargar-adjunto/<int:adjunto_id>')
def descargar_adjunto(adjunto_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT ruta_archivo, nombre_archivo FROM archivos_tarea WHERE id = %s', (adjunto_id,))
    adjunto = cursor.fetchone()
    cursor.close()
    conn.close()
    if not adjunto or not os.path.exists(adjunto['ruta_archivo']):
        abort(404)
    return send_file(adjunto['ruta_archivo'], as_attachment=True, download_name=adjunto['nombre_archivo'])

# Ruta para servir archivos subidos
@tareas_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(current_app.root_path, 'uploads'), filename)

def agregar_comentario_trello(idCardTrello, comentario):
    url = f"https://api.trello.com/1/cards/{idCardTrello}/actions/comments"
    params = {
        "text": comentario,
        "key": TRELLO_API_KEY,
        "token": TRELLO_API_TOKEN
    }
    resp = requests.post(url, params=params)
    if resp.status_code == 200:
        return resp.json().get('id')  # id del comentario en Trello
    return None

def editar_comentario_trello(idCardTrello, idCommentTrello, nuevo_comentario):
    url = f"https://api.trello.com/1/cards/{idCardTrello}/actions/{idCommentTrello}/comments"
    params = {
        "text": nuevo_comentario,
        "key": TRELLO_API_KEY,
        "token": TRELLO_API_TOKEN
    }
    resp = requests.put(url, params=params)
    return resp.status_code == 200

def eliminar_comentario_trello(idCardTrello, idCommentTrello):
    url = f"https://api.trello.com/1/cards/{idCardTrello}/actions/{idCommentTrello}/comments"
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_API_TOKEN
    }
    resp = requests.delete(url, params=params)
    return resp.status_code == 200

@tareas_bp.route('/tareas/<int:tarea_id>/comentarios', methods=['GET'])
@login_required
def listar_comentarios_tarea(tarea_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener idCardTrello de la tarea
        cursor.execute('SELECT idCardTrello FROM tareas_trello WHERE id = %s', (tarea_id,))
        row = cursor.fetchone()
        idCardTrello = row['idCardTrello'] if row else None
        # Comentarios del sistema
        cursor.execute('''
            SELECT c.id, c.comentario, c.fecha, c.usuario_id, e.nombre, e.apellido, e.rol, c.id_comment_trello
            FROM comentarios_tarea c
            JOIN empleados e ON c.usuario_id = e.id
            WHERE c.tarea_id = %s
            ORDER BY c.fecha ASC
        ''', (tarea_id,))
        comentarios_db = cursor.fetchall()
        comentarios = []
        ids_trello_db = set()
        for c in comentarios_db:
            if c['id_comment_trello']:
                ids_trello_db.add(c['id_comment_trello'])
            c['fuente'] = 'sistema'
            c['puede_editar'] = (c['usuario_id'] == current_user.id or current_user.rol == 'jefe')
            c['puede_eliminar'] = (c['usuario_id'] == current_user.id or current_user.rol == 'jefe')
            comentarios.append(c)
        # Comentarios de Trello: sincronizar con la base local
        if idCardTrello:
            url = f"https://api.trello.com/1/cards/{idCardTrello}/actions"
            params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN, "filter": "commentCard"}
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                for action in resp.json():
                    id_comment_trello = action['id']
                    if id_comment_trello in ids_trello_db:
                        continue  # Ya está en la base de datos
                    # Insertar comentario de Trello en la base local
                    cursor.execute('''
                        INSERT INTO comentarios_tarea (tarea_id, usuario_id, comentario, fecha, id_comment_trello)
                        VALUES (%s, NULL, %s, %s, %s)
                    ''', (tarea_id, action['data']['text'], action['date'], id_comment_trello))
                    conn.commit()
                    comentarios.append({
                        'id': None,
                        'comentario': action['data']['text'],
                        'fecha': action['date'],
                        'usuario_id': None,
                        'nombre': action['memberCreator']['fullName'],
                        'apellido': '',
                        'rol': 'Trello',
                        'id_comment_trello': id_comment_trello,
                        'fuente': 'trello',
                        'puede_editar': False,
                        'puede_eliminar': False
                    })
        # Volver a consultar todos los comentarios (incluyendo los recién insertados)
        cursor.execute('''
            SELECT c.id, c.comentario, c.fecha, c.usuario_id, e.nombre, e.apellido, e.rol, c.id_comment_trello
            FROM comentarios_tarea c
            LEFT JOIN empleados e ON c.usuario_id = e.id
            WHERE c.tarea_id = %s
            ORDER BY c.fecha ASC
        ''', (tarea_id,))
        comentarios = []
        for c in cursor.fetchall():
            c['fuente'] = 'trello' if c['usuario_id'] is None else 'sistema'
            c['puede_editar'] = (c['usuario_id'] == current_user.id or current_user.rol == 'jefe') if c['usuario_id'] else False
            c['puede_eliminar'] = (c['usuario_id'] == current_user.id or current_user.rol == 'jefe') if c['usuario_id'] else False
            comentarios.append(c)
        cursor.close()
        conn.close()
        # Ordenar por fecha
        comentarios.sort(key=lambda x: x['fecha'])
        return jsonify(comentarios)
    except Exception as e:
        import traceback
        print('Error interno en listar_comentarios_tarea:', str(e))
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

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
        tarea = cursor.fetchone()
        if not tarea:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'La tarea no existe.'}), 404
        idCardTrello = tarea['idCardTrello']
        idCommentTrello = None
        if idCardTrello:
            idCommentTrello = agregar_comentario_trello(idCardTrello, comentario)
        cursor.execute('''
            INSERT INTO comentarios_tarea (tarea_id, usuario_id, comentario, id_comment_trello)
            VALUES (%s, %s, %s, %s)
        ''', (tarea_id, current_user.id, comentario, idCommentTrello))
        conn.commit()
        # Notificar a los asignados de la tarea ANTES de cerrar la conexión
        cursor.execute('SELECT empleado_id FROM tareas_trello WHERE id = %s', (tarea_id,))
        tarea = cursor.fetchone()
        if tarea and tarea['empleado_id'] and tarea['empleado_id'] != current_user.id:
            crear_y_emitir_notificacion(tarea['empleado_id'], f'Nuevo comentario en tu tarea.', 'comentario')
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        print('Error interno en agregar_comentario_tarea:', str(e))
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@tareas_bp.route('/comentarios/<int:comentario_id>', methods=['DELETE'])
@login_required
def eliminar_comentario_tarea(comentario_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT c.usuario_id, c.id_comment_trello, t.idCardTrello FROM comentarios_tarea c JOIN tareas_trello t ON c.tarea_id = t.id WHERE c.id = %s', (comentario_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Comentario no encontrado.'}), 404
    if row['usuario_id'] != current_user.id and current_user.rol != 'jefe':
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'No tienes permiso para eliminar este comentario.'}), 403
    if row['id_comment_trello'] and row['idCardTrello']:
        eliminar_comentario_trello(row['idCardTrello'], row['id_comment_trello'])
    cursor.execute('DELETE FROM comentarios_tarea WHERE id = %s', (comentario_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@tareas_bp.route('/comentarios/<int:comentario_id>', methods=['PUT'])
@login_required
def editar_comentario_tarea(comentario_id):
    data = request.get_json()
    nuevo_comentario = data.get('comentario', '').strip()
    if not nuevo_comentario:
        return jsonify({'success': False, 'message': 'El comentario no puede estar vacío.'}), 400
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT c.usuario_id, c.id_comment_trello, t.idCardTrello FROM comentarios_tarea c JOIN tareas_trello t ON c.tarea_id = t.id WHERE c.id = %s', (comentario_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Comentario no encontrado.'}), 404
    if row['usuario_id'] != current_user.id and current_user.rol != 'jefe':
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'No tienes permiso para editar este comentario.'}), 403
    if row['id_comment_trello'] and row['idCardTrello']:
        editar_comentario_trello(row['idCardTrello'], row['id_comment_trello'], nuevo_comentario)
    cursor.execute('UPDATE comentarios_tarea SET comentario = %s WHERE id = %s', (nuevo_comentario, comentario_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@tareas_bp.route('/tareas/eliminar/<int:tarea_id>', methods=['POST'])
@login_required
def eliminar_tarea(tarea_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # Obtener idCardTrello antes de eliminar
    cursor.execute('SELECT idCardTrello FROM tareas_trello WHERE id = %s', (tarea_id,))
    tarea = cursor.fetchone()
    if not tarea:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Tarea no encontrada.'}), 404
    idCardTrello = tarea['idCardTrello']
    # Eliminar en Trello si corresponde
    if idCardTrello:
        url = f"https://api.trello.com/1/cards/{idCardTrello}"
        params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
        requests.delete(url, params=params)
    # Eliminar de la base de datos
    cursor.execute('DELETE FROM tareas_trello WHERE id = %s', (tarea_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'message': 'Tarea eliminada correctamente.'}) 