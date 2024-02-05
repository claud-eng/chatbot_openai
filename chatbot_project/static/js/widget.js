function handleBotOptions(options) {
    
    var chatBox = document.getElementById('chatBox');
    removePreviousOptions(); // Limpia las opciones anteriores del chatBox

    if (options && options.length > 0) {
        options.forEach(function(option) {
            var optionButton = document.createElement('button');
            optionButton.textContent = option.text;
            optionButton.classList.add('option-button', 'btn', 'btn-primary', 'm-2');
            optionButton.onclick = function() {
                sendMessage(option.value, option.text); // Envía el valor de la opción
            };
            chatBox.appendChild(optionButton); // Agrega el botón directamente al chatBox
        });
    }
    // Desplaza el chatBox a la última opción añadida
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removePreviousOptions() {

    var chatBox = document.getElementById('chatBox');
    var optionButtons = chatBox.querySelectorAll('.option-button');
    optionButtons.forEach(function(button) {
        chatBox.removeChild(button);
    });
}

function appendMessage(sender, message, isHtml = false) {
    var chatBox = document.getElementById('chatBox');
    var messageDiv = document.createElement('div');
    messageDiv.classList.add('message');

    // Asigna las clases para diferenciar los mensajes del usuario y del bot.
    if (sender === 'user') {
        messageDiv.classList.add('user-message');
        message = 'Tú: ' + message; // Añade "Tú: " antes del mensaje del usuario.
    } else {
        messageDiv.classList.add('bot-message');
        message = 'Alejandra: ' + message; // Añade "Alejandra: " antes del mensaje del bot.
    }

    // Añade el mensaje como HTML o texto.
    if (isHtml) {
        messageDiv.innerHTML = message;
    } else {
        messageDiv.textContent = message;
    }

    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight; // Desplaza hasta el último mensaje.
}

document.addEventListener('DOMContentLoaded', function() {
    var input = document.getElementById('messageInput');
    input.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault(); // Evita que se cree una nueva línea en el input si es un textarea.
            sendMessage(); // Llama a la función sendMessage cuando se presiona Enter.
        }
    });
});

function sendMessage(messageToSend = null, optionText = null) {
    var messageInput = document.getElementById('messageInput');
    var message = messageToSend || messageInput.value.trim();
    var displayMessage = optionText || message;

    if (message) {
        if (messageToSend !== 'inicio') {
            appendMessage('user', displayMessage);
        }
        messageInput.value = '';
        messageInput.setAttribute('disabled', 'disabled');

        fetch('/chatbot/chat/?message=' + encodeURIComponent(message))
            .then(response => response.json())
            .then(data => {
                appendMessage('bot', data.respuesta, data.respuesta.includes('href=') || data.respuesta.includes('<a '));
                handleBotOptions(data.options);
                // Solo habilita el campo de entrada si es necesario.
                if (debeHabilitarCampoDeEntrada(data.options)) {
                    messageInput.removeAttribute('disabled');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                messageInput.removeAttribute('disabled');
            });
    }
}

function debeHabilitarCampoDeEntrada(options) {
    // Habilita el campo de entrada solo si no hay opciones de botón presentadas al usuario.
    return options.length === 0;
}

function toggleChat() {
    var chatWidget = document.querySelector('.chat-widget');
    var minimizedIcon = document.querySelector('.minimized-icon');

    // Alternar la visibilidad del chat y el ícono de minimizado
    chatWidget.classList.toggle('open');
    chatWidget.classList.toggle('minimized');
    minimizedIcon.style.display = chatWidget.classList.contains('minimized') ? 'flex' : 'none';
}

function minimizeChat() {
    var chatWidget = document.querySelector('.chat-widget');
    var minimizedIcon = document.querySelector('.minimized-icon');
    
    // Ocultar el chat y mostrar el ícono de minimizado
    chatWidget.classList.remove('open');
    chatWidget.classList.add('minimized');
    minimizedIcon.style.display = 'flex';
}

window.onload = function() {
    var chatWidget = document.querySelector('.chat-widget');
    var messageInput = document.getElementById('messageInput');

    if (!chatWidget.classList.contains('open')) {
        chatWidget.classList.add('open');
    }

    // Deshabilita el campo de entrada al cargar la página y después de cualquier interacción.
    // Nota: Esto asume que la función sendMessage no habilita el campo de entrada.
    messageInput.disabled = true;

    // Envía el mensaje de inicio para obtener las opciones iniciales.
    sendMessage('inicio');
};