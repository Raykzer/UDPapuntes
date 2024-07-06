import base64
import fitz
import flask
import httplib2
import json
import pathlib
import socket
import sys
import os
import requests
from authlib.integrations.flask_client import OAuth
from datetime import datetime
from flask import Flask, abort, redirect, render_template, request, send_file, send_from_directory, session, url_for
from funciones import convert_pdf_to_image, extract_manga_names, search_pdfs, create_pdf_thumbnail
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from io import BytesIO
from pymongo import MongoClient
from requests_oauthlib import OAuth2Session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from pip._vendor import cachecontrol
from flask_login import login_required, current_user
from flask import Flask, session, abort, redirect, request
import google.auth.transport.requests

# Inicializar la aplicación Flask
app = Flask(__name__)
app.secret_key = "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"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['THUMBNAIL_FOLDER'] = 'thumbnails'
thumbnails_dir = os.path.join(app.root_path, app.config['THUMBNAIL_FOLDER'])

# Conexión a MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['documentDB']
collection = db['documents']
users_collection = db['users']


# Configuración de OAuth de Google
GOOGLE_CLIENT_ID = "4413767145-2temsr0uv0c2l5hqt68voi8cm8nergd2.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="https://udpapuntes.xyz/authorize"
)


# Decorador para verificar si el usuario ha iniciado sesión
def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()
    return wrapper

# Decorador para verificar si el usuario es admin
def admin_login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session or session["google_id"] != "117746659694757023709":
            return abort(401)  # Unauthorized for non-admin users
        else:
            return function(*args, **kwargs)
    return wrapper


# Ruta para iniciar sesión
@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


# Ruta para autorizar el inicio de sesión con Google
@app.route("/authorize") #/callback
def authorize():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)   # El estado no coincide
    #Verificar si el usuario está registrado, si no guardar en la base de datos users_collection.
    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    google_id = id_info.get("sub")
    name = id_info.get("name")


     # Verificar si el usuario ya está registrado
    user = users_collection.find_one({"google_id": google_id})

    if user:
        # User exists, proceed with login
        print("User exists, logging in...")
    else:
        # User doesn't exist, save in DB
        users_collection.insert_one({"google_id": google_id, "name": name})
        print("New user, saved to DB.")

    session["google_id"] = google_id
    session["name"] = name
    

    # Redirigir a la página adecuada según el Google ID
    if google_id == "117746659694757023709":
        return redirect("/review")
    else:
        return redirect("/home")


# Ruta para cerrar sesión
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# Ruta principal
@app.route("/")
def index():
    return render_template('index.html')


# Ruta para una área protegida
@app.route("/protected_area")
def protected_area():
    return f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"


# Ruta para el home (requiere inicio de sesión)
@app.route('/home', methods=['GET', 'POST'], endpoint='home')
@login_is_required
def home():
    
    if request.method == 'POST':
        # Manejar solicitud POST si es necesario
        pass
    
    # Obtener los 4 últimos documentos subidos, ordenados por timestamp
    latest_documents = list(collection.find().sort('timestamp', -1).limit(4))
    
    # Actualizar cada documento para enviar la imagen como contenido binario codificado en base64
    for doc in latest_documents:
        image_path = os.path.join(thumbnails_dir, doc['imagen_src'])
        with open(image_path, 'rb') as f:
            image_content = f.read()
            doc['imagen_src'] = base64.b64encode(image_content).decode('utf-8')  # Codificar en base64 y convertir a cadena

    return render_template('HOME.html', latest_documents=latest_documents)


# Función para crear miniaturas de PDFs
def create_pdf_thumbnail(pdf_path, thumbnail_path):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)  # Cargar la primera página
    pix = page.get_pixmap()
    pix.save(thumbnail_path)


# Ruta para subir archivos
@app.route('/upload', methods=['POST'])
def subir_archivo():
    archivo = request.files['file']
    if archivo.filename == '':
        return 'No se seleccionó ningún archivo', 400
    if archivo and archivo.filename.endswith('.pdf'):
        filename = secure_filename(archivo.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        archivo.save(filepath)

        # Crear miniatura
        thumbnail_filename = filename.rsplit('.', 1)[0] + '.png'
        thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumbnail_filename)
        create_pdf_thumbnail(filepath, thumbnail_path)

        titulo = request.form.get('title')
        autor = request.form.get('author')
        descripcion = request.form.get('description')
        categoria = request.form.get('category')

        documento = {
            'titulo': titulo,
            'autor': autor,
            'descripcion': descripcion,
            'categoria': categoria,
            'ruta_archivo': filepath,
            'imagen_src': thumbnail_filename,  # Almacenar el nombre de la miniatura
            'timestamp': datetime.now(),  # Agregar marca de tiempo
            'likes': [],  # Contador inicial de likes
            'dislikes': []  # Contador inicial de dislikes
        }

        collection.insert_one(documento)

        return redirect(url_for('home'))
    return 'Tipo de archivo no válido', 400


# Ruta para servir miniaturas
@app.route('/thumbnails/<filename>')
def thumbnails(filename):
    return send_from_directory(thumbnails_dir, filename)


# Ruta para buscar documentos
@app.route('/buscar', methods=['GET', 'POST'])
def buscar():
    if request.method == 'POST':
        termino_busqueda = request.form['termino_busqueda']
        # Consultar la base de datos para obtener los libros que contengan el término en el título
        resultados = list(collection.find({"titulo": {"$regex": termino_busqueda, "$options": "i"}}))
        
        # Actualizar cada libro para enviar la imagen como contenido binario codificado en base64
        for resultado in resultados:
            image_path = os.path.join(thumbnails_dir, resultado['imagen_src'])
            with open(image_path, 'rb') as f:
                image_content = f.read()
                resultado['imagen_src'] = base64.b64encode(image_content).decode('utf-8')  # Codificar en base64 y convertir a cadena
        
        return render_template('resultados.html', books=resultados)
    
    return render_template('resultados.html', books=[])


# Ruta para la sección de materias
@app.route('/materias', endpoint='materias')
@login_is_required
def materias():
    # Obtener los documentos de MongoDB filtrados por categoría 'materia'
    books = list(collection.find({'categoria': 'materia'}))

    # Actualizar cada libro para enviar la imagen como contenido binario codificado en base64
    for book in books:
        image_path = os.path.join(thumbnails_dir, book['imagen_src'])
        with open(image_path, 'rb') as f:
            image_content = f.read()
            book['imagen_src'] = base64.b64encode(image_content).decode('utf-8')  # Codificar en base64 y convertir a cadena

    return render_template('materias.html', books=books)


# Ruta para la sección de apuntes
@app.route('/apuntes', endpoint='apuntes')
@login_is_required
def apuntes():
    # Obtener los documentos de la colección 'documents' filtrados por categoría 'apunte'
    books = list(collection.find({'categoria': 'apunte'}))
    
    # Actualizar cada libro para enviar la imagen como contenido binario codificado en base64
    for book in books:
        image_path = os.path.join(thumbnails_dir, book['imagen_src'])
        with open(image_path, 'rb') as f:
            image_content = f.read()
            book['imagen_src'] = base64.b64encode(image_content).decode('utf-8')  # Codificar en base64 y convertir a cadena
    return render_template('apuntes.html', books=books)


# Ruta para la sección de lecturas
@app.route('/lecturas', endpoint='lecturas')
@login_is_required
def lecturas():
    # Obtener los documentos de la colección 'documents' filtrados por categoría 'lectura'
    books = list(collection.find({'categoria': 'lectura'}))

    # Actualizar cada libro para enviar la imagen como contenido binario codificado en base64
    for book in books:
        image_path = os.path.join(thumbnails_dir, book['imagen_src'])
        with open(image_path, 'rb') as f:
            image_content = f.read()
            book['imagen_src'] = base64.b64encode(image_content).decode('utf-8')  # Codificar en base64 y convertir a cadena
    return render_template('lecturas.html', books=books)




# Ruta para la vista del documento
@app.route('/visualizador/<titulo>', endpoint='visualizador') 
def visualizador(titulo):   
    if 'google_id' in session:
        pass
    else:
        return redirect(url_for('index'))
    # Buscar el libro por título en MongoDB
    book = collection.find_one({'titulo': titulo})
    if book:
        image_path = os.path.join(thumbnails_dir, book['imagen_src'])
        with open(image_path, 'rb') as f:
            image_content = f.read()
            book['imagen_src'] = base64.b64encode(image_content).decode('utf-8')  # Codificar en base64 y convertir a cadena

        # Contar likes y dislikes
        likes_count = len(book.get('likes', []))
        dislikes_count = len(book.get('dislikes', []))

        return render_template('visualizador.html', book=book, likes_count=likes_count, dislikes_count=dislikes_count)
    else:
        return redirect(url_for('materias'))  # Redireccionar a materias si no se encuentra el libro


#ver en linea
@app.route('/visualizador/<titulo>/view')
def view_online(titulo):
    if 'google_id' in session:
        pass
    else:
        return redirect(url_for('index'))
    book = collection.find_one({'titulo': titulo})
    if book:
        filename = os.path.basename(book['ruta_archivo'])
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    else:
        return redirect(url_for('home'))


#descargar
@app.route('/visualizador/<titulo>/download')
def download(titulo):
    if 'google_id' in session:
        pass
    else:
        return redirect(url_for('index'))
    book = collection.find_one({'titulo': titulo})
    if book:
        filename = os.path.basename(book['ruta_archivo'])
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    else:
        return redirect(url_for('home'))    


# Ruta para manejar likes
@app.route('/like/<titulo>')
def like(titulo):
    if 'google_id' in session:
        username = session['name']
        book = collection.find_one({'titulo': titulo})
        if book:
            if username not in book.get('likes', []):
                collection.update_one(
                    {'titulo': titulo},
                    {'$addToSet': {'likes': username}, '$pull': {'dislikes': username}}
                )
                session.setdefault('likes', []).append(titulo)
                if titulo in session.get('dislikes', []):
                    session['dislikes'].remove(titulo)
    return redirect(url_for('visualizador', titulo=titulo))


# Ruta para manejar dislikes
@app.route('/dislike/<titulo>')
def dislike(titulo):
    if 'google_id' in session:
        username = session['name']
        book = collection.find_one({'titulo': titulo})
        if book:
            if username not in book.get('dislikes', []):
                collection.update_one(
                    {'titulo': titulo},
                    {'$addToSet': {'dislikes': username}, '$pull': {'likes': username}}
                )
                session.setdefault('dislikes', []).append(titulo)
                if titulo in session.get('likes', []):
                    session['likes'].remove(titulo)
    return redirect(url_for('visualizador', titulo=titulo))


# Ruta para la sección de revisión de administrador
@app.route('/review', endpoint='review')
@admin_login_is_required
def review():
    # Obtener todos los documentos de la base de datos
    documents = list(collection.find())
    
    # Actualizar cada documento para enviar la imagen como contenido binario codificado en base64
    for doc in documents:
        image_path = os.path.join(thumbnails_dir, doc['imagen_src'])
        with open(image_path, 'rb') as f:
            image_content = f.read()
            doc['imagen_src'] = base64.b64encode(image_content).decode('utf-8')  # Codificar en base64 y convertir a cadena

    return render_template('review.html', documents=documents)



# Ruta para vista de documentos del administrador
@app.route('/visualizador_A/<titulo>')
def visualizador_A(titulo):
    if  session["google_id"] == "117746659694757023709":
        pass
    else:
        return redirect(url_for('index'))
    # Buscar el libro por título en MongoDB
    book = collection.find_one({'titulo': titulo})
    if book:
        image_path = os.path.join(thumbnails_dir, book['imagen_src'])
        with open(image_path, 'rb') as f:
            image_content = f.read()
            book['imagen_src'] = base64.b64encode(image_content).decode('utf-8')  # Codificar en base64 y convertir a cadena

        # Contar likes y dislikes
        likes_count = len(book.get('likes', []))
        dislikes_count = len(book.get('dislikes', []))

        return render_template('visualizador_A.html', book=book, likes_count=likes_count, dislikes_count=dislikes_count)
    else:
        return redirect(url_for('review'))  # Redireccionar a materias si no se encuentra el libro


# Ruta para buscar documentos en la sección de revisión de administrador
@app.route('/buscar_A', methods=['GET', 'POST'])
def buscar_A():
    if request.method == 'POST':
        termino_busqueda = request.form.get('termino_busqueda', '')
        # Consultar la base de datos para obtener los documentos que contengan el término en el título
        documentos = list(db.documents.find({"titulo": {"$regex": termino_busqueda, "$options": "i"}}))
        
        # Actualizar cada documento para enviar la imagen como contenido binario codificado en base64
        for documento in documentos:
            image_path = os.path.join(thumbnails_dir, documento['imagen_src'])
            with open(image_path, 'rb') as f:
                image_content = f.read()
                documento['imagen_src'] = base64.b64encode(image_content).decode('utf-8')  # Codificar en base64 y convertir a cadena
        
        return render_template('review_res.html', documents=documentos)
    
    return render_template('review_res.html', documents=[])


# Ruta para eliminar documentos
@app.route('/delete/<titulo>', methods=['POST'])
def delete_document(titulo):
    # Buscar el documento en la base de datos
    document = collection.find_one({'titulo': titulo})
    if not document:
        # Documento no encontrado, redirigir a una página de error o a la revisión
        return redirect(url_for('review'))  

    # Obtener los paths de los archivos asociados
    pdf_path = document['ruta_archivo']
    thumbnail_path = os.path.join(thumbnails_dir, document['imagen_src'])

    # Eliminar el archivo PDF
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    else:
        print(f"El archivo PDF {pdf_path} no existe.")

    # Eliminar la imagen thumbnail
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)
    else:
        print(f"La imagen thumbnail {thumbnail_path} no existe.")

    # Eliminar el documento de la base de datos
    result = collection.delete_one({'titulo': titulo})
    if result.deleted_count > 0:
        # Eliminación exitosa, redirigir a la página de revisión
        return redirect(url_for('review'))
    else:
        # Documento no encontrado, redirigir a una página de error o a la revisión
        return redirect(url_for('review'))  # Puedes personalizar este comportamiento según tus necesidades



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='4200')
