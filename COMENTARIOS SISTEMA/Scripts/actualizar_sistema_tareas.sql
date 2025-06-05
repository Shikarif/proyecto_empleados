-- Crear la base de datos desde cero
DROP DATABASE IF EXISTS testdb;
CREATE DATABASE testdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE testdb;

-- Tabla de equipos
CREATE TABLE equipos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

-- Tabla de empleados
CREATE TABLE empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    correo VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    equipo_id INT,
    rol ENUM('jefe', 'lider', 'practicante') DEFAULT 'practicante',
    habilidades TEXT,
    horas_disponibles INT DEFAULT 40,
    FOREIGN KEY (equipo_id) REFERENCES equipos(id)
);

-- Tabla de fortalezas
CREATE TABLE fortalezas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

-- Relación empleado-fortalezas
CREATE TABLE empleado_fortalezas (
    empleado_id INT,
    fortaleza_id INT,
    PRIMARY KEY (empleado_id, fortaleza_id),
    FOREIGN KEY (empleado_id) REFERENCES empleados(id),
    FOREIGN KEY (fortaleza_id) REFERENCES fortalezas(id)
);

-- Tabla de habilidades
CREATE TABLE habilidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT
);

-- Relación empleado-habilidades
CREATE TABLE empleado_habilidades (
    empleado_id INT,
    habilidad_id INT,
    nivel ENUM('básico', 'intermedio', 'avanzado') DEFAULT 'básico',
    PRIMARY KEY (empleado_id, habilidad_id),
    FOREIGN KEY (empleado_id) REFERENCES empleados(id),
    FOREIGN KEY (habilidad_id) REFERENCES habilidades(id)
);

-- Tabla de tareas
CREATE TABLE tareas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(100) NOT NULL,
    descripcion TEXT,
    fecha_creacion DATE,
    fecha_limite DATE,
    estado ENUM('pendiente', 'en_progreso', 'completada') DEFAULT 'pendiente',
    prioridad ENUM('baja', 'media', 'alta') DEFAULT 'media',
    horas_estimadas INT,
    habilidades_requeridas TEXT
);

-- Tabla de asignaciones
CREATE TABLE asignaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT,
    tarea_id INT,
    fecha_asignacion DATE,
    fecha_inicio DATE,
    fecha_fin DATE,
    estado ENUM('asignada', 'en_progreso', 'completada') DEFAULT 'asignada',
    FOREIGN KEY (empleado_id) REFERENCES empleados(id),
    FOREIGN KEY (tarea_id) REFERENCES tareas(id)
);

-- Tabla de archivos adjuntos a tareas
CREATE TABLE archivos_tarea (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tarea_id INT NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    tipo_archivo VARCHAR(50),
    ruta_archivo VARCHAR(255) NOT NULL,
    fecha_subida DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_id INT,
    id_attachment_trello VARCHAR(100),
    FOREIGN KEY (tarea_id) REFERENCES tareas(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES empleados(id) ON DELETE SET NULL
);

-- Tabla de comentarios de tareas
CREATE TABLE IF NOT EXISTS comentarios_tarea (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tarea_id INT NOT NULL,
    usuario_id INT NOT NULL,
    comentario TEXT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    id_comment_trello VARCHAR(255) DEFAULT NULL,
    FOREIGN KEY (tarea_id) REFERENCES tareas(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES empleados(id) ON DELETE CASCADE
); 