const socket = io('http://127.0.0.1:5000', { 
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 5
});

socket.on('connect', () => {
    console.log('Conectado al servidor WebSocket');
});

socket.on('connect_error', (error) => {
    console.log('Error de conexión WebSocket:', error);
});

socket.on('message', (data) => {
    console.log('Mensaje recibido del servidor:', data.text); // Mostrar data.text
    removeTypingIndicator();
    const messages = document.getElementById('chat-messages');
    const message = document.createElement('div');
    message.className = 'message bot';
    message.textContent = data.text || 'Mensaje vacío recibido';
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
});

socket.on('prompt_buttons', (data) => {
    console.log('Botones recibidos:', data.buttons);
    const messages = document.getElementById('chat-messages');
    const buttonsDiv = document.createElement('div');
    buttonsDiv.className = 'buttons';
    data.buttons.forEach(button => {
        const btn = document.createElement('button');
        btn.textContent = button;
        btn.style.margin = '5px';
        btn.onclick = () => {
            document.getElementById('chat-input').value = button;
            sendMessage();
            buttonsDiv.remove();
        };
        buttonsDiv.appendChild(btn);
    });
    messages.appendChild(buttonsDiv);
    messages.scrollTop = messages.scrollHeight;
});

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) {
        console.log('No se envió mensaje: entrada vacía');
        return;
    }

    const messages = document.getElementById('chat-messages');
    const userMessage = document.createElement('div');
    userMessage.className = 'message user';
    userMessage.textContent = message;
    messages.appendChild(userMessage);

    console.log('Enviando mensaje al servidor:', message);
    socket.emit('message', { text: message });
    console.log('Mensaje enviado:', message);

    input.value = '';
    messages.scrollTop = messages.scrollHeight;
    addTypingIndicator();
}

function addTypingIndicator() {
    const messages = document.getElementById('chat-messages');
    const typing = document.createElement('div');
    typing.id = 'typing-indicator';
    typing.className = 'message bot';
    typing.textContent = 'Escribiendo...';
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;
}

function removeTypingIndicator() {
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
}

document.getElementById('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        console.log('Tecla Enter presionada, enviando mensaje');
        sendMessage();
    }
});