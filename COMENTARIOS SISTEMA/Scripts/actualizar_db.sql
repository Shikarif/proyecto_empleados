-- Para cambiar la contraseña especial de reinicio de base de datos, ejecuta:
-- UPDATE configuracion SET valor = SHA2('nueva_contraseña', 256) WHERE clave = 'password_reinicio';
--------------------------------------------------
-- Borrar tablas forzando la eliminación de las relaciones
SET FOREIGN_KEY_CHECKS = 0;
use testdb;
TRUNCATE TABLE empleado_fortalezas;
TRUNCATE TABLE empleados;
TRUNCATE TABLE fortalezas;
SET FOREIGN_KEY_CHECKS = 1;
--------------------------------------------------

ALTER TABLE empleados
ADD COLUMN telefono VARCHAR(20) AFTER correo,
ADD COLUMN departamento VARCHAR(100) AFTER telefono,
ADD COLUMN fecha_contratacion DATE AFTER departamento; 

-------------------------------------------------
#crear nuevos jedes desde la base de datos
INSERT INTO empleados (nombre, apellido, correo, telefono, equipo_id, rol, password)
VALUES ('Nombre', 'Apellido', 'correo@ejemplo.com', '123456789', NULL, 'jefe', '<contraseña_hash>');