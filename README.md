# Sistema de Gestión de Empleados

Sistema web desarrollado en Flask para la gestión completa de empleados, con interfaz moderna y funcionalidades avanzadas.

## 🚀 Características

- Gestión completa de empleados (CRUD)
- Búsqueda y filtrado de empleados
- Estadísticas y visualización de datos
- Interfaz moderna y responsiva
- Validación de datos en tiempo real
- Base de datos MySQL

## 📋 Requisitos Previos

- Python 3.8 o superior
- MySQL Server
- pip (gestor de paquetes de Python)

## 🛠️ Instalación

1. **Clonar el repositorio**
```bash
git clone <url-del-repositorio>
cd proyecto_empleados
```

2. **Crear y activar entorno virtual**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar la base de datos**
- Crear una base de datos MySQL llamada `empleados_db`
- Ejecutar el script SQL para crear las tablas:
```bash
mysql -u root -p empleados_db < actualizar_db.sql
```

5. **Configurar variables de entorno**
Crear un archivo `.env` en la raíz del proyecto con:
```
DB_HOST=localhost
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_NAME=empleados_db
```

## 🚀 Ejecución

1. **Iniciar el servidor**
```bash
python app.py
```

2. **Acceder a la aplicación**
Abrir el navegador y visitar: `http://localhost:5000`

## 📱 Funcionalidades

### Gestión de Empleados
- **Agregar**: Formulario con validación para nuevos empleados
- **Editar**: Modificación de datos existentes
- **Eliminar**: Eliminación con confirmación
- **Buscar**: Búsqueda por nombre, apellido o correo

### Campos de Empleado
- Nombre
- Apellido
- Correo electrónico
- Teléfono (9 dígitos)
- Departamento
- Fecha de contratación

### Estadísticas
- Total de empleados
- Últimos empleados contratados
- Distribución por departamento
- Gráficos interactivos

## 🛠️ Estructura del Proyecto

```
proyecto_empleados/
├── app.py              # Aplicación principal
├── db_config.py        # Configuración de la base de datos
├── requirements.txt    # Dependencias del proyecto
├── actualizar_db.sql   # Script de actualización de la base de datos
└── templates/          # Plantillas HTML
    ├── base.html       # Plantilla base
    ├── index.html      # Página principal
    ├── agregar.html    # Formulario de agregar
    ├── editar.html     # Formulario de editar
    └── estadisticas.html # Página de estadísticas
```

## 📦 Dependencias Principales

- Flask: Framework web
- Flask-SQLAlchemy: ORM para base de datos
- mysql-connector-python: Conector MySQL
- python-dotenv: Manejo de variables de entorno
- Bootstrap 5: Framework CSS
- Font Awesome: Iconos
- Google Fonts: Fuentes tipográficas

## 🔧 Comandos Útiles

### Base de Datos
```bash
# Reiniciar la base de datos
mysql -u root -p empleados_db < actualizar_db.sql

# Verificar conexión
python -c "from db_config import db; print(db.engine.table_names())"
```

### Desarrollo
```bash
# Activar entorno virtual
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instalar nuevas dependencias
pip install <paquete>
pip freeze > requirements.txt

# Ejecutar en modo desarrollo
python app.py
```

## 🐛 Solución de Problemas

1. **Error de conexión a la base de datos**
   - Verificar credenciales en `.env`
   - Asegurar que MySQL está en ejecución
   - Comprobar que la base de datos existe

2. **Errores de dependencias**
   - Actualizar pip: `python -m pip install --upgrade pip`
   - Reinstalar dependencias: `pip install -r requirements.txt`

3. **Problemas con el servidor**
   - Verificar que el puerto 5000 está disponible
   - Comprobar logs de error en la consola

## 📝 Notas Adicionales

- El sistema está optimizado para navegadores modernos
- Se recomienda usar Python 3.8 o superior
- La base de datos debe ser MySQL 5.7 o superior
- Los archivos de configuración no deben subirse al control de versiones

## 🤝 Contribución

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE.md](LICENSE.md) para más detalles. 
https://xhaxxorx.github.io/proyecto_empleados/

