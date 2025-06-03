"""
Modelos de datos para el sistema de Asignación de Tareas Equitativas.

Este módulo define la estructura de la base de datos utilizando SQLAlchemy ORM.
Define las clases principales del sistema y sus relaciones, incluyendo:
- Usuario: Gestión de usuarios y autenticación
- Equipo: Organización de equipos de trabajo
- Tarea: Gestión de tareas y asignaciones
- Mensaje: Sistema de comunicación interna
- Notification: Sistema de notificaciones

Las clases implementan relaciones uno a muchos y muchos a muchos según sea necesario.
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    """
    Modelo de Usuario que implementa la autenticación y gestión de usuarios.
    
    Atributos:
        id: Identificador único del usuario
        nombre: Nombre del usuario
        apellido: Apellido del usuario
        email: Correo electrónico único
        password_hash: Hash de la contraseña
        rol: Rol del usuario (jefe, lider, practicante)
        equipo_id: ID del equipo al que pertenece
        avatar_url: URL de la imagen de perfil
        ultima_conexion: Fecha de última conexión
        
    Relaciones:
        equipo: Relación con el equipo al que pertenece
        tareas_creadas: Tareas creadas por el usuario
        tareas_asignadas: Tareas asignadas al usuario
        mensajes: Mensajes enviados por el usuario
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(64), nullable=False)
    apellido = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    rol = db.Column(db.String(20), nullable=False)  # jefe, lider, practicante
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipo.id'))
    avatar_url = db.Column(db.String(200))
    ultima_conexion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    equipo = db.relationship('Equipo', backref='miembros')
    tareas_creadas = db.relationship('Tarea', backref='creador', foreign_keys='Tarea.creador_id')
    tareas_asignadas = db.relationship('Tarea', backref='asignado_a', foreign_keys='Tarea.asignado_a')
    mensajes = db.relationship('Mensaje', backref='usuario', lazy='dynamic')
    
    def set_password(self, password):
        """Genera y almacena el hash de la contraseña."""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Verifica si la contraseña proporcionada coincide con el hash almacenado."""
        return check_password_hash(self.password_hash, password)
    
    def actualizar_ultima_conexion(self):
        """Actualiza la fecha de última conexión del usuario."""
        self.ultima_conexion = datetime.utcnow()
        db.session.commit()

class Equipo(db.Model):
    """
    Modelo de Equipo para la organización de grupos de trabajo.
    
    Atributos:
        id: Identificador único del equipo
        nombre: Nombre único del equipo
        descripcion: Descripción detallada del equipo
        activo: Estado de actividad del equipo
        
    Relaciones:
        tareas: Tareas asociadas al equipo
        mensajes: Mensajes del equipo
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(64), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    tareas = db.relationship('Tarea', backref='equipo', lazy='dynamic')
    mensajes = db.relationship('Mensaje', backref='equipo', lazy='dynamic')

class Tarea(db.Model):
    """
    Modelo de Tarea para la gestión de asignaciones y seguimiento.
    
    Atributos:
        id: Identificador único de la tarea
        titulo: Título de la tarea
        descripcion: Descripción detallada
        estado: Estado actual (pendiente, en_progreso, completada)
        fecha_creacion: Fecha de creación
        fecha_limite: Fecha límite para completar
        creador_id: ID del usuario que creó la tarea
        asignado_a: ID del usuario asignado
        equipo_id: ID del equipo al que pertenece
        
    Propiedades:
        estado_color: Retorna el color CSS correspondiente al estado
    """
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, en_progreso, completada
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_limite = db.Column(db.DateTime)
    creador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    asignado_a = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipo.id'))
    
    @property
    def estado_color(self):
        """Retorna el color CSS correspondiente al estado de la tarea."""
        return {
            'pendiente': 'warning',
            'en_progreso': 'info',
            'completada': 'success'
        }.get(self.estado, 'secondary')

class Mensaje(db.Model):
    """
    Modelo de Mensaje para la comunicación interna del sistema.
    
    Atributos:
        id: Identificador único del mensaje
        contenido: Contenido del mensaje
        fecha_creacion: Fecha de creación
        usuario_id: ID del usuario que envió el mensaje
        equipo_id: ID del equipo al que pertenece el mensaje
    """
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipo.id'))

class Notification(db.Model):
    """
    Modelo de Notification para el sistema de notificaciones.
    
    Atributos:
        id: Identificador único de la notificación
        mensaje: Contenido de la notificación
        tipo: Tipo de notificación (info, exito, alerta, error)
        leido: Estado de lectura
        fecha: Fecha de creación
        usuario_id: ID del usuario destinatario
    """
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(30), default='info')  # info, exito, alerta, error
    leido = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    usuario = db.relationship('Usuario', backref='notificaciones') 