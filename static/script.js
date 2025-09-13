// Conexión al servidor WebSocket
const socket = io('http://127.0.0.1:5000', { 
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 5
});

// Conexión establecida
socket.on('connect', () => {
    console.log('Conectado al servidor WebSocket');
});

// Error de conexión
socket.on('connect_error', (error) => {
    console.log('Error de conexión WebSocket:', error);
});

// Recibir mensajes del servidor
socket.on('message', (data) => {
    console.log('Mensaje recibido del servidor:', data.text);
    removeTypingIndicator();

    const messages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';
    messageDiv.textContent = data.text || 'Mensaje vacío recibido';
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
});

// Mostrar botones de sugerencia enviados por el servidor
socket.on('prompt_buttons', (data) => {
    console.log('Botones recibidos:', data.buttons);

    const messages = document.getElementById('chat-messages');
    const buttonsDiv = document.createElement('div');
    buttonsDiv.className = 'buttons';

    data.buttons.forEach(buttonText => {
        const btn = document.createElement('button');
        btn.textContent = buttonText;
        btn.style.margin = '5px';
        btn.onclick = () => {
            document.getElementById('chat-input').value = buttonText;
            sendMessage();
            buttonsDiv.remove();
        };
        buttonsDiv.appendChild(btn);
    });

    messages.appendChild(buttonsDiv);
    messages.scrollTop = messages.scrollHeight;
});

// Enviar mensaje al servidor
function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    // Mostrar mensaje del usuario en la UI
    const messages = document.getElementById('chat-messages');
    const userDiv = document.createElement('div');
    userDiv.className = 'message user';
    userDiv.textContent = message;
    messages.appendChild(userDiv);
    messages.scrollTop = messages.scrollHeight;

    console.log('Enviando mensaje al servidor:', message);
    socket.emit('message', { text: message });
    input.value = '';

    addTypingIndicator();
}

// Indicador de escritura del bot
function addTypingIndicator() {
    const messages = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typing-indicator';
    typingDiv.className = 'message bot';
    typingDiv.textContent = 'Escribiendo...';
    messages.appendChild(typingDiv);
    messages.scrollTop = messages.scrollHeight;
}

// Remover indicador de escritura
function removeTypingIndicator() {
    const typingDiv = document.getElementById('typing-indicator');
    if (typingDiv) typingDiv.remove();
}

// Enviar mensaje al presionar Enter
document.getElementById('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
