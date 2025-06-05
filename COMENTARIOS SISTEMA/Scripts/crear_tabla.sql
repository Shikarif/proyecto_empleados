-- Crear la base de datos si no existe
CREATE DATABASE IF NOT EXISTS testdb;

-- Usar la base de datos
USE testdb;

-- Crear la tabla empleados
CREATE TABLE IF NOT EXISTS empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    correo VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    departamento VARCHAR(100),
    fecha_contratacion DATE
); 