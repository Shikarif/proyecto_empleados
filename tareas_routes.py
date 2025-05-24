from flask import Blueprint, render_template, request, redirect, url_for, flash
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
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tareas (titulo, descripcion, fecha_creacion, fecha_limite, 
                              prioridad, horas_estimadas, habilidades_requeridas)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (titulo, descripcion, datetime.now(), fecha_limite, 
              prioridad, horas_estimadas, habilidades_requeridas))
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