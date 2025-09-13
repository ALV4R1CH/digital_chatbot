const socket = io('http://127.0.0.1:5000', { transports:['websocket','polling'], reconnection:true });

socket.on('connect', () => console.log('Conectado al servidor WebSocket'));
socket.on('connect_error', (err) => console.log('Error de conexión:', err));

socket.on('message', (data) => { removeTypingIndicator(); appendMessage(data.text, 'bot'); });

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    appendMessage(message, 'user');
    socket.emit('message', { text: message });
    input.value = '';
    addTypingIndicator();
}

function appendMessage(text, sender) {
    const messages = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    msgDiv.textContent = text;
    messages.appendChild(msgDiv);
    messages.scrollTop = messages.scrollHeight;
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

document.getElementById('chat-input').addEventListener('keypress', (e) => { if(e.key==='Enter') sendMessage(); });
