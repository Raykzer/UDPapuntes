Contexto y Objetivo
El proyecto "UDP Apuntes" tiene como objetivo crear un espacio colaborativo para estudiantes de la Universidad Diego Portales (UDP), facilitando el intercambio y acceso a recursos de estudio. Este sitio web, accesible solo para estudiantes mediante autenticación con correo UDP, contará con funciones básicas de carga y acceso a documentos, respaldadas por un sistema de moderación para garantizar la calidad del contenido. Su diseño se basa en las sugerencias y preocupaciones de alumnos y coordinadores de carrera.

Características
Autenticación con Google OAuth: Acceso seguro y restringido a estudiantes de la UDP.
Carga y Descarga de Documentos: Interfaz intuitiva para compartir y acceder a materiales de estudio.
Sistema de Likes: Los usuarios pueden votar los documentos, destacando los más útiles.
Panel de Administración: Permite la gestión de contenidos y usuarios (accesible solo para administradores).
Detalles de Implementación
Configuración del Entorno
Clonar el repositorio
Navegar al directorio del proyecto
Crear un entorno virtual: python3 -m venv venv
Activar el entorno virtual:
En Windows: venv\Scripts\activate
En MacOS/Linux: source venv/bin/activate
Instalar las dependencias: pip install -r requirements.txt
Dependencias
Flask
Flask-PyMongo
Flask-OAuthlib
Gunicorn
Nginx
Cloudflare
Código Fuente
El código fuente se organiza en las siguientes secciones clave:

app.py: Punto de entrada principal de la aplicación.
templates/: Directorio que contiene las vistas HTML.
static/: Directorio que contiene archivos estáticos como CSS y JavaScript.
uploads/: Directorio para almacenar los documentos subidos.
Autenticación
El sistema de autenticación utiliza Google OAuth. Los usuarios deben iniciar sesión con su correo UDP para acceder a la plataforma.

Rutas de la API
GET /home: Página principal con los últimos documentos subidos.
POST /upload: Ruta para cargar nuevos documentos.
GET /download/<file_id>: Descarga de documentos.
POST /like/<file_id>: Añadir un "like" a un documento.
POST /dislike/<file_id>: Añadir un "dislike" a un documento.
GET /admin/review: Página de revisión de documentos (solo para administradores).
Integración y Despliegue
Integración Continua
El proyecto utiliza GitHub Actions para la integración continua, asegurando que todas las pruebas se ejecuten y pasen antes de cualquier despliegue.

Despliegue
Configurar un servidor con Ubuntu.
Instalar Nginx y Gunicorn.
Configurar Nginx para servir la aplicación Flask detrás de Gunicorn.
Configurar Cloudflare para manejar HTTPS y gestionar el dominio.
Manejo de Errores y Logging
Uso de Flask-Logging para registrar eventos y errores.
Configuración de manejo de excepciones para capturar y registrar errores críticos.
Documentación para el Usuario
Guía del Usuario
Para usar la aplicación:

Iniciar sesión con tu correo UDP.
Navegar a la página principal para ver los documentos disponibles.
Usar la barra de búsqueda para encontrar documentos específicos.
Subir nuevos documentos desde la sección de carga.
Votar documentos con likes o dislikes para ayudar a otros usuarios.
Preguntas Frecuentes (FAQ)
¿Cómo puedo subir un documento?
Inicia sesión y navega a la sección de carga, luego selecciona el archivo y súbelo.
¿Cómo puedo votar un documento?
Utiliza los botones de like o dislike en la página de visualización de documentos.
Anexos
Glosario
OAuth: Un protocolo estándar para la autorización segura.
Nginx: Un servidor web que se puede usar como proxy inverso.
Gunicorn: Un servidor HTTP WSGI para aplicaciones Python.
Flask: Un microframework para Python basado en Werkzeug y Jinja2.
