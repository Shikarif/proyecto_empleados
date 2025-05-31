from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def rol_requerido(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.rol not in roles:
                flash('No tienes permiso para acceder a esta función.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def equipo_requerido(f):
    """Decorador para verificar que el usuario pertenece al equipo que intenta acceder."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Debes iniciar sesión para acceder a esta función.', 'danger')
            return redirect(url_for('login'))
            
        equipo_id = kwargs.get('equipo_id')
        if not equipo_id:
            flash('ID de equipo no especificado.', 'danger')
            return redirect(url_for('index'))
            
        # Los jefes tienen acceso a todos los equipos
        if current_user.rol == 'jefe':
            return f(*args, **kwargs)
            
        # Verificar que el usuario pertenece al equipo
        if current_user.equipo_id != int(equipo_id):
            flash('No tienes permiso para acceder a este equipo.', 'danger')
            return redirect(url_for('index'))
            
        return f(*args, **kwargs)
    return decorated_function 