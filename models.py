from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
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
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def actualizar_ultima_conexion(self):
        self.ultima_conexion = datetime.utcnow()
        db.session.commit()

class Equipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(64), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    tareas = db.relationship('Tarea', backref='equipo', lazy='dynamic')
    mensajes = db.relationship('Mensaje', backref='equipo', lazy='dynamic')

class Tarea(db.Model):
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
        return {
            'pendiente': 'warning',
            'en_progreso': 'info',
            'completada': 'success'
        }.get(self.estado, 'secondary')

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipo.id'))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(30), default='info')  # info, exito, alerta, error
    leido = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    usuario = db.relationship('Usuario', backref='notificaciones') 