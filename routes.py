from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from . import db
from .models import Equipo, Usuario, Tarea, Mensaje

@bp.route('/equipos')
@login_required
def lista_equipos():
    equipos = Equipo.query.all()
    return render_template('equipos/lista.html', equipos=equipos)

@bp.route('/equipos/<int:equipo_id>')
@login_required
def vista_equipo(equipo_id):
    equipo = Equipo.query.get_or_404(equipo_id)
    
    # Verificar acceso
    if current_user.rol != 'jefe' and current_user.equipo_id != equipo_id:
        flash('No tienes acceso a este equipo', 'error')
        return redirect(url_for('main.lista_equipos'))
    
    # Obtener miembros del equipo
    miembros = Usuario.query.filter_by(equipo_id=equipo_id).all()
    miembros_activos = [m for m in miembros if m.ultima_conexion and (datetime.utcnow() - m.ultima_conexion).seconds < 300]
    
    # Obtener mensajes del equipo
    mensajes = Mensaje.query.filter_by(equipo_id=equipo_id).order_by(Mensaje.fecha_creacion.desc()).limit(50).all()
    
    # Obtener tareas
    if current_user.rol == 'lider':
        tareas = Tarea.query.filter_by(equipo_id=equipo_id).all()
    else:
        tareas = Tarea.query.filter_by(equipo_id=equipo_id, asignado_a=current_user.id).all()
    
    return render_template('equipos/vista_equipo.html',
                         equipo=equipo,
                         miembros=miembros,
                         miembros_activos=miembros_activos,
                         mensajes=mensajes,
                         tareas=tareas)

@bp.route('/equipos/<int:equipo_id>/mensaje', methods=['POST'])
@login_required
def enviar_mensaje(equipo_id):
    equipo = Equipo.query.get_or_404(equipo_id)
    
    # Verificar acceso
    if current_user.rol != 'jefe' and current_user.equipo_id != equipo_id:
        return jsonify({'error': 'No tienes acceso a este equipo'}), 403
    
    contenido = request.form.get('mensaje')
    if not contenido:
        return jsonify({'error': 'El mensaje no puede estar vacío'}), 400
    
    mensaje = Mensaje(
        contenido=contenido,
        equipo_id=equipo_id,
        usuario_id=current_user.id
    )
    
    db.session.add(mensaje)
    db.session.commit()
    
    return jsonify({
        'id': mensaje.id,
        'contenido': mensaje.contenido,
        'usuario': {
            'nombre': current_user.nombre,
            'apellido': current_user.apellido,
            'avatar_url': current_user.avatar_url
        },
        'fecha_creacion': mensaje.fecha_creacion.strftime('%H:%M')
    }) 