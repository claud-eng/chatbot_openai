(function () {
    // Cargar estilos personalizados
    var customStylesLink = document.createElement('link');
    customStylesLink.rel = 'stylesheet';
    var currentUrl = window.location.href;
    var url = new URL(currentUrl);
    var domain = url.hostname;

    // Cargar archivo CSS dependiendo de la URL
    if (domain.includes('probar.iconcreta.com')) {
        customStylesLink.href = '/static/css/widget2.css';
    } else if (domain.includes('www.prueba.com')) {
        customStylesLink.href = '/static/css/prueba.css';
    } else if (domain.includes('www.test.cl')) {
        customStylesLink.href = '/static/css/test.css';
    } else {
        customStylesLink.href = '/static/css/widget.css'; // Archivo CSS por defecto
    }

    document.head.appendChild(customStylesLink);

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
                <div class="chat-logo-text">
                    Desarrollado por <br><a href="https://iconcreta.com/" target="_blank">www.iconcreta.com</a>
                </div>
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
        sendButton.addEventListener('click', function () {
            sendMessage();
        });

        // Crear y agregar el botón de maximizar fuera del chatWidgetDiv
        var minimizedIcon = document.createElement('div');
        minimizedIcon.className = 'minimized-icon';
        minimizedIcon.innerHTML = '+';
        minimizedIcon.onclick = function () { toggleChat(true); };
        minimizedIcon.style.display = 'none'; // Inicialmente oculto
        document.body.appendChild(minimizedIcon);

        var minimizeChatButton = chatWidgetDiv.querySelector('.minimize-chat-btn');
        var toggleChatButton = chatWidgetDiv.querySelector('.toggle-chat-btn');

        minimizeChatButton.addEventListener('click', function () {
            toggleChat(false); // Minimizar
        });
        toggleChatButton.addEventListener('click', function () {
            toggleChat(true); // Maximizar
        });

        // Cargar el estado guardado del chat
        var chatState = loadChatState();
        toggleChat(chatState === 'open'); // Llama directamente a la función con true o false según el estado guardado

        // Funciones para manipular el widget de chat
        function toggleChat(shouldOpen) {
            if (shouldOpen) {
                chatWidgetDiv.classList.add('open');
                chatWidgetDiv.classList.remove('minimized');
                minimizedIcon.style.display = 'none';
                saveChatState(true); // Guardar el estado como abierto
            } else {
                chatWidgetDiv.classList.remove('open');
                chatWidgetDiv.classList.add('minimized');
                minimizedIcon.style.display = 'flex'; // Asegura que el botón de maximizar se muestre cuando el chat se minimiza
                saveChatState(false); // Guardar el estado como minimizado
            }
        }

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

                var chatSessionId = getWithExpiry('chatSessionId');
                if (!chatSessionId) {
                    chatSessionId = generateUniqueId();
                    setWithExpiry('chatSessionId', chatSessionId, 2 * 24 * 60 * 60 * 1000); // 2 días en milisegundos
                }

                var urlActual = window.location.href;

                fetch(`/chatbot/flujo_dptos_casas/?message=${encodeURIComponent(message)}&url=${encodeURIComponent(urlActual)}&chatSessionId=${chatSessionId}`, {
                    credentials: 'include'
                })
                .then(response => response.json())
                .then(data => {
                    appendMessage('bot', data.respuesta, data.respuesta.includes('href=') || data.respuesta.includes('<a '));
                    handleBotOptions(data.options, data.state); // Pasa el estado actual al manejar las opciones
                    if (debeHabilitarCampoDeEntrada(data.options)) {
                        messageInput.removeAttribute('disabled');
                    }
                    saveConversationState(); // Guardar el estado de la conversación
                })
                .catch(error => {
                    console.error('Error:', error);
                    messageInput.removeAttribute('disabled');
                });
            }
        }

        // Función para generar un ID único
        function generateUniqueId() {
            return Math.random().toString(36).substr(2, 9);
        }

        // Función para manejar las opciones del bot
        function handleBotOptions(options, state) {
            var chatBox = chatWidgetDiv.querySelector('#chatBox');
            removePreviousOptions(); // Eliminar las opciones anteriores

            if (options && options.length > 0) {
                setWithExpiry('chatBotOptionsAvailable', 'true', 2 * 24 * 60 * 60 * 1000); // 2 días en milisegundos

                if (state === 'seleccionando_proyecto' && options.length === 1) {
                    // Selección automática para flujo 'seleccionando_proyecto' con una sola opción
                    sendMessage(options[0].value, options[0].text, true);
                    return;
                }

                options.forEach(function (option) {
                    var optionButton = document.createElement('button');
                    optionButton.textContent = option.text;
                    optionButton.classList.add('option-button', 'btn', 'btn-primary', 'm-2');
                    optionButton.setAttribute('data-value', option.value);
                    optionButton.onclick = function () {
                        disableOptionButtons();
                        sendMessage(option.value, option.text);
                    };
                    chatBox.appendChild(optionButton);
                });
                chatBox.scrollTop = chatBox.scrollHeight;
                return;
            }
            removeItemWithExpiry('chatBotOptionsAvailable'); // No hay opciones disponibles
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        // Función para deshabilitar botones de opciones
        function disableOptionButtons() {
            var optionButtons = chatWidgetDiv.querySelectorAll('.option-button');
            optionButtons.forEach(function (button) {
                button.setAttribute('disabled', 'disabled');
            });
        }

        // Función para eliminar opciones anteriores
        function removePreviousOptions() {
            var chatBox = chatWidgetDiv.querySelector('#chatBox');
            var optionButtons = chatBox.querySelectorAll('.option-button');
            optionButtons.forEach(function (button) {
                chatBox.removeChild(button);
            });
        }

        // Función para añadir mensaje al chat
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

        // Función para determinar si el campo de entrada debe estar habilitado
        function debeHabilitarCampoDeEntrada(options) {
            return options.length === 0;
        }

        // Funciones para guardar y cargar el estado de la conversación
        function saveConversationState() {
            var chatBox = chatWidgetDiv.querySelector('#chatBox');
            var messages = chatBox.innerHTML;
            setWithExpiry('chatConversationState', messages, 2 * 24 * 60 * 60 * 1000); // 2 días en milisegundos
            
            var chatOptions = [];
            chatWidgetDiv.querySelectorAll('.option-button').forEach(button => {
                chatOptions.push({ text: button.textContent, value: button.getAttribute('data-value') });
            });
            setWithExpiry('chatBotOptionsState', JSON.stringify(chatOptions), 2 * 24 * 60 * 60 * 1000); // 2 días en milisegundos
        }

        // Función para cargar el estado de la conversación
        function loadConversationState() {
            var chatBox = chatWidgetDiv.querySelector('#chatBox');
            var messages = getWithExpiry('chatConversationState');
            if (messages) {
                chatBox.innerHTML = messages;
                chatBox.scrollTop = chatBox.scrollHeight;
                
                var chatOptions = getWithExpiry('chatBotOptionsState');
                if (chatOptions) {
                    removePreviousOptions(); // Eliminar las opciones anteriores antes de restaurar
                    var options = JSON.parse(chatOptions);
                    options.forEach(option => {
                        var optionButton = document.createElement('button');
                        optionButton.textContent = option.text;
                        optionButton.classList.add('option-button', 'btn', 'btn-primary', 'm-2');
                        optionButton.setAttribute('data-value', option.value);
                        optionButton.onclick = function () {
                            disableOptionButtons();
                            sendMessage(option.value, option.text);
                        };
                        chatBox.appendChild(optionButton);
                    });
                    chatBox.scrollTop = chatBox.scrollHeight;
                    return true; // Indica que se ha cargado un estado de conversación
                }
            }
            return false; // No se encontró un estado de conversación anterior
        }

        // Función para guardar el estado del chatbot (minimizado o maximizado)
        function saveChatState(isOpen) {
            setWithExpiry('chatWidgetState', isOpen ? 'open' : 'minimized', 2 * 24 * 60 * 60 * 1000); // 2 días en milisegundos
        }

        // Función para cargar el estado del chatbot
        function loadChatState() {
            return getWithExpiry('chatWidgetState');
        }

        // Inicialización y eventos
        var input = chatWidgetDiv.querySelector('#messageInput');
        input.addEventListener('keypress', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                sendMessage();
            }
        });

        if (!loadConversationState()) { // Cargar el estado de la conversación, si no hay, enviar el mensaje de inicio
            sendMessage('inicio');
        }

        // Restaurar el estado de las opciones al cargar
        if (getWithExpiry('chatBotOptionsAvailable') === 'true') {
            input.setAttribute('disabled', 'disabled'); // Deshabilitar el campo de entrada si hay opciones disponibles
        }
    }

    // Verificar si el DOM está completamente cargado
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChatWidget);
    } else {
        initChatWidget();
    }

    // Funciones para manejar el almacenamiento con expiración
    function setWithExpiry(key, value, ttl) {
        const now = new Date();

        // item es un objeto que contiene el valor y la fecha de expiración
        const item = {
            value: value,
            expiry: now.getTime() + ttl,
        }
        localStorage.setItem(key, JSON.stringify(item));
    }

    // Función para obtener datos con expiración de localStorage
    function getWithExpiry(key) {
        const itemStr = localStorage.getItem(key);

        // Si el item no existe, devuelve null
        if (!itemStr) {
            return null;
        }

        const item = JSON.parse(itemStr);
        const now = new Date();

        // Compara la fecha de expiración con la fecha actual
        if (now.getTime() > item.expiry) {
            // Si el item ha expirado, elimínalo de localStorage
            localStorage.removeItem(key);
            return null;
        }
        return item.value;
    }

    // Función para eliminar datos de localStorage
    function removeItemWithExpiry(key) {
        localStorage.removeItem(key);
    }

})();

