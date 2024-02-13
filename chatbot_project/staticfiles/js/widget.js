(function() {
    // Cargar Bootstrap CSS
    var bootstrapLink = document.createElement('link');
    bootstrapLink.rel = 'stylesheet';
    bootstrapLink.href = 'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css';
    document.head.appendChild(bootstrapLink);

    // Cargar estilos personalizados
    var customStylesLink = document.createElement('link');
    customStylesLink.rel = 'stylesheet';
    customStylesLink.href = '/static/css/widget.css'; 
    document.head.appendChild(customStylesLink);

    // Cargar jQuery
    var jqueryScript = document.createElement('script');
    jqueryScript.src = 'https://code.jquery.com/jquery-3.5.1.slim.min.js';
    document.body.appendChild(jqueryScript);

    // Cargar Popper.js
    var popperScript = document.createElement('script');
    popperScript.src = 'https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js';
    document.body.appendChild(popperScript);

    // Cargar Bootstrap JS
    var bootstrapScript = document.createElement('script');
    bootstrapScript.src = 'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js';
    document.body.appendChild(bootstrapScript);

    // Esperar a que jQuery y Popper.js estén cargados antes de inicializar el widget
    bootstrapScript.onload = function() {
        // Inicializar el widget aquí
        initChatWidget();
    };

    var isChatWidgetInitialized = false; // Controla si el widget ya fue inicializado

    function initChatWidget() {
        if (isChatWidgetInitialized) return; // Evita inicializar el widget más de una vez
        isChatWidgetInitialized = true;
    
        // Crear contenedor principal del widget de chat
        var chatWidgetDiv = document.createElement('div');
        chatWidgetDiv.classList.add('chat-widget');
        document.body.appendChild(chatWidgetDiv);
    
        // Agregar el HTML interno del widget de chat
        chatWidgetDiv.innerHTML = `
            <div class="chat-header">
                <a href="https://iconcreta.com/" target="_blank" class="chat-logo-link">
                    <img src="/static/img/logo.png" alt="Logo Empresa" class="chat-logo">
                </a>
                <button class="minimize-chat-btn">-</button>
                <button class="toggle-chat-btn">Chat</button>                
            </div>
            <div class="chat-container shadow-sm">
                <div id="chatBox" class="chat-content shadow-sm"></div>
                <div class="input-group">
                    <input type="text" id="messageInput" class="form-control" placeholder="Escribe tu mensaje aquí...">
                    <div class="input-group-append">
                    <button class="btn btn-primary" type="button">Enviar</button>
                    </div>
                </div>
            </div>
        `;
    
        var sendButton = chatWidgetDiv.querySelector('.input-group-append .btn');
        sendButton.addEventListener('click', function() {
            sendMessage();
        });
        
        // Crear y agregar el botón de maximizar fuera del chatWidgetDiv
        var minimizedIcon = document.createElement('div');
        minimizedIcon.className = 'minimized-icon';
        minimizedIcon.innerHTML = '+';
        minimizedIcon.onclick = function() { toggleChat(true); };
        minimizedIcon.style.display = 'none'; // Inicialmente oculto
        document.body.appendChild(minimizedIcon);
    
        var minimizeChatButton = chatWidgetDiv.querySelector('.minimize-chat-btn');
        var toggleChatButton = chatWidgetDiv.querySelector('.toggle-chat-btn');
    
        minimizeChatButton.addEventListener('click', function() {
            toggleChat(false); // Minimizar
        });
        toggleChatButton.addEventListener('click', function() {
            toggleChat(true); // Maximizar
        });
    
        function toggleChat(shouldOpen) {
            if (shouldOpen) {
                chatWidgetDiv.classList.add('open');
                chatWidgetDiv.classList.remove('minimized');
                minimizedIcon.style.display = 'none';
            } else {
                chatWidgetDiv.classList.remove('open');
                chatWidgetDiv.classList.add('minimized');
                minimizedIcon.style.display = 'flex'; // Asegura que el botón de maximizar se muestre cuando el chat se minimiza
            }
        }
    
        // Funciones para manipular el widget de chat
        function sendMessage(messageToSend = null, optionText = null) {
            var messageInput = chatWidgetDiv.querySelector('#messageInput');
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

        function handleBotOptions(options) {
            var chatBox = chatWidgetDiv.querySelector('#chatBox');
            removePreviousOptions();

            if (options && options.length > 0) {
                options.forEach(function(option) {
                    var optionButton = document.createElement('button');
                    optionButton.textContent = option.text;
                    optionButton.classList.add('option-button', 'btn', 'btn-primary', 'm-2');
                    optionButton.onclick = function() {
                        sendMessage(option.value, option.text);
                    };
                    chatBox.appendChild(optionButton);
                });
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function removePreviousOptions() {
            var chatBox = chatWidgetDiv.querySelector('#chatBox');
            var optionButtons = chatBox.querySelectorAll('.option-button');
            optionButtons.forEach(function(button) {
                chatBox.removeChild(button);
            });
        }

        function appendMessage(sender, message, isHtml = false) {
            var chatBox = chatWidgetDiv.querySelector('#chatBox');
            var messageDiv = document.createElement('div');
            messageDiv.classList.add('message');

            if (sender === 'user') {
                messageDiv.classList.add('user-message');
                message = 'Tú: ' + message;
            } else {
                messageDiv.classList.add('bot-message');
                message = 'Alejandra: ' + message;
            }

            if (isHtml) {
                messageDiv.innerHTML = message;
            } else {
                messageDiv.textContent = message;
            }

            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function debeHabilitarCampoDeEntrada(options) {
            return options.length === 0;
        }

        // Inicialización y eventos
        var input = chatWidgetDiv.querySelector('#messageInput');
        input.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                sendMessage();
            }
        });

        sendMessage('inicio');
    }

    // Verificar si el DOM está completamente cargado
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChatWidget);
    } else {
        initChatWidget();
    }
})();