from flask import Flask, render_template, request, session
from flask_socketio import SocketIO
import sqlite3
from datetime import datetime
import os
from groq import Groq

# Configuración
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'super_secret_key')
socketio = SocketIO(app, cors_allowed_origins=['http://127.0.0.1:5500', 'http://localhost:5500', 'http://127.0.0.1:5000'], async_mode='eventlet')

# Inicializar cliente Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
groq_client = Groq(api_key=GROQ_API_KEY)

# Inicializar DB
def init_db():
    with sqlite3.connect('leads.db') as conn:
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

# Función para generar respuesta con Groq
def generate_ai_response(state, user_message):
    history = "Eres un asistente amigable llamado 'Digi' que recopila información del cliente.\n"
    for k, v in state.items():
        if k != 'step':
            history += f"- {k}: {v}\n"
    prompt = f"{history} El usuario dice: {user_message}\nResponde en español de forma natural."

    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Error al generar respuesta con Groq:", e)
        return "Lo siento, tuve un problema generando la respuesta."

# Función de recomendaciones
def get_recommendations(business_type):
    recs = {
        'restaurante': ["Sitio web con reservas online", "SEO local para Google Maps"],
        'tienda': ["Tienda online con e-commerce", "Automatización de inventario"],
        'servicios': ["CRM para gestión de clientes", "Campañas de email marketing"],
        'default': ["Sitio web profesional", "Análisis de datos para decisiones"]
    }
    return recs.get(business_type.lower(), recs['default'])

# Rutas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

# WebSocket
@socketio.on('connect')
def connect():
    session['chat_state'] = {'step': 0, 'name': '', 'email': '', 'business_type': '', 'needs': ''}
    session.modified = True
    socketio.emit('message', {'text': '¡Hola! Soy tu asistente digital. ¿Cuál es tu nombre?'}, to=request.sid)

# Manejo de pasos
def handle_step(state, user_message, sid):
    step = state['step']

    if step == 0:
        state['name'] = user_message
        state['step'] = 1
        ai_resp = generate_ai_response(state, user_message)
    elif step == 1:
        if '@' not in user_message:
            socketio.emit('message', {'text': 'Por favor, ingresa un email válido.'}, to=sid)
            return
        state['email'] = user_message
        state['step'] = 2
        ai_resp = generate_ai_response(state, user_message)
    elif step == 2:
        state['business_type'] = user_message
        state['step'] = 3
        ai_resp = generate_ai_response(state, user_message)
    elif step == 3:
        state['needs'] = user_message
        ai_resp = generate_ai_response(state, user_message)

        # Guardar en DB
        try:
            with sqlite3.connect('leads.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO leads (name,email,business_type,needs) VALUES (?,?,?,?)',
                    (state['name'], state['email'], state['business_type'], state['needs'])
                )
                conn.commit()
        except Exception as e:
            print("Error guardando lead:", e)
            ai_resp += "\nHubo un error guardando los datos."

        state['step'] = 4
    else:
        ai_resp = "Gracias, ya tenemos tus datos. ¡Pronto te contactaremos!"

    session['chat_state'] = state
    session.modified = True
    socketio.emit('message', {'text': ai_resp}, to=sid)

@socketio.on('message')
def handle_message(data):
    sid = request.sid
    user_message = data.get('text', '').strip()
    state = session.get('chat_state', {'step': 0})
    handle_step(state, user_message, sid)

# Ejecutar app
if __name__ == '__main__':
    init_db()
    socketio.run(app, port=5000)
