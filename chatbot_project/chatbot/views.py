from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
import json
import os 
from .functions import *
from .validators import *

def cargar_comunas():
    # Ruta al archivo comunas.jsonl
    jsonl_path = os.path.join(settings.BASE_DIR, 'chatbot/comunas.jsonl')
    comunas = {}
    with open(jsonl_path, 'r', encoding='utf-8') as file:  # Especificar la codificación aquí
        for line in file:
            comuna = json.loads(line)
            comunas[comuna["Comuna Oficial"]] = True
    return comunas

# Esta variable se inicializará en la primera solicitud HTTP que se procese
comunas_chile = None

def chat(request):

    global comunas_chile
    # Cargar comunas si aún no se han cargado
    if comunas_chile is None:
        comunas_chile = cargar_comunas()

    # Obtener solo el dominio y el puerto de la solicitud
    host = request.get_host()

    # Determinar el proyecto basado en el dominio
    if 'localhost:8000' in host:
        project = 'Test 1'
    elif '127.0.0.1:8000' in host:
        project = 'Test 2'
    elif 'otrodominio.com' in host:
        project = 'Test 3'
    else:
        project = 'Desconocido'

    user_message = request.GET.get('message', '').strip().lower()
    session_data = request.session.get('chat_data', {'state': 'inicio', 'context': []})

    # Mapeo de los valores a texto amigable
    precio_a_texto = {
        'menos_1800': 'Menos de 1800 UF',
        'entre_1800_2499': 'Entre 1800 y 2499 UF',
        'entre_2500_3999': 'Entre 2500 y 3999 UF',
        'entre_4000_6999': 'Entre 4000 y 6999 UF',
        'mas_7000': 'Más de 7000 UF'
    }

    # Obtener el rango de precio en texto amigable
    precio_texto_amigable = next((precio_a_texto[item['rango_precio']] for item in session_data['context'] if 'rango_precio' in item), "Desconocido")

    if 'context' not in session_data:
        session_data['context'] = []
        
    response = ''
    options = []

    # Verificar si el usuario viene de hacer un reclamo o de finalizar cotización
    from_reclamo = session_data.get('from_reclamo', False)
    from_cotizacion = session_data.get('from_cotizacion', False)

    # Reiniciar las banderas para futuras interacciones.
    session_data['from_reclamo'] = False
    session_data['from_cotizacion'] = False

    # Verificar si el mensaje es 'inicio' y si viene de alguno de los flujos anteriores.
    if user_message == 'inicio':
        # Esto reinicia completamente la sesión para un nuevo usuario
        session_data.clear()  # Esto eliminará todos los datos existentes en la sesión
        session_data['state'] = 'inicio'
        session_data['context'] = []
        session_data['ha_dado_telefono'] = False  
        if from_reclamo or from_cotizacion:
            response = 'Hola nuevamente, ¿En qué puedo ayudarte esta vez?'
        else:
            response = 'Hola, soy un Asistente Virtual, ¿En qué puedo ayudarte?'
        session_data['state'] = 'inicio'
        options = [
            {'text': 'Necesito ayuda para cotizar', 'value': 'cotizar'},
            {'text': 'Deseo realizar un reclamo', 'value': 'reclamo'}
        ]

    elif session_data['state'] == 'inicio':
        if 'cotizar' in user_message:
            session_data['state'] = 'solicitando_nombre'
            response = '¡Gracias por tu interés en nuestro proyecto! Para una atención más personalizada, ¿Podrías indicarme tu nombre por favor?'
        elif 'reclamo' in user_message:
            session_data['state'] = 'inicio'  # Reiniciamos la conversación
            session_data['from_reclamo'] = True  # Marcamos que viene de hacer un reclamo
            response = 'Lamento saber que tienes un reclamo. Por favor, sigue las instrucciones en la sección contáctanos en el siguiente enlace: <a href="https://www.google.cl" target="_blank">https://www.google.cl</a>'
            options = [
                {'text': 'Continuar', 'value': 'inicio'}
            ]

    elif session_data['state'] == 'solicitando_nombre':
        if is_potential_name(user_message):
            # Utiliza OpenAI para interpretar la intención completa
            prompt = f"El usuario dijo: '{user_message}'. Teniendo en cuenta que el usuario puede incluir agradecimientos o frases adicionales antes y/o después de dar su nombre (recordar que es opcional), el usuario en la frase que ha dicho, ¿En alguna parte menciona su nombre? responde si o no (tener en cuenta de que algunas personas de manera opcional puede que ingresen sus dos nombres y dos apellidos). Sólo es obligatorio ingresar el primer nombre"
            response_openai = generate_openai_response(prompt)
            if "sí" in response_openai.lower():
                # Prompt para extraer el nombre completo (nombre y apellido) del mensaje
                prompt_extraccion = f"Extrae el nombre completo (nombre y apellido) del siguiente texto: '{user_message}' (En caso de sólo haber un nombre sólo extrae eso, ya que el segundo nombre y los apellidos son opcionales)."
                nombre_completo = generate_openai_response(prompt_extraccion).strip()
                # Utiliza la función extraer_primer_nombre para obtener solo el primer nombre
                primer_nombre = extraer_primer_nombre(nombre_completo)
                session_data['context'].append({'nombre_completo': nombre_completo, 'primer_nombre': primer_nombre})
                session_data['state'] = 'solicitando_comuna'
                response = f'Gracias {primer_nombre}, ¿En qué comuna estás interesado en cotizar? Por favor sólo ingresa el nombre de una comuna.'
            else:
                response = 'Parece que no has ingresado tu nombre de manera válida. Por favor, intenta nuevamente ingresando al menos tu primer nombre.'
        else:
            response = 'Por favor, ingresa al menos tu primer nombre.'

    elif session_data['state'] == 'solicitando_comuna':
        # Normaliza y capitaliza la entrada del usuario
        comuna_usuario = capitalizar_comuna(quitar_acentos(user_message))

        # Normaliza las claves del diccionario comunas_chile para hacer la comparación insensible a acentos
        comunas_chile_normalizadas = {quitar_acentos(comuna).upper(): valor for comuna, valor in comunas_chile.items()}

        # Verifica si la comuna ingresada por el usuario, convertida a mayúsculas y sin acentos, se encuentra en el diccionario
        if comuna_usuario.upper() in comunas_chile_normalizadas:
            # La comuna ya está en el formato correcto para ser guardada gracias a la función capitalizar_comuna
            comuna_extraida = comuna_usuario
            session_data['context'].append({'comuna': comuna_extraida})
            session_data['state'] = 'solicitando_tipo_inmueble'
            
            # Verifica si el 'primer_nombre' se encuentra en el contexto
            primer_nombre = None
            for item in session_data['context']:
                if 'primer_nombre' in item:
                    primer_nombre = item['primer_nombre']
                    break
            
            response = f'Genial {primer_nombre}, ¿qué tipo de inmueble estás buscando?' if primer_nombre else 'Genial, ¿qué tipo de inmueble estás buscando?'
            options = [
                {'text': 'Departamento', 'value': 'departamento'},
                {'text': 'Casa', 'value': 'casa'}
            ]
        else:
            response = 'No he podido identificar una comuna válida en tu respuesta. Por favor, intenta ingresando el nombre de una comuna en Chile como Las Condes, Santiago Centro o La Florida, etc.'


    elif session_data['state'] == 'solicitando_tipo_inmueble':
        session_data['context'].append({'tipo_inmueble': user_message})
        session_data['state'] = 'solicitando_rango_precio'
        options = [
            {'text': 'Menos de 1800 UF', 'value': 'menos_1800'},
            {'text': 'Entre 1800 y 2499 UF', 'value': 'entre_1800_2499'},
            {'text': 'Entre 2500 y 3999 UF', 'value': 'entre_2500_3999'},
            {'text': 'Entre 4000 y 6999 UF', 'value': 'entre_4000_6999'},
            {'text': 'Más de 7000 UF', 'value': 'mas_7000'},
        ]
        response = 'Muy bien, ¿En qué rango de precios estás interesado?'

    elif session_data['state'] == 'solicitando_rango_precio':
        session_data['context'].append({'rango_precio': user_message})

        # Extraer el primer nombre del contexto para personalizar la respuesta
        primer_nombre = None
        for item in session_data['context']:
            if 'primer_nombre' in item:
                primer_nombre = item['primer_nombre']
                break

        # Utilizar un nombre predeterminado si no se encontró el primer nombre
        if primer_nombre is None:
            primer_nombre = "cliente"

        correo_existente = next((item for item in session_data['context'] if 'correo' in item), None)

        if correo_existente and not from_cotizacion:
            # Continuar sin solicitar el correo si ya se proporcionó en una cotización anterior
            session_data['state'] = 'solicitando_dormitorios'
            options = [
                {'text': '1 dormitorio', 'value': '1'},
                {'text': '2 dormitorios', 'value': '2'},
                {'text': '3 dormitorios', 'value': '3'},
                {'text': '4 dormitorios', 'value': '4'},
                {'text': 'Más de 4 dormitorios', 'value': '5+'},
            ]
            response = f"Perfecto, {primer_nombre}, ¿Cuántos dormitorios necesitas?"
        else:
            # Solicitar el correo en una nueva cotización
            session_data['state'] = 'solicitando_correo'
            response = f"Excelente {primer_nombre}, antes de continuar, ¿podrías proporcionarme tu correo electrónico para enviarte información detallada sobre tu cotización?"
            options = []

    elif session_data['state'] == 'solicitando_correo':
        # Verifica si el mensaje del usuario contiene un correo electrónico
        prompt_verificar_correo = f"El usuario dijo: '{user_message}'. ¿Contiene esto una dirección de correo electrónico válida? Responde 'sí' o 'no'."
        respuesta_verificar_correo = generate_openai_response(prompt_verificar_correo)
        
        if "sí" in respuesta_verificar_correo.lower():
            # Si hay un correo, intenta extraerlo
            prompt_extraer_correo = f"Extrae la dirección de correo electrónico del siguiente mensaje del usuario: '{user_message}'."
            correo_extraido = generate_openai_response(prompt_extraer_correo).strip()
            
            # Valida el correo extraído
            if validate_email(correo_extraido):
                # Si el correo es válido, continúa con el flujo
                session_data['context'].append({'correo': correo_extraido})
                session_data['state'] = 'solicitando_dormitorios'
                options = [
                    {'text': '1 dormitorio', 'value': '1'},
                    {'text': '2 dormitorios', 'value': '2'},
                    {'text': '3 dormitorios', 'value': '3'},
                    {'text': '4 dormitorios', 'value': '4'},
                    {'text': 'Más de 4 dormitorios', 'value': '5+'},
                ]
                response = '¡Gracias! ¿Cuántos dormitorios necesitas?'
            else:
                # Si OpenAI proporciona una cadena que no es un correo válido, solicita que se ingrese de nuevo
                response = 'El correo proporcionado no parece ser válido. Por favor, ingresa un correo electrónico válido.'
        else:
            # Si OpenAI indica que no hay un correo, solicita que se ingrese de nuevo
            response = 'No he detectado un correo electrónico en tu mensaje. Por favor, ingresa tu correo electrónico para continuar.'

    elif session_data['state'] == 'solicitando_dormitorios':
        # Asume que 'user_message' contiene la cantidad de dormitorios, por ejemplo, "2 dormitorios"
        cantidad_dormitorios = user_message.split()[0]  # Esto extraerá el número de la respuesta
        session_data['context'].append({'dormitorios': cantidad_dormitorios})
        session_data['state'] = 'solicitando_banos'  # Cambiamos el estado para solicitar los baños
        options = [
            {'text': '1 baño', 'value': '1'},
            {'text': '2 baños', 'value': '2'},
            {'text': '3 baños', 'value': '3'},
            {'text': '4 o más baños', 'value': '4+'},
        ]
        response = '¿Cuántos baños prefieres?'

    elif session_data['state'] == 'solicitando_banos':
        print("Estado actual: solicitando_banos")  # Depuración
        print(f"ha_dado_telefono antes de verificar: {session_data.get('ha_dado_telefono')}")  # Depuración
        # Extracción del primer nombre antes de usarlo en la respuesta
        primer_nombre = None
        for item in session_data['context']:
            if 'primer_nombre' in item:
                primer_nombre = item['primer_nombre']
                break

        if primer_nombre is None:
            primer_nombre = "cliente"  # O algún valor predeterminado si no se encuentra

        # Asume que 'user_message' contiene la cantidad de baños
        cantidad_banos = user_message.split()[0]  # Esto extraerá el número de la respuesta
        session_data['context'].append({'banos': cantidad_banos})

        # Inicializa variables para almacenar los valores necesarios
        tipo_inmueble = rango_precio = dormitorios = banos = None

        # Itera sobre el contexto para extraer los valores necesarios
        for item in session_data['context']:
            if 'tipo_inmueble' in item:
                tipo_inmueble = item['tipo_inmueble']
            elif 'rango_precio' in item:
                rango_precio = item['rango_precio']
            elif 'dormitorios' in item:
                dormitorios = item['dormitorios']
            elif 'banos' in item:
                banos = item['banos']

        # Verifica que todos los valores necesarios estén presentes
        if all(value is not None for value in [tipo_inmueble, rango_precio, dormitorios, banos]):
            productos = obtener_productos_activos(tipo_inmueble, rango_precio, dormitorios, banos)

            # Decide qué hacer con los productos obtenidos
            producto_destacado = obtener_producto_mas_barato(productos) if productos else None

            if producto_destacado:
                # Marca la búsqueda como exitosa
                session_data['busqueda_exitosa'] = True

                if session_data.get('ha_dado_telefono') is not None and session_data.get('cotizacion_subsecuente', False):
                    # Suponiendo que 'cotizacion_subsecuente' se establece a True después de la primera cotización
                    nombre_completo = next((item['nombre_completo'] for item in session_data['context'] if 'nombre_completo' in item), "Desconocido")
                    comuna = next((item['comuna'] for item in session_data['context'] if 'comuna' in item), "Desconocida")
                    correo = next((item['correo'] for item in session_data['context'] if 'correo' in item), "Desconocido")
                    telefono = next((item['telefono'] for item in session_data['context'] if 'telefono' in item), "")
                    precio_texto_amigable = next((precio_a_texto[item['rango_precio']] for item in session_data['context'] if 'rango_precio' in item), "Desconocido")
                    tipo_inmueble = next((item['tipo_inmueble'] for item in session_data['context'] if 'tipo_inmueble' in item), "Desconocido")
                    dormitorios = next((item['dormitorios'] for item in session_data['context'] if 'dormitorios' in item), "Desconocido")
                    banos = next((item['banos'] for item in session_data['context'] if 'banos' in item), "Desconocido")
                    
                    # Llamar a send_email
                    send_email(nombre_completo, comuna, correo, project, telefono, precio_texto_amigable, tipo_inmueble, dormitorios, banos)

                # Generar respuesta con OpenAI
                prompt_openai = (
                    f"Redacta un mensaje sólo limitándote a mencionar las características del producto, no debes dar mensajes de bienvenida como Hola, tampoco des mensajes de despedida y/o menciones el nombre del cliente, sólo debes ser breve, preciso y amigable, no debes sonar tan robótico, el mensaje debe comenzar diciendo Tenemos... "
                    f"basándote en los siguientes detalles del inmueble recomendado:\n\n"
                    f"Nombre del inmueble: {producto_destacado.get('Nombre')}\n"
                    f"Precio total en UF: {producto_destacado.get('PrecioTotalUF')}\n"
                )
                respuesta_openai = generate_openai_response(prompt_openai).strip()

                # Añadir la respuesta de OpenAI a la variable de respuesta
                response = f"{respuesta_openai} Te hemos enviado a tu correo electrónico más productos según tu cotización. Ha sido un placer ayudarte, {primer_nombre}."

                productos_aleatorios = obtener_productos_activos(tipo_inmueble, rango_precio, dormitorios, banos, cantidad=5)
                correo_destinatario = next((item['correo'] for item in session_data['context'] if 'correo' in item), None)

                if correo_destinatario and productos_aleatorios:
                    # Iniciar el contenido del correo con un saludo y una introducción
                    contenido_correo = f"Estimado/a {primer_nombre}, es un placer presentarte una selección exclusiva de propiedades que podrían ser de tu interés:<br><br>"
                    
                    # Iterar sobre los productos seleccionados, limitando a un máximo de 5
                    for producto in productos_aleatorios[:5]:
                        # Agregar cada producto al contenido del correo con un salto de línea HTML
                        contenido_correo += f"- {producto['Nombre']} a un precio de {producto['PrecioTotalUF']} UF<br>"
                    
                    # Agregar el cierre después de listar los productos
                    contenido_correo += "<br>Esperamos que estas opciones sean de tu agrado. Estamos a tu disposición para cualquier consulta o para ofrecerte más información. ¡Gracias por considerarnos en tu búsqueda de la propiedad perfecta!"
                    
                    # Enviar el correo con el contenido generado, asegurándose de que se envía como HTML
                    enviar_correo_con_seleccion(correo_destinatario, contenido_correo)

                # Verifica si ya se ha proporcionado el número de teléfono
                if not session_data.get('ha_dado_telefono', False):
                    print("ha_dado_telefono es False, se debería pedir el teléfono.")  # Depuración
                    response += " Para una forma de contacto más directa, ¿deseas otorgar tu número de teléfono?"
                    options = [
                        {'text': 'Sí, deseo dar mi número de teléfono', 'value': 'dar_telefono'},
                        {'text': 'No, gracias', 'value': 'no_dar_telefono'}
                    ]
                    session_data['state'] = 'solicitando_telefono'
                else:
                    print("ha_dado_telefono es True, no se pide el teléfono.")  # Depuración
                    # Continuar al estado de finalización si ya se ha dado el teléfono
                    response += " ¿Necesitas ayuda con otra cosa?"
                    options = [
                        {'text': 'Sí, quiero seguir cotizando', 'value': 'cotizar'},
                        {'text': 'No, volver a inicio', 'value': 'inicio'}
                    ]
                    session_data['state'] = 'finalizacion'
            else:
                if not producto_destacado:
                    # Verifica si ya se ha proporcionado el número de teléfono
                    if not session_data.get('ha_dado_telefono', False):
                        response = "Lo siento, no hemos encontrado inmuebles que coincidan con tus criterios. Para continuar con la cotización y tener una comunicación más directa, ¿te gustaría proporcionar un número de teléfono?"
                        options = [
                            {'text': 'Sí, deseo dar mi número de teléfono', 'value': 'dar_telefono'},
                            {'text': 'No, gracias', 'value': 'no_dar_telefono'}  
                        ]
                        session_data['state'] = 'solicitando_telefono'  # Cambio de estado para solicitar el teléfono
                    else:
                        response = "Lo siento, no hemos encontrado inmuebles que coincidan con tus criterios. ¿Te puedo asistir en algo más?"
                        options = [
                            {'text': 'Sí, quiero seguir cotizando', 'value': 'cotizar'},
                            {'text': 'No, gracias', 'value': 'inicio'}
                        ]
                        session_data['state'] = 'finalizacion'  # Cambia a finalización para manejar la siguiente acción
        else:
            # Si falta información, ofrece volver al paso donde falta la información.
            response = "Parece que falta información para completar tu solicitud. Por favor, verifica que has ingresado todos los datos requeridos."
            session_data['state'] = 'solicitando_banos'
            options = [
                {'text': '1 baño', 'value': '1'},
                {'text': '2 baños', 'value': '2'},
                {'text': '3 baños', 'value': '3'},
                {'text': '4 o más baños', 'value': '4+'},
            ]

    elif session_data['state'] == 'solicitando_telefono':
        if user_message == 'dar_telefono':
            response = "Por favor, ingresa tu número de teléfono."
            session_data['state'] = 'ingresando_telefono'
            options = []
        elif user_message == 'no_dar_telefono':
            session_data['ha_dado_telefono'] = True
            response = "Entendido. ¿Te puedo ayudar en algo más?"
            session_data['state'] = 'finalizacion'
            options = [
                {'text': 'Sí, quiero seguir cotizando', 'value': 'cotizar'},
                {'text': 'No, volver a inicio', 'value': 'inicio'}
            ]
            
            # Obtener datos del contexto para enviar por correo
            nombre_completo = next((item['nombre_completo'] for item in session_data['context'] if 'nombre_completo' in item), "Desconocido")
            comuna = next((item['comuna'] for item in session_data['context'] if 'comuna' in item), "Desconocida")
            correo = next((item['correo'] for item in session_data['context'] if 'correo' in item), "Desconocido")
            telefono = next((item['telefono'] for item in session_data['context'] if 'telefono' in item), "")
            precio_texto_amigable = next((precio_a_texto[item['rango_precio']] for item in session_data['context'] if 'rango_precio' in item), "Desconocido")
            tipo_inmueble = next((item['tipo_inmueble'] for item in session_data['context'] if 'tipo_inmueble' in item), "Desconocido")
            dormitorios = next((item['dormitorios'] for item in session_data['context'] if 'dormitorios' in item), "Desconocido")
            banos = next((item['banos'] for item in session_data['context'] if 'banos' in item), "Desconocido")
            
            # Llamar a send_email
            send_email(nombre_completo, comuna, correo, project, telefono, precio_texto_amigable, tipo_inmueble, dormitorios, banos)

    elif session_data['state'] == 'ingresando_telefono':
        # Primer paso: Verificación
        prompt_verificacion = f"¿La frase '{user_message}' contiene un número de teléfono con al menos 8 dígitos numéricos? sólo responde si o no"
        respuesta_verificacion = generate_openai_response(prompt_verificacion)

        # Preparar datos para enviar por correo
        nombre_completo = next((item['nombre_completo'] for item in session_data['context'] if 'nombre_completo' in item), "Desconocido")
        comuna = next((item['comuna'] for item in session_data['context'] if 'comuna' in item), "Desconocida")
        correo = next((item['correo'] for item in session_data['context'] if 'correo' in item), "Desconocido")
        telefono = next((item['telefono'] for item in session_data['context'] if 'telefono' in item), "")
        precio_texto_amigable = next((precio_a_texto[item['rango_precio']] for item in session_data['context'] if 'rango_precio' in item), "Desconocido")
        tipo_inmueble = next((item['tipo_inmueble'] for item in session_data['context'] if 'tipo_inmueble' in item), "Desconocido")
        dormitorios = next((item['dormitorios'] for item in session_data['context'] if 'dormitorios' in item), "Desconocido")
        banos = next((item['banos'] for item in session_data['context'] if 'banos' in item), "Desconocido")

        if respuesta_verificacion.lower() == "sí":
            # Segundo paso: Extracción y ajuste
            prompt_ajuste = f"Extrae y ajusta al formato chileno el número de teléfono presente en la frase '{user_message}'. El formato chileno es '+569' seguido de los 8 dígitos para números locales o '+56' para números que comienzan con '9' seguido de otros 8 dígitos, entrégame como respuesta sólo el número junto con el prefijo."
            numero_ajustado = generate_openai_response(prompt_ajuste)
            
            # Procesar el número ajustado
            if numero_ajustado:
                session_data['context'].append({'telefono': numero_ajustado})
                session_data['ha_dado_telefono'] = True
                response = "Gracias por proporcionar tu número de teléfono. ¿Te puedo ayudar en algo más?"
                # Enviar correo con datos recopilados, incluyendo el teléfono
                send_email(nombre_completo, comuna, correo, project, numero_ajustado, precio_texto_amigable, tipo_inmueble, dormitorios, banos)
                options = [
                    {'text': 'Sí, quiero seguir cotizando', 'value': 'cotizar'},
                    {'text': 'No, volver a inicio', 'value': 'inicio'}
                ]
                session_data['state'] = 'finalizacion'
            else:
                response = "No pude encontrar un número de teléfono válido en tu mensaje. ¿Podrías proporcionarlo nuevamente?"
                options = []  
        else:
            response = "No detecté un número de teléfono en tu mensaje. ¿Podrías proporcionarlo nuevamente?"
            options = []  

    elif session_data['state'] == 'finalizacion':
        if 'cotizar' in user_message:
            session_data['cotizacion_subsecuente'] = True
            session_data['context'] = [
                item for item in session_data['context']
                if 'rango_precio' not in item and 'tipo_inmueble' not in item and 'dormitorios' not in item and 'banos' not in item
            ]
            if session_data.get('busqueda_exitosa', False) and not session_data.get('ha_dado_telefono', False):
                # Solicitar el número de teléfono solo si la búsqueda anterior fue exitosa
                # y el teléfono no se ha proporcionado aún
                response = "Para continuar con la cotización y tener una comunicación más directa, ¿te gustaría proporcionar un número de teléfono?"
                options = [
                    {'text': 'Sí, deseo dar mi número de teléfono', 'value': 'dar_telefono'},
                    {'text': 'No, gracias', 'value': 'no_dar_telefono'}
                ]
                session_data['state'] = 'solicitando_telefono'
            else:
                # Continuar directamente con la cotización sin solicitar el teléfono
                session_data['state'] = 'solicitando_tipo_inmueble'
                response = "Genial, ¿qué tipo de inmueble estás buscando?"
                options = [
                    {'text': 'Departamento', 'value': 'departamento'},
                    {'text': 'Casa', 'value': 'casa'}
                ]
                session_data['busqueda_exitosa'] = False
        elif 'inicio' in user_message:
            # Reiniciar completamente la sesión si el usuario elige volver al inicio
            session_data.clear()
            session_data['state'] = 'inicio'
            options = [
                {'text': 'Necesito ayuda para cotizar', 'value': 'cotizar'},
                {'text': 'Deseo realizar un reclamo', 'value': 'reclamo'},
            ]
            response = "Hola, soy un Asistente Virtual, ¿En qué puedo ayudarte?"

    request.session['chat_data'] = session_data

    return JsonResponse({'respuesta': response, 'options': options})

def chat_view(request):
    return render(request, 'chat.html', {})

