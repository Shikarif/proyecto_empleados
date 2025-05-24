from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from db_config import get_connection
from datetime import datetime
from tareas_routes import tareas_bp  # Importar el blueprint de tareas
import hashlib
import bcrypt
from collections import Counter
import re
from flask_login import login_required, current_user, LoginManager, UserMixin, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Necesario para los mensajes flash

# Registrar el blueprint de tareas
app.register_blueprint(tareas_bp)

# Inicializar LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo de usuario compatible con Flask-Login
class Usuario(UserMixin):
    pass

@login_manager.user_loader
def load_user(user_id):
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM empleados WHERE id = %s", (user_id,))
    usuario = cursor.fetchone()
    conexion.close()
    if usuario:
        user = Usuario()
        user.id = usuario['id']
        user.nombre = usuario['nombre']
        user.apellido = usuario['apellido']
        user.email = usuario['correo']
        user.rol = usuario['rol']
        user.telefono = usuario.get('telefono', '')
        user.password = usuario['password']
        # Puedes agregar más campos si los necesitas
        return user
    return None

@app.route('/')
@login_required
def index():
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM empleados WHERE rol IN ('lider', 'practicante') ORDER BY nombre")
    empleados = cursor.fetchall()
    conexion.close()
    return render_template('index.html', empleados=empleados)

@app.route('/buscar', methods=['GET'])
def buscar():
    query = request.args.get('q', '')
    rol_filtro = request.args.get('rol', '')
    conexion = get_connection()
    cursor = conexion.cursor()
    sql = "SELECT * FROM empleados WHERE rol IN ('lider', 'practicante')"
    params = []
    if query:
        sql += " AND (nombre LIKE %s OR apellido LIKE %s OR correo LIKE %s)"
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
    if rol_filtro:
        sql += " AND rol = %s"
        params.append(rol_filtro)
    sql += " ORDER BY nombre"
    cursor.execute(sql, tuple(params))
    empleados = cursor.fetchall()
    conexion.close()
    return render_template('index.html', empleados=empleados, query=query, rol_filtro=rol_filtro)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM equipos ORDER BY nombre")
    equipos = cursor.fetchall()
    roles = ['jefe', 'lider', 'practicante']

    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        correo = request.form['correo']
        telefono = request.form.get('telefono', '')
        equipo_id = request.form.get('equipo_id')
        rol = request.form.get('rol')
        habilidades = request.form.get('habilidades', '')
        fortalezas = request.form.get('fortalezas', '')
        horas_disponibles = request.form.get('horas_disponibles', 40)

        try:
            cursor.execute("""
                UPDATE empleados 
                SET nombre=%s, apellido=%s, correo=%s, telefono=%s, equipo_id=%s, rol=%s, habilidades=%s, horas_disponibles=%s
                WHERE id=%s
            """, (nombre, apellido, correo, telefono, equipo_id, rol, habilidades, horas_disponibles, id))
            # Actualizar fortalezas
            cursor.execute("DELETE FROM empleado_fortalezas WHERE empleado_id=%s", (id,))
            if rol in ['lider', 'practicante']:
                if habilidades:
                    habilidades_list = [h.strip() for h in habilidades.split(',') if h.strip()]
                    for habilidad in habilidades_list:
                        cursor.execute("SELECT id FROM habilidades WHERE nombre=%s", (habilidad,))
                        hab_row = cursor.fetchone()
                        if hab_row:
                            habilidad_id = hab_row['id']
                        else:
                            cursor.execute("INSERT INTO habilidades (nombre) VALUES (%s)", (habilidad,))
                            habilidad_id = cursor.lastrowid
                        cursor.execute("INSERT IGNORE INTO empleado_habilidades (empleado_id, habilidad_id) VALUES (%s, %s)", (id, habilidad_id))
                # Guardar fortalezas en la tabla relacional si se ingresan
                if fortalezas:
                    fortalezas_list = [f.strip() for f in fortalezas.split(',') if f.strip()]
                    for fortaleza in fortalezas_list:
                        cursor.execute("SELECT id FROM fortalezas WHERE nombre=%s", (fortaleza,))
                        fort_row = cursor.fetchone()
                        if fort_row:
                            fortaleza_id = fort_row['id']
                        else:
                            cursor.execute("INSERT INTO fortalezas (nombre) VALUES (%s)", (fortaleza,))
                            fortaleza_id = cursor.lastrowid
                        cursor.execute("INSERT IGNORE INTO empleado_fortalezas (empleado_id, fortaleza_id) VALUES (%s, %s)", (id, fortaleza_id))
            conexion.commit()
            flash('Empleado actualizado exitosamente!', 'success')
        except Exception as e:
            flash(f'Error al actualizar empleado: {str(e)}', 'danger')
        finally:
            conexion.close()
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM empleados WHERE id=%s", (id,))
    empleado = cursor.fetchone()
    # Obtener fortalezas actuales del empleado
    cursor.execute("""
        SELECT f.nombre FROM fortalezas f
        JOIN empleado_fortalezas ef ON f.id = ef.fortaleza_id
        WHERE ef.empleado_id = %s
    """, (id,))
    fortalezas_actuales = ', '.join([row['nombre'] for row in cursor.fetchall()])
    conexion.close()
    return render_template('editar.html', empleado=empleado, equipos=equipos, roles=roles, fortalezas_actuales=fortalezas_actuales)

@app.route('/eliminar/<int:id>')
def eliminar(id):
    try:
        conexion = get_connection()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM empleados WHERE id=%s", (id,))
        conexion.commit()
        flash('Empleado eliminado exitosamente!', 'success')
    except Exception as e:
        flash(f'Error al eliminar empleado: {str(e)}', 'danger')
    finally:
        conexion.close()
    return redirect(url_for('index'))

@app.route('/reiniciar', methods=['GET', 'POST'])
@login_required
def reiniciar():
    # Solo permitir acceso a jefes
    if current_user.rol != 'jefe':
        flash('No tienes permiso para acceder a esta función.', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        password = request.form.get('password')
        if not password:
            flash('Debes ingresar la contraseña especial.', 'danger')
            return render_template('reiniciar_confirmar.html')
        conexion = get_connection()
        cursor = conexion.cursor()
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'password_reinicio'")
        row = cursor.fetchone()
        if not row:
            flash('No se ha configurado la contraseña especial.', 'danger')
            conexion.close()
            return render_template('reiniciar_confirmar.html')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash != row[0]:
            flash('Contraseña incorrecta.', 'danger')
            conexion.close()
            return render_template('reiniciar_confirmar.html')
        try:
            # Obtener IDs de empleados a eliminar (lider y practicante)
            cursor.execute("SELECT id FROM empleados WHERE rol IN ('lider', 'practicante')")
            ids = [row[0] for row in cursor.fetchall()]
            if ids:
                ids_str = ','.join(str(i) for i in ids)
                # Borrar relaciones
                cursor.execute(f"DELETE FROM empleado_fortalezas WHERE empleado_id IN ({ids_str})")
                cursor.execute(f"DELETE FROM empleado_habilidades WHERE empleado_id IN ({ids_str})")
                cursor.execute(f"DELETE FROM asignaciones WHERE empleado_id IN ({ids_str})")
                # Actualizar tareas: dejar sin propietario
                cursor.execute(f"UPDATE tareas SET empleado_id = NULL WHERE empleado_id IN ({ids_str})")
                # Borrar empleados
                cursor.execute(f"DELETE FROM empleados WHERE id IN ({ids_str})")
            conexion.commit()
            flash('Base de datos reiniciada exitosamente (solo practicantes y líderes eliminados).', 'success')
        except Exception as e:
            flash(f'Error al reiniciar la base de datos: {str(e)}', 'danger')
        finally:
            conexion.close()
        return redirect(url_for('index'))
    # GET: mostrar formulario de confirmación
    return render_template('reiniciar_confirmar.html')

@app.route('/estadisticas')
def estadisticas():
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    
    # Total de empleados (solo líderes y practicantes)
    cursor.execute("SELECT COUNT(*) as total FROM empleados WHERE rol IN ('lider', 'practicante')")
    total_empleados = cursor.fetchone()['total']
    
    # Empleados por equipo (solo líderes y practicantes)
    cursor.execute("""
        SELECT e.nombre AS equipo, COUNT(emp.id) as total
        FROM equipos e
        LEFT JOIN empleados emp ON emp.equipo_id = e.id AND emp.rol IN ('lider', 'practicante')
        GROUP BY e.id, e.nombre
        ORDER BY total DESC
    """)
    empleados_por_equipo = cursor.fetchall()
    
    # Últimos empleados agregados (solo líderes y practicantes)
    cursor.execute("""
        SELECT * FROM empleados 
        WHERE rol IN ('lider', 'practicante')
        ORDER BY id DESC 
        LIMIT 5
    """)
    ultimos_agregados = cursor.fetchall()
    
    conexion.close()
    
    return render_template('estadisticas.html',
                         total_empleados=total_empleados,
                         empleados_por_equipo=empleados_por_equipo,
                         ultimos_agregados=ultimos_agregados)

@app.route('/equipos')
def equipos():
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    # Obtener todos los equipos
    cursor.execute("SELECT * FROM equipos ORDER BY nombre")
    equipos = cursor.fetchall()
    # Obtener miembros por equipo (solo líderes y practicantes)
    equipos_con_miembros = []
    for equipo in equipos:
        cursor.execute("""
            SELECT * FROM empleados WHERE equipo_id = %s AND rol IN ('lider', 'practicante')
        """, (equipo['id'],))
        miembros = cursor.fetchall()
        equipos_con_miembros.append({
            'id': equipo['id'],
            'nombre': equipo['nombre'],
            'miembros': miembros,
            'total': len(miembros)
        })
    conexion.close()
    return render_template('equipos.html', equipos=equipos_con_miembros)

@app.route('/equipos/nuevo', methods=['GET', 'POST'])
def agregar_equipo():
    if request.method == 'POST':
        nombre = request.form['nombre']
        try:
            conexion = get_connection()
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO equipos (nombre) VALUES (%s)", (nombre,))
            conexion.commit()
            conexion.close()
            flash('Equipo creado exitosamente!', 'success')
        except Exception as e:
            flash(f'Error al crear equipo: {str(e)}', 'danger')
        return redirect(url_for('equipos'))
    return render_template('agregar_equipo.html')

@app.route('/habilidades', methods=['GET', 'POST'])
def habilidades():
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form.get('descripcion', '')
        try:
            cursor.execute("INSERT INTO habilidades (nombre, descripcion) VALUES (%s, %s)", (nombre, descripcion))
            conexion.commit()
            flash('Habilidad agregada exitosamente!', 'success')
        except Exception as e:
            flash(f'Error al agregar habilidad: {str(e)}', 'danger')
    cursor.execute("SELECT * FROM habilidades ORDER BY nombre")
    habilidades = cursor.fetchall()
    conexion.close()
    return render_template('habilidades.html', habilidades=habilidades)

@app.route('/competencias')
def competencias():
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    # Obtener solo líderes y practicantes con equipo y rol
    cursor.execute("""
        SELECT emp.id, emp.nombre, emp.apellido, emp.rol, eq.nombre AS equipo
        FROM empleados emp
        LEFT JOIN equipos eq ON emp.equipo_id = eq.id
        WHERE emp.rol IN ('lider', 'practicante')
        ORDER BY emp.nombre, emp.apellido
    """)
    empleados = cursor.fetchall()
    # Obtener habilidades y fortalezas de cada empleado
    empleados_competencias = []
    for emp in empleados:
        cursor.execute("""
            SELECT h.id, h.nombre FROM habilidades h
            JOIN empleado_habilidades eh ON h.id = eh.habilidad_id
            WHERE eh.empleado_id = %s
        """, (emp['id'],))
        habilidades = [row['nombre'] for row in cursor.fetchall()]
        cursor.execute("""
            SELECT f.id, f.nombre FROM fortalezas f
            JOIN empleado_fortalezas ef ON f.id = ef.fortaleza_id
            WHERE ef.empleado_id = %s
        """, (emp['id'],))
        fortalezas = [row['nombre'] for row in cursor.fetchall()]
        empleados_competencias.append({
            'id': emp['id'],
            'nombre': emp['nombre'],
            'apellido': emp['apellido'],
            'rol': emp['rol'],
            'equipo': emp['equipo'],
            'habilidades': habilidades,
            'fortalezas': fortalezas
        })
    # Obtener todas las habilidades y fortalezas globales
    cursor.execute("SELECT id, nombre FROM habilidades ORDER BY nombre")
    habilidades_globales = cursor.fetchall()
    cursor.execute("SELECT id, nombre FROM fortalezas ORDER BY nombre")
    fortalezas_globales = cursor.fetchall()
    conexion.close()
    return render_template('competencias.html', empleados=empleados_competencias, habilidades_globales=habilidades_globales, fortalezas_globales=fortalezas_globales)

@app.route('/competencias/editar/<int:id>', methods=['POST'])
def editar_competencias(id):
    conexion = get_connection()
    cursor = conexion.cursor()
    habilidades = request.form.getlist('habilidades')
    fortalezas = request.form.getlist('fortalezas')
    # Actualizar habilidades
    cursor.execute("DELETE FROM empleado_habilidades WHERE empleado_id=%s", (id,))
    for hab_id in habilidades:
        cursor.execute("INSERT INTO empleado_habilidades (empleado_id, habilidad_id) VALUES (%s, %s)", (id, hab_id))
    # Actualizar fortalezas
    cursor.execute("DELETE FROM empleado_fortalezas WHERE empleado_id=%s", (id,))
    for fort_id in fortalezas:
        cursor.execute("INSERT INTO empleado_fortalezas (empleado_id, fortaleza_id) VALUES (%s, %s)", (id, fort_id))
    conexion.commit()
    conexion.close()
    flash('Competencias actualizadas correctamente.', 'success')
    return redirect(url_for('competencias'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        password = request.form.get('password')
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM empleados WHERE correo = %s", (correo,))
        usuario = cursor.fetchone()
        conexion.close()
        if usuario and bcrypt.checkpw(password.encode('utf-8'), usuario['password'].encode('utf-8')):
            # Crear instancia de Usuario (UserMixin)
            user = Usuario()
            user.id = usuario['id']
            user.nombre = usuario['nombre']
            user.apellido = usuario['apellido']
            user.email = usuario['correo']
            user.rol = usuario['rol']
            user.telefono = usuario.get('telefono', '')
            user.password = usuario['password']
            # Autenticar con Flask-Login
            login_user(user)
            # Registrar sesión activa
            conexion = get_connection()
            cursor = conexion.cursor()
            cursor.execute("""
                REPLACE INTO sesiones_activas (usuario_id, rol, ultima_actividad)
                VALUES (%s, %s, %s)
            """, (user.id, user.rol, datetime.now()))
            conexion.commit()
            conexion.close()
            flash('¡Bienvenido, {}! Has iniciado sesión correctamente.'.format(usuario['nombre']), 'success')
            return redirect(url_for('index'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
    
    # Obtener habilidades y fortalezas globales para el modal
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM habilidades ORDER BY nombre")
    habilidades_globales = cursor.fetchall()
    cursor.execute("SELECT * FROM fortalezas ORDER BY nombre")
    fortalezas_globales = cursor.fetchall()
    conexion.close()
    
    return render_template('login.html', 
                         habilidades_globales=habilidades_globales,
                         fortalezas_globales=fortalezas_globales)

@app.route('/verificar_competencias')
@login_required
def verificar_competencias():
    if current_user.rol not in ['lider', 'practicante']:
        return jsonify({'tiene_competencias': True})
    
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    
    # Verificar habilidades
    cursor.execute("""
        SELECT COUNT(*) as total FROM empleado_habilidades 
        WHERE empleado_id = %s
    """, (current_user.id,))
    tiene_habilidades = cursor.fetchone()['total'] > 0
    
    # Verificar fortalezas
    cursor.execute("""
        SELECT COUNT(*) as total FROM empleado_fortalezas 
        WHERE empleado_id = %s
    """, (current_user.id,))
    tiene_fortalezas = cursor.fetchone()['total'] > 0
    
    conexion.close()
    
    return jsonify({
        'tiene_competencias': tiene_habilidades and tiene_fortalezas
    })

@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    # Reutiliza la lógica de agregar empleado, pero desde /registrar
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM equipos ORDER BY nombre")
    equipos = cursor.fetchall()
    roles = ['jefe', 'lider', 'practicante']
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        correo = request.form['correo']
        telefono = request.form.get('telefono', '')
        equipo_id = request.form.get('equipo_id')
        rol = request.form.get('rol')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        
        if password != password2:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('registrar.html', equipos=equipos, roles=roles)
        
        if rol == 'jefe':
            cursor.execute("SELECT COUNT(*) as total FROM empleados WHERE rol = 'jefe'")
            total_jefes = cursor.fetchone()['total']
            if total_jefes >= 4:
                flash('No se pueden registrar más de 4 jefes.', 'danger')
                conexion.close()
                return render_template('registrar.html', equipos=equipos, roles=roles)
            # Si es jefe, no se asigna equipo
            equipo_id = None
        
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute("""
                INSERT INTO empleados 
                (nombre, apellido, correo, telefono, equipo_id, rol, password) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (nombre, apellido, correo, telefono, equipo_id, rol, password_hash))
            conexion.commit()
            flash('¡Registro exitoso, {}! Ahora puedes iniciar sesión.'.format(nombre), 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error al registrar: {str(e)}', 'danger')
        finally:
            conexion.close()
        return redirect(url_for('login'))
    conexion.close()
    return render_template('registrar.html', equipos=equipos, roles=roles)

@app.route('/logout')
def logout():
    # Eliminar sesión activa
    try:
        conexion = get_connection()
        cursor = conexion.cursor()
        if hasattr(current_user, 'id'):
            cursor.execute("DELETE FROM sesiones_activas WHERE usuario_id = %s", (current_user.id,))
            conexion.commit()
        conexion.close()
    except Exception as e:
        pass
    logout_user()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Limpiar sesiones inactivas antes de contar
    limpiar_sesiones_inactivas()
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    usuario_id = current_user.id
    rol = current_user.rol
    
    # Obtener información del usuario actual
    cursor.execute("""
        SELECT e.*, eq.nombre as equipo_nombre 
        FROM empleados e 
        LEFT JOIN equipos eq ON e.equipo_id = eq.id 
        WHERE e.id = %s
    """, (usuario_id,))
    usuario_actual = cursor.fetchone()
    
    # Tracking real de usuarios logueados
    cursor.execute("SELECT rol, COUNT(*) as total FROM sesiones_activas GROUP BY rol")
    roles_activos = {row['rol']: row['total'] for row in cursor.fetchall()}
    total_activos = sum(roles_activos.values())
    
    # Obtener estadísticas generales (solo líderes y practicantes)
    cursor.execute("SELECT COUNT(*) as total FROM empleados WHERE rol IN ('lider', 'practicante')")
    total_empleados = cursor.fetchone()['total']
    
    # Obtener empleados por rol (solo líderes y practicantes)
    cursor.execute("""
        SELECT rol, COUNT(*) as total 
        FROM empleados 
        WHERE rol IN ('lider', 'practicante')
        GROUP BY rol
    """)
    roles_stats = {row['rol']: row['total'] for row in cursor.fetchall()}
    
    # Datos específicos según el rol
    if rol == 'jefe':
        # Para jefes: ver todos los equipos y sus miembros (solo líderes y practicantes)
        cursor.execute("""
            SELECT e.*, eq.nombre as equipo_nombre 
            FROM empleados e 
            LEFT JOIN equipos eq ON e.equipo_id = eq.id 
            WHERE e.rol IN ('lider', 'practicante')
            ORDER BY e.nombre
        """)
        empleados = cursor.fetchall()
        # Equipos sin líder
        cursor.execute("""
            SELECT eq.*, COUNT(e.id) as total_miembros
            FROM equipos eq 
            LEFT JOIN empleados e ON eq.id = e.equipo_id AND e.rol IN ('lider', 'practicante')
            LEFT JOIN empleados l ON eq.id = l.equipo_id AND l.rol = 'lider'
            WHERE l.id IS NULL
            GROUP BY eq.id
        """)
        equipos_sin_lider = cursor.fetchall()
        # Estadísticas de equipos
        cursor.execute("""
            SELECT eq.id, eq.nombre,
                   SUM(CASE WHEN e.rol IN ('lider', 'practicante') THEN 1 ELSE 0 END) as total_miembros,
                   SUM(CASE WHEN e.rol = 'practicante' THEN 1 ELSE 0 END) as total_practicantes,
                   MAX(CASE WHEN e.rol = 'lider' THEN 1 ELSE 0 END) as tiene_lider
            FROM equipos eq
            LEFT JOIN empleados e ON eq.id = e.equipo_id
            GROUP BY eq.id, eq.nombre
        """)
        stats_equipos = cursor.fetchall()
        # Tareas por equipo
        cursor.execute("""
            SELECT eq.nombre as equipo,
                   COUNT(t.id) as total_tareas,
                   SUM(CASE WHEN t.estado = 'completada' THEN 1 ELSE 0 END) as tareas_completadas
            FROM equipos eq
            LEFT JOIN empleados e ON eq.id = e.equipo_id AND e.rol IN ('lider', 'practicante')
            LEFT JOIN tareas t ON e.id = t.empleado_id
            GROUP BY eq.id, eq.nombre
        """)
        tareas_por_equipo = cursor.fetchall()
        # KPIs de tareas
        cursor.execute("SELECT COUNT(*) as total FROM tareas")
        total_tareas = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM tareas WHERE estado = 'completada'")
        tareas_completadas = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM tareas WHERE estado != 'completada'")
        tareas_pendientes = cursor.fetchone()['total']
        # Eficiencia por equipo
        cursor.execute("""
            SELECT eq.nombre,
                   COUNT(t.id) as total_tareas,
                   SUM(CASE WHEN t.estado = 'completada' THEN 1 ELSE 0 END) as tareas_completadas
            FROM equipos eq
            LEFT JOIN empleados e ON eq.id = e.equipo_id
            LEFT JOIN tareas t ON e.id = t.empleado_id
            GROUP BY eq.id
        """)
        nombres_equipos = []
        eficiencia_equipos = []
        ranking_equipos = []
        for row in cursor.fetchall():
            nombres_equipos.append(row['nombre'])
            if row['total_tareas'] > 0:
                eficiencia = int(row['tareas_completadas'] / row['total_tareas'] * 100)
            else:
                eficiencia = 0
            eficiencia_equipos.append(eficiencia)
            ranking_equipos.append({
                'nombre': row['nombre'],
                'eficiencia': eficiencia,
                'tareas_completadas': row['tareas_completadas'] or 0,
                'total_tareas': row['total_tareas'] or 0
            })
        # Últimos empleados registrados (por id descendente)
        cursor.execute("""
            SELECT e.nombre, e.apellido, e.rol, eq.nombre as equipo
            FROM empleados e
            LEFT JOIN equipos eq ON e.equipo_id = eq.id
            WHERE e.rol IN ('lider', 'practicante')
            ORDER BY e.id DESC
            LIMIT 8
        """)
        ultimos_empleados = cursor.fetchall()
        # Tareas más recientes
        cursor.execute("""
            SELECT t.titulo, t.estado, e.nombre as asignado_nombre, t.fecha_creacion
            FROM tareas t
            LEFT JOIN empleados e ON t.empleado_id = e.id
            ORDER BY t.fecha_creacion DESC
            LIMIT 5
        """)
        tareas_recientes = cursor.fetchall()
        return render_template('dashboard.html',
            usuario=usuario_actual,
            total_empleados=total_empleados or 0,
            roles_stats=roles_stats or {},
            empleados=empleados or [],
            equipos_sin_lider=equipos_sin_lider or [],
            stats_equipos=stats_equipos or [],
            tareas_por_equipo=tareas_por_equipo or [],
            es_jefe=True,
            total_tareas=total_tareas or 0,
            tareas_completadas=tareas_completadas or 0,
            tareas_pendientes=tareas_pendientes or 0,
            roles_activos=roles_activos,
            total_activos=total_activos,
            eficiencia_equipos=eficiencia_equipos,
            nombres_equipos=nombres_equipos,
            ranking_equipos=ranking_equipos,
            ultimos_empleados=ultimos_empleados,
            tareas_recientes=tareas_recientes
        )
    
    elif rol == 'lider':
        # Para líderes: ver su equipo y tareas pendientes
        cursor.execute("""
            SELECT e.* 
            FROM empleados e 
            WHERE e.equipo_id = %s AND e.rol = 'practicante'
        """, (usuario_actual['equipo_id'],))
        miembros_equipo = cursor.fetchall()
        
        # Obtener tareas pendientes del equipo
        cursor.execute("""
            SELECT t.*, e.nombre as asignado_nombre, e.apellido as asignado_apellido
            FROM tareas t
            LEFT JOIN empleados e ON t.empleado_id = e.id
            WHERE e.equipo_id = %s AND t.estado != 'completada'
            ORDER BY t.fecha_limite ASC
        """, (usuario_actual['equipo_id'],))
        tareas_pendientes = cursor.fetchall()
        
        # Obtener estadísticas de rendimiento por miembro (solo practicantes)
        cursor.execute("""
            SELECT e.id, e.nombre, e.apellido,
                   COUNT(t.id) as total_tareas,
                   SUM(CASE WHEN t.estado = 'completada' THEN 1 ELSE 0 END) as tareas_completadas,
                   AVG(CASE WHEN t.estado = 'completada' THEN 
                       TIMESTAMPDIFF(HOUR, t.fecha_creacion, t.fecha_completada)
                   ELSE NULL END) as tiempo_promedio
            FROM empleados e
            LEFT JOIN tareas t ON e.id = t.empleado_id
            WHERE e.equipo_id = %s AND e.rol = 'practicante'
            GROUP BY e.id, e.nombre, e.apellido
        """, (usuario_actual['equipo_id'],))
        rendimiento_miembros = cursor.fetchall()
        
        # Obtener tareas próximas a vencer
        cursor.execute("""
            SELECT t.*, e.nombre as asignado_nombre, e.apellido as asignado_apellido
            FROM tareas t
            LEFT JOIN empleados e ON t.empleado_id = e.id
            WHERE e.equipo_id = %s 
            AND t.estado != 'completada'
            AND t.fecha_limite BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 3 DAY)
            ORDER BY t.fecha_limite ASC
        """, (usuario_actual['equipo_id'],))
        tareas_proximas = cursor.fetchall()
        
        return render_template('dashboard.html',
            usuario=usuario_actual,
            total_empleados=total_empleados or 0,
            roles_stats=roles_stats or {},
            miembros_equipo=miembros_equipo or [],
            tareas_pendientes=tareas_pendientes or [],
            rendimiento_miembros=rendimiento_miembros or [],
            tareas_proximas=tareas_proximas or [],
            es_lider=True,
            total_tareas=0,
            tareas_completadas=0,
            roles_activos=roles_activos,
            total_activos=total_activos
        )
    
    else:  # practicante
        # Para practicantes: ver sus tareas y progreso
        cursor.execute("""
            SELECT t.* 
            FROM tareas t 
            WHERE t.empleado_id = %s 
            ORDER BY t.fecha_limite ASC
        """, (usuario_id,))
        mis_tareas = cursor.fetchall()
        
        # Calcular estadísticas de tareas
        total_tareas = len(mis_tareas)
        tareas_completadas = sum(1 for t in mis_tareas if t['estado'] == 'completada')
        tareas_pendientes = sum(1 for t in mis_tareas if t['estado'] != 'completada')
        
        # Obtener tareas próximas a vencer
        cursor.execute("""
            SELECT t.*
            FROM tareas t
            WHERE t.empleado_id = %s 
            AND t.estado != 'completada'
            AND t.fecha_limite BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 3 DAY)
            ORDER BY t.fecha_limite ASC
        """, (usuario_id,))
        tareas_proximas = cursor.fetchall()
        
        return render_template('dashboard.html',
            usuario=usuario_actual,
            total_empleados=total_empleados or 0,
            roles_stats=roles_stats or {},
            mis_tareas=mis_tareas or [],
            total_tareas=total_tareas or 0,
            tareas_completadas=tareas_completadas or 0,
            tareas_pendientes=tareas_pendientes or 0,
            tareas_proximas=tareas_proximas or [],
            es_practicante=True,
            roles_activos=roles_activos,
            total_activos=total_activos
        )
    
    conexion.close()

@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html', usuario=current_user)

@app.route('/actualizar_perfil', methods=['POST'])
@login_required
def actualizar_perfil():
    try:
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        telefono = request.form.get('telefono')

        # Validaciones básicas
        if not nombre or not apellido or not email:
            flash('Todos los campos obligatorios deben estar completos.', 'danger')
            return redirect(url_for('perfil'))

        # Validar formato de email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('El formato del correo electrónico no es válido.', 'danger')
            return redirect(url_for('perfil'))

        # Verificar si el email ya existe (excepto para el usuario actual)
        usuario_existente = Usuario.query.filter(
            Usuario.email == email,
            Usuario.id != current_user.id
        ).first()
        if usuario_existente:
            flash('El correo electrónico ya está registrado por otro usuario.', 'danger')
            return redirect(url_for('perfil'))

        # Actualizar datos del usuario
        current_user.nombre = nombre
        current_user.apellido = apellido
        current_user.email = email
        current_user.telefono = telefono

        db.session.commit()
        flash('Perfil actualizado exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error al actualizar el perfil. Por favor, intente nuevamente.', 'danger')
        print(f"Error en actualizar_perfil: {str(e)}")

    return redirect(url_for('perfil'))

@app.route('/cambiar_password', methods=['POST'])
@login_required
def cambiar_password():
    try:
        # Obtener datos del formulario
        password_actual = request.form.get('password_actual')
        password_nueva = request.form.get('password_nueva')
        password_confirmar = request.form.get('password_confirmar')

        # Validar que la contraseña actual sea correcta
        if not check_password_hash(current_user.password, password_actual):
            flash('La contraseña actual es incorrecta.', 'danger')
            return redirect(url_for('perfil'))

        # Validar que las nuevas contraseñas coincidan
        if password_nueva != password_confirmar:
            flash('Las nuevas contraseñas no coinciden.', 'danger')
            return redirect(url_for('perfil'))

        # Validar longitud mínima de la contraseña
        if len(password_nueva) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres.', 'danger')
            return redirect(url_for('perfil'))

        # Actualizar contraseña
        current_user.password = generate_password_hash(password_nueva)
        db.session.commit()
        flash('Contraseña actualizada exitosamente.', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Error al cambiar la contraseña. Por favor, intente nuevamente.', 'danger')
        print(f"Error en cambiar_password: {str(e)}")

    return redirect(url_for('perfil'))

@app.route('/equipos/eliminar/<int:id>', methods=['POST'])
def eliminar_equipo(id):
    try:
        conexion = get_connection()
        cursor = conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM empleados WHERE equipo_id = %s", (id,))
        empleados_count = cursor.fetchone()[0]
        if empleados_count > 0:
            conexion.close()
            flash('No se puede eliminar un equipo con miembros asociados.', 'danger')
            return redirect(url_for('jefes'))
        cursor.execute("DELETE FROM equipos WHERE id = %s", (id,))
        conexion.commit()
        conexion.close()
        flash('Equipo eliminado con éxito.', 'success')
        return redirect(url_for('jefes'))
    except Exception as e:
        flash(f'Error al eliminar equipo: {str(e)}', 'danger')
        return redirect(url_for('jefes'))

@app.route('/jefes', methods=['GET'])
@login_required
def jefes():
    if current_user.rol != 'jefe':
        flash('Acceso restringido solo para jefes.', 'danger')
        return redirect(url_for('index'))
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM empleados WHERE rol = 'jefe' ORDER BY nombre")
    jefes = cursor.fetchall()
    # Obtener líderes y practicantes sin equipo
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre, apellido, rol FROM empleados WHERE equipo_id IS NULL AND rol IN ('lider', 'practicante') ORDER BY nombre")
    usuarios_disponibles = cursor.fetchall()
    # Obtener equipos y si tienen líder y total de miembros
    cursor.execute("""
        SELECT eq.id, eq.nombre,
               MAX(CASE WHEN e.rol = 'lider' THEN 1 ELSE 0 END) as tiene_lider,
               SUM(CASE WHEN e.rol IN ('lider', 'practicante') THEN 1 ELSE 0 END) as total_miembros
        FROM equipos eq
        LEFT JOIN empleados e ON eq.id = e.equipo_id
        GROUP BY eq.id, eq.nombre
        ORDER BY eq.nombre
    """)
    equipos = cursor.fetchall()
    # Obtener líderes disponibles para asignar
    cursor.execute("SELECT id, nombre, apellido FROM empleados WHERE rol = 'lider' AND equipo_id IS NULL ORDER BY nombre")
    lideres_disponibles = cursor.fetchall()
    conexion.close()
    return render_template('jefes.html', jefes=jefes, usuarios_disponibles=usuarios_disponibles, equipos=equipos, lideres_disponibles=lideres_disponibles)

@app.route('/jefes/crear_equipo', methods=['POST'])
@login_required
def crear_equipo_jefe():
    if current_user.rol != 'jefe':
        flash('Acceso restringido solo para jefes.', 'danger')
        return redirect(url_for('jefes'))
    nombre = request.form.get('nombre')
    miembros = request.form.getlist('miembros[]')
    if not nombre:
        flash('Debe ingresar el nombre del equipo.', 'danger')
        return redirect(url_for('jefes'))
    conexion = get_connection()
    cursor = conexion.cursor()
    try:
        cursor.execute("INSERT INTO equipos (nombre) VALUES (%s)", (nombre,))
        equipo_id = cursor.lastrowid
        for miembro_id in miembros:
            cursor.execute("UPDATE empleados SET equipo_id = %s WHERE id = %s", (equipo_id, miembro_id))
        conexion.commit()
        flash('Equipo creado correctamente.', 'success')
    except Exception as e:
        conexion.rollback()
        flash(f'Error al crear equipo: {str(e)}', 'danger')
    finally:
        conexion.close()
    return redirect(url_for('jefes'))

@app.route('/jefes/asignar_lider', methods=['POST'])
@login_required
def asignar_lider():
    if current_user.rol != 'jefe':
        flash('Acceso restringido solo para jefes.', 'danger')
        return redirect(url_for('jefes'))
    equipo_id = request.form.get('equipo_id')
    lider_id = request.form.get('lider_id')
    if not equipo_id or not lider_id:
        flash('Debe seleccionar un equipo y un líder.', 'danger')
        return redirect(url_for('jefes'))
    conexion = get_connection()
    cursor = conexion.cursor()
    try:
        cursor.execute("UPDATE empleados SET equipo_id = %s WHERE id = %s AND rol = 'lider'", (equipo_id, lider_id))
        conexion.commit()
        flash('Líder asignado correctamente al equipo.', 'success')
    except Exception as e:
        conexion.rollback()
        flash(f'Error al asignar líder: {str(e)}', 'danger')
    finally:
        conexion.close()
    return redirect(url_for('jefes'))

@app.route('/equipos/integrantes/<int:equipo_id>')
def integrantes_equipo(equipo_id):
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT nombre, apellido, correo, rol FROM empleados WHERE equipo_id = %s AND rol IN ('lider', 'practicante') ORDER BY rol, nombre
    """, (equipo_id,))
    integrantes = cursor.fetchall()
    conexion.close()
    return jsonify({'integrantes': integrantes})

@app.route('/jefes/editar_equipo', methods=['POST'])
@login_required
def editar_equipo():
    if current_user.rol != 'jefe':
        flash('Acceso restringido solo para jefes.', 'danger')
        return redirect(url_for('jefes'))
    equipo_id = request.form.get('equipo_id')
    nombre = request.form.get('nombre')
    lider_id = request.form.get('lider_id')
    miembros = request.form.getlist('miembros[]')
    if not equipo_id or not nombre:
        flash('Faltan datos obligatorios.', 'danger')
        return redirect(url_for('jefes'))
    conexion = get_connection()
    cursor = conexion.cursor()
    try:
        # Actualizar nombre del equipo
        cursor.execute("UPDATE equipos SET nombre = %s WHERE id = %s", (nombre, equipo_id))
        # Asignar/cambiar líder
        if lider_id:
            # Validar que el líder no esté en otro equipo
            cursor.execute("SELECT equipo_id FROM empleados WHERE id = %s AND rol = 'lider'", (lider_id,))
            lider_row = cursor.fetchone()
            if lider_row and lider_row[0] and int(lider_row[0]) != int(equipo_id):
                flash('El líder seleccionado ya pertenece a otro equipo.', 'danger')
                conexion.close()
                return redirect(url_for('jefes'))
            # Asignar líder a este equipo
            cursor.execute("UPDATE empleados SET equipo_id = %s WHERE id = %s AND rol = 'lider'", (equipo_id, lider_id))
        # Actualizar miembros (líderes/practicantes)
        # Primero, quitar a todos los miembros actuales de este equipo
        cursor.execute("UPDATE empleados SET equipo_id = NULL WHERE equipo_id = %s AND rol IN ('lider', 'practicante')", (equipo_id,))
        # Luego, asignar los seleccionados
        for miembro_id in miembros:
            cursor.execute("UPDATE empleados SET equipo_id = %s WHERE id = %s AND rol IN ('lider', 'practicante')", (equipo_id, miembro_id))
        conexion.commit()
        flash('Equipo actualizado correctamente.', 'success')
    except Exception as e:
        conexion.rollback()
        flash(f'Error al editar equipo: {str(e)}', 'danger')
    finally:
        conexion.close()
    return redirect(url_for('jefes'))

def limpiar_sesiones_inactivas():
    conexion = get_connection()
    cursor = conexion.cursor()
    cursor.execute("""
        DELETE FROM sesiones_activas
        WHERE ultima_actividad < (NOW() - INTERVAL 30 MINUTE)
    """)
    conexion.commit()
    conexion.close()

if __name__ == '__main__':
    app.run(debug=True)
