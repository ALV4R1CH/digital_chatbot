from flask import Flask, render_template, request, session
from flask_socketio import SocketIO
import sqlite3
import os
from dotenv import load_dotenv
from groq import Groq

# Cargar variables de entorno
load_dotenv()

# Configuración Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'super_secret_key')
socketio = SocketIO(app, cors_allowed_origins=[
    'http://127.0.0.1:5500',
    'http://localhost:5500',
    'http://127.0.0.1:5000',
    'http://localhost:5000',
    'https://kaisa-chatbot.onrender.com'
], async_mode='eventlet')

# Inicializar cliente Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    print("Error: La variable de entorno GROQ_API_KEY no está configurada.")
    groq_client = None
else:
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
def generate_ai_response(state, user_message, step):
    system_prompt = (
        "Eres Kaisa, una asistente digital amigable, profesional y con un toque de humor ligero. "
        "Tu objetivo es recopilar información de contacto del cliente (nombre, email, tipo de negocio, necesidades) "
        "y ofrecer recomendaciones iniciales para vender páginas web."
    )
    history = f"Contexto:\n- Nombre: {state.get('name','N/A')}\n- Email: {state.get('email','N/A')}\n- Negocio: {state.get('business_type','N/A')}\n- Necesidades: {state.get('needs','N/A')}"

    prompts_by_step = {
        0: f"El usuario acaba de dar su nombre: '{user_message}'. Preséntate y pídele su correo electrónico.",
        1: f"El usuario proporcionó su email: '{user_message}'. Pregúntale sobre su tipo de negocio.",
        2: f"El usuario mencionó su negocio: '{user_message}'. Pregúntale qué necesita o qué problemas quiere resolver con una página web.",
        3: f"El usuario indicó sus necesidades: '{user_message}'. Agradécele, confirma que los datos fueron guardados y que el equipo se pondrá en contacto."
    }
    instruction = prompts_by_step.get(step, "La conversación ha terminado. Agradece al usuario.")

    full_prompt = f"{system_prompt}\n\n{history}\n\nTarea actual:\n{instruction}"

    try:
        if not groq_client:
            raise Exception("Cliente Groq no inicializado.")
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": full_prompt}],
            model="llama-3.3-70b-versatile",
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Error generando respuesta con Groq:", e)
        return "Lo siento, tuve un problema generando la respuesta."

# Recomendaciones iniciales
def get_recommendations(business_type):
    recs = {
        'restaurante': ["Sitio web con reservas online", "SEO local para Google Maps", "Menú digital interactivo"],
        'tienda': ["Tienda online con carrito de compras", "Automatización de inventario", "Campañas en redes sociales"],
        'servicios': ["Landing pages personalizadas", "CRM para gestión de clientes", "Email marketing"],
        'default': ["Sitio web profesional", "Optimización para móviles", "Estrategias de marketing digital"]
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
    socketio.emit('message', {'text': '¡Hola! Soy Kaisa, tu asistente digital. ¿Cuál es tu nombre?'}, to=request.sid)

# Manejo de pasos
def step_0(state, msg, sid):
    state['name'] = msg
    state['step'] = 1
    return generate_ai_response(state, msg, 0)

def step_1(state, msg, sid):
    if '@' not in msg:
        socketio.emit('message', {'text': 'Ingresa un email válido, por favor.'}, to=sid)
        return None
    state['email'] = msg
    state['step'] = 2
    return generate_ai_response(state, msg, 1)

def step_2(state, msg, sid):
    state['business_type'] = msg
    state['step'] = 3
    return generate_ai_response(state, msg, 2)

def step_3(state, msg, sid):
    state['needs'] = msg
    ai_resp = generate_ai_response(state, msg, 3)
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
        ai_resp += "\n(Hubo un error guardando los datos, pero no te preocupes, lo revisaremos)."
    state['step'] = 4
    return ai_resp

def step_4(state, msg, sid):
    return "¡Gracias! Hemos registrado tus datos. Nuestro equipo se pondrá en contacto contigo pronto."

step_handlers = [step_0, step_1, step_2, step_3, step_4]

@socketio.on('message')
def handle_message(data):
    sid = request.sid
    user_message = data.get('text','').strip()
    state = session.get('chat_state', {'step':0})
    step = state.get('step',0)

    if 0 <= step < len(step_handlers):
        handler = step_handlers[step]
        ai_resp = handler(state, user_message, sid)
        session['chat_state'] = state
        session.modified = True
        if ai_resp:
            socketio.emit('message', {'text': ai_resp}, to=sid)

# Ejecutar app
if __name__ == '__main__':
    init_db()
    print("Servidor iniciado. Clave Groq cargada correctamente." if GROQ_API_KEY else "Servidor iniciado. Groq no cargada.")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
