from flask import Flask, render_template, request, session
from flask_socketio import SocketIO
import sqlite3
from datetime import datetime
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins=['http://127.0.0.1:5500', 'http://localhost:5500', 'http://127.0.0.1:5000'], logger=True, engineio_logger=True)

# Configuración de Hugging Face API
HF_API_TOKEN = os.getenv('HF_API_TOKEN', 'tu-huggingface-api-token')
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"

# Inicializar base de datos SQLite
def init_db():
    try:
        with sqlite3.connect('leads.db', timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    business_type TEXT,
                    needs TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads';")
            if cursor.fetchone():
                print("Tabla 'leads' creada o ya existe.")
            else:
                print("Error: Tabla 'leads' no se creó.")
    except sqlite3.Error as e:
        print(f"Error al inicializar la base de datos: {e}")

# Generar respuesta con Hugging Face API
def generate_ai_response(state, user_message):
    prompt = f"""
    Eres una asistente profesional de asesoramiento digital para negocios. Tu objetivo es guiar al usuario para recopilar su nombre, email, tipo de negocio y necesidades, y ofrecer recomendaciones personalizadas. 
    Contexto: 
    - Nombre: {state.get('name', 'Desconocido')}
    - Email: {state.get('email', 'No proporcionado')}
    - Tipo de negocio: {state.get('business_type', 'No especificado')}
    - Mensaje actual: {user_message}
    Responde en español, de manera profesional, amigable y concisa, avanzando la conversación hacia el siguiente paso (si corresponde). No repitas el prompt.
    """
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_length": 200, "temperature": 0.7, "return_full_text": False}
    }
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()[0]["generated_text"].strip()
    except Exception as e:
        print(f"Error al generar respuesta con IA: {e}")
        return None

# Recomendaciones de respaldo
def get_recommendations(business_type):
    recommendations = {
        'restaurante': ["Sitio web con reservas online", "SEO local para Google Maps"],
        'tienda': ["Tienda online con e-commerce", "Automatización de inventario"],
        'servicios': ["CRM para gestión de clientes", "Campañas de email marketing"],
        'default': ["Sitio web profesional", "Análisis de datos para decisiones"]
    }
    return recommendations.get(business_type.lower(), recommendations['default'])

# Ruta principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para favicon.ico
@app.route('/favicon.ico')
def favicon():
    return '', 204

# WebSocket para el chat
@socketio.on('connect')
def connect(auth=None):
    sid = request.sid
    origin = request.headers.get('Origin')
    print(f"Cliente conectado: {sid}, Origen: {origin}")
    session['chat_state'] = {'step': 0, 'data': {}}
    session.modified = True
    socketio.emit('message', {'text': '¡Hola! Soy tu asistente digital. Al compartir tus datos, aceptas que te contactemos. ¿Cuál es tu nombre?'}, to=sid)

@socketio.on('connect_error')
def connect_error(error):
    print(f"Error de conexión WebSocket: {error}")

@socketio.on('message')
def handle_message(data):
    sid = request.sid
    try:
        user_message = data.get('text', '').strip()
        state = session.get('chat_state', {'step': 0, 'data': {}})
        print(f"Mensaje recibido de {sid}: {user_message}, paso: {state['step']}")

        if state['step'] == 0:  # Preguntar nombre
            if not user_message:
                socketio.emit('message', {'text': 'Por favor, dime tu nombre para continuar.'}, to=sid)
            else:
                state['data']['name'] = user_message
                state['step'] = 1
                session['chat_state'] = state
                session.modified = True
                ai_response = generate_ai_response(state['data'], user_message)
                socketio.emit('message', {'text': ai_response or f'Encantado, {user_message}. ¿Cuál es tu email para enviarte un resumen?'}, to=sid)
        
        elif state['step'] == 1:  # Preguntar email
            if not user_message or '@' not in user_message:
                socketio.emit('message', {'text': 'Por favor, ingresa un email válido.'}, to=sid)
            else:
                state['data']['email'] = user_message
                state['step'] = 2
                session['chat_state'] = state
                session.modified = True
                ai_response = generate_ai_response(state['data'], user_message)
                socketio.emit('message', {'text': ai_response or 'Gracias. ¿Qué tipo de negocio tienes? (ej. restaurante, tienda, servicios)'}, to=sid)
                socketio.emit('prompt_buttons', {'buttons': ['Restaurante', 'Tienda', 'Servicios']}, to=sid)
        
        elif state['step'] == 2:  # Preguntar tipo de negocio
            if not user_message:
                socketio.emit('message', {'text': 'Por favor, dime el tipo de negocio (ej. restaurante, tienda, servicios).'}, to=sid)
            else:
                state['data']['business_type'] = user_message
                state['step'] = 3
                session['chat_state'] = state
                session.modified = True
                ai_response = generate_ai_response(state['data'], user_message)
                socketio.emit('message', {'text': ai_response or '¡Entendido! ¿Qué necesitas para tu negocio? (ej. sitio web, automatización, marketing)'}, to=sid)
        
        elif state['step'] == 3:  # Preguntar necesidades y guardar lead
            state['data']['needs'] = user_message or "No especificado"
            recommendations = get_recommendations(state['data']['business_type'])
            ai_response = generate_ai_response(state['data'], user_message)
            response = f"Gracias por compartir, {state['data']['name']}. Para tu {state['data']['business_type']}, te recomiendo:\n"
            for rec in recommendations:
                response += f"- {rec}\n"
            response += "Guardaré tus datos y te contactaré para ayudarte. ¡Gracias por confiar en nosotros!"
            
            # Guardar lead
            try:
                with sqlite3.connect('leads.db', timeout=10) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO leads (name, email, business_type, needs, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (state['data']['name'], state['data']['email'], state['data']['business_type'], state['data']['needs'], datetime.now()))
                    conn.commit()
                    cursor.execute('SELECT * FROM leads WHERE email = ?', (state['data']['email'],))
                    saved_lead = cursor.fetchone()
                    if saved_lead:
                        print(f"Lead guardado: {state['data']['name']}, {state['data']['email']}, ID: {saved_lead[0]}")
                    else:
                        print(f"Error: Lead no encontrado después de guardar: {state['data']['name']}, {state['data']['email']}")
            except sqlite3.Error as e:
                print(f"Error al guardar el lead: {e}")
                response = f"Error al guardar los datos: {e}. Por favor, intenta de nuevo."
            
            state['step'] = 4
            session['chat_state'] = state
            session.modified = True
            socketio.emit('message', {'text': ai_response or response}, to=sid)
        
        else:  # Fin de la conversación
            ai_response = generate_ai_response(state['data'], user_message)
            socketio.emit('message', {'text': ai_response or 'Gracias por charlar. Ya tenemos tus datos. ¡Pronto te contactaremos!'}, to=sid)
    
    except Exception as e:
        print(f"Error en el servidor: {e}")
        socketio.emit('message', {'text': f"Error en el servidor: {e}"}, to=sid)

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)