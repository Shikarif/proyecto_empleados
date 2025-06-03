"""
Funciones auxiliares y decoradores para el sistema de Asignación de Tareas Equitativas.

Este módulo proporciona utilidades y decoradores para:
- Control de acceso basado en roles
- Verificación de pertenencia a equipos
- Redirecciones y mensajes flash
- Validaciones de seguridad

Los decoradores implementan la lógica de autorización y control de acceso
que se aplica a las rutas de la aplicación.
"""

from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def rol_requerido(*roles):
    """
    Decorador para restringir el acceso a rutas basado en roles de usuario.
    
    Args:
        *roles: Lista de roles permitidos para acceder a la ruta
        
    Returns:
        function: Decorador que verifica el rol del usuario
        
    Ejemplo:
        @app.route('/admin')
        @rol_requerido('jefe', 'lider')
        def admin_panel():
            return 'Panel de administración'
    """
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
    """
    Decorador para verificar que el usuario pertenece al equipo que intenta acceder.
    
    Este decorador implementa la siguiente lógica:
    1. Verifica que el usuario esté autenticado
    2. Verifica que se proporcione un ID de equipo
    3. Permite acceso a jefes a todos los equipos
    4. Verifica que los demás usuarios pertenezcan al equipo
    
    Args:
        f: Función a decorar
        
    Returns:
        function: Decorador que verifica la pertenencia al equipo
        
    Ejemplo:
        @app.route('/equipo/<int:equipo_id>')
        @equipo_requerido
        def vista_equipo(equipo_id):
            return 'Vista del equipo'
    """
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