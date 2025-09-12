import eventlet
import eventlet.wsgi
from app import app, socketio

def main():
    """Inicia el servidor de la aplicación."""
    print("Iniciando servidor en http://127.0.0.1:5000")
    eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 5000)), app)

if __name__ == "__main__":
    main()