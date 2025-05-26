from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from db_config import get_connection
from datetime import datetime

tareas_bp = Blueprint('tareas', __name__)

# Rutas para gestión de tareas
@tareas_bp.route('/tareas')
def listar_tareas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM tareas ORDER BY fecha_limite')
    tareas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('tareas/lista.html', tareas=tareas)

@tareas_bp.route('/tareas/nueva', methods=['GET', 'POST'])
def nueva_tarea():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        fecha_limite = request.form['fecha_limite']
        prioridad = request.form['prioridad']
        horas_estimadas = request.form['horas_estimadas']
        habilidades_requeridas = request.form['habilidades_requeridas']
        tiempo_estimado = request.form.get('tiempo_estimado', 0)
        # Al crear, tiempo_real es 0, temporizador inactivo
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tareas (titulo, descripcion, fecha_creacion, fecha_limite, 
                              prioridad, horas_estimadas, habilidades_requeridas, tiempo_estimado, tiempo_real, temporizador_activo, inicio_temporizador)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (titulo, descripcion, datetime.now(), fecha_limite, 
              prioridad, horas_estimadas, habilidades_requeridas, tiempo_estimado, 0, 0, None))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Tarea creada exitosamente', 'success')
        return redirect(url_for('tareas.listar_tareas'))
    return render_template('tareas/nueva.html')

# Rutas para asignación automática
@tareas_bp.route('/tareas/asignar-automatico')
def asignar_automatico():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener tareas pendientes
    cursor.execute('SELECT * FROM tareas WHERE estado = "pendiente"')
    tareas_pendientes = cursor.fetchall()
    
    # Obtener empleados disponibles
    cursor.execute('''
        SELECT e.*, 
               COUNT(a.id) as tareas_asignadas,
               SUM(t.horas_estimadas) as horas_asignadas
        FROM empleados e
        LEFT JOIN asignaciones a ON e.id = a.empleado_id
        LEFT JOIN tareas t ON a.tarea_id = t.id
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
                UPDATE tareas SET estado = "en_progreso"
                WHERE id = %s
            ''', (tarea['id'],))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Tareas asignadas automáticamente', 'success')
    return redirect(url_for('tareas.listar_tareas'))

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
    cursor.execute('UPDATE tareas SET temporizador_activo=1, inicio_temporizador=%s WHERE id=%s', (datetime.now(), tarea_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@tareas_bp.route('/tareas/pausar_temporizador/<int:tarea_id>', methods=['POST'])
def pausar_temporizador(tarea_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT inicio_temporizador, tiempo_real FROM tareas WHERE id=%s', (tarea_id,))
    tarea = cursor.fetchone()
    if tarea and tarea['inicio_temporizador']:
        tiempo_transcurrido = int((datetime.now() - tarea['inicio_temporizador']).total_seconds() // 60)
        nuevo_tiempo_real = (tarea['tiempo_real'] or 0) + tiempo_transcurrido
        cursor.execute('UPDATE tareas SET temporizador_activo=0, inicio_temporizador=NULL, tiempo_real=%s WHERE id=%s', (nuevo_tiempo_real, tarea_id))
        conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'tiempo_real': nuevo_tiempo_real})

@tareas_bp.route('/tareas/actualizar_tiempo_real/<int:tarea_id>', methods=['POST'])
def actualizar_tiempo_real(tarea_id):
    nuevo_tiempo = request.json.get('tiempo_real')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE tareas SET tiempo_real=%s WHERE id=%s', (nuevo_tiempo, tarea_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@tareas_bp.route('/tareas/asignar-equitativamente', methods=['GET'])
def asignar_equitativamente():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # Obtener tareas pendientes
    cursor.execute('SELECT * FROM tareas WHERE estado = "pendiente"')
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
            cursor.execute('UPDATE tareas SET estado = %s WHERE id = %s', ('en_progreso', tarea_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': f'Error al asignar tareas: {str(e)}'}), 500
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'message': 'Tareas asignadas exitosamente.'}) 