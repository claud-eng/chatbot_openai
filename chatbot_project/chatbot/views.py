from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from .rutas import *
from .functions import *
from .validators import *
from .opciones_proyectos import * 
from .preguntas_variadas import obtener_pregunta

# Esta variable se inicializará en la primera solicitud HTTP que se procese
comunas_chile = None

# Función correspondiente al flujo del chatbot para cotizar departamentos y casas
def flujo_dptos_casas(request):
    chat_session_id = request.GET.get('chatSessionId', '')
    
    if not chat_session_id:
        return JsonResponse({'error': 'No chat session ID provided'}, status=400)

    session_key = f"chat_data_{chat_session_id}"
    session_data = request.session.get(session_key, {'state': 'inicio', 'context': []})

    url_cliente = request.GET.get('url', '')

    # Corrige las comunas ingresadas por el usuario sin la letra ñ
    correcciones = {
        "nunoa": "Ñuñoa",
        "penalolen": "Peñalolen",
        "penaflor": "Peñaflor",
        "rio ibanez": "Rio Ibañez",
        "canete": "Cañete",
        "niquen": "Ñiquen",
        "hualane": "Hualañe",
        "donihue": "Doñihue",
        "vina de mar": "Viña del Mar",
        "vicuna": "Vicuña",
        "chanaral": "Chañaral",
        "camina": "Camiña",
    }
    
    global comunas_chile
    if comunas_chile is None:
        comunas_chile = cargar_comunas()

    user_message = request.GET.get('message', '').strip().lower()

    precio_a_texto = {
        'menos_1800': 'Menos de 1800 UF',
        'entre_1800_2499': 'Entre 1800 y 2499 UF',
        'entre_2500_3999': 'Entre 2500 y 3999 UF',
        'entre_4000_6999': 'Entre 4000 y 6999 UF',
        'mas_7000': 'Más de 7000 UF'
    }

    # Parsea el rango de precio a texto
    convertir_rango_precio_a_texto = next((precio_a_texto[item['rango_precio']] for item in session_data['context'] if 'rango_precio' in item), "Desconocido")

    if 'context' not in session_data:
        session_data['context'] = []
        
    response = ''
    options = []

    from_reclamo = session_data.get('from_reclamo', False)
    from_cotizacion = session_data.get('from_cotizacion', False)

    session_data['from_reclamo'] = False
    session_data['from_cotizacion'] = False

    if user_message == 'inicio':
        session_data.clear()
        session_data['state'] = 'inicio'
        session_data['context'] = []
        session_data['ha_dado_telefono'] = False
        
        ruta_archivo_configuracion = seleccionar_ruta_configuracion(url_cliente)
        configuracion = leer_archivo_configuracion(ruta_archivo=ruta_archivo_configuracion)
        respuesta_inicial = configuracion.get('RESPUESTA_INICIAL', 'Hola, soy un Asistente Virtual, ¿En qué puedo ayudarte?')
        
        if from_reclamo or from_cotizacion:
            response = 'Hola nuevamente, ¿En qué puedo ayudarte esta vez?'
        else:
            response = respuesta_inicial
        
        session_data['state'] = 'inicio'
        options = [
            {'text': 'Necesito ayuda para cotizar', 'value': 'cotizar'},
            {'text': 'Deseo realizar un reclamo', 'value': 'reclamo'}
        ]

    elif session_data['state'] == 'inicio':
        if 'cotizar' in user_message:
            options = obtener_opciones_proyectos(url_cliente)
            session_data['state'] = 'seleccionando_proyecto'
            response = '¿En cuál proyecto deseas cotizar?'
        elif 'reclamo' in user_message:
            ruta_archivo_configuracion = seleccionar_ruta_configuracion(url_cliente)
            configuracion = leer_archivo_configuracion(ruta_archivo=ruta_archivo_configuracion)
            session_data['state'] = 'inicio'
            session_data['from_reclamo'] = True
            response = configuracion.get('RESPUESTA_RECLAMO', 'No se encontró una respuesta para reclamos.')
            options = [
                {'text': 'Continuar', 'value': 'inicio'}
            ]

    elif session_data['state'] == 'seleccionando_proyecto':
        proyecto_seleccionado = user_message  # Actualiza el proyecto seleccionado con el mensaje del usuario
        print(f"Proyecto seleccionado: {proyecto_seleccionado}")  # Depuración

        ruta_archivo_configuracion = seleccionar_ruta_configuracion(url_cliente, proyecto_seleccionado)
        print(f"Ruta archivo configuración: {ruta_archivo_configuracion}")  # Depuración

        parametros_archivo_configuracion = leer_archivo_configuracion(ruta_archivo=ruta_archivo_configuracion)  # Pasamos ruta_archivo_configuracion como ruta_archivo

        print(f"Parámetros archivo configuración cargados: {parametros_archivo_configuracion}")  # Depuración

        session_data['context'].append({'config': parametros_archivo_configuracion, 'proyecto': proyecto_seleccionado})

        productos = obtener_productos_activos(url_cliente, proyecto_seleccionado)
        
        if productos:
            session_data['context'].append({'todos_los_productos': productos})

            nombre_completo = next((item['nombre_completo'] for item in session_data['context'] if 'nombre_completo' in item), None)
            comuna = next((item['comuna'] for item in session_data['context'] if 'comuna' in item), None)
            correo = next((item['correo'] for item in session_data['context'] if 'correo' in item), None)

            if not nombre_completo:
                session_data['state'] = 'solicitando_nombre'
                response = obtener_pregunta('nombre')
            elif not comuna:
                session_data['state'] = 'solicitando_comuna'
                primer_nombre = extraer_primer_nombre(nombre_completo) if nombre_completo else "cliente"
                response = obtener_pregunta('comuna', primer_nombre=primer_nombre)
            elif not correo:
                session_data['state'] = 'solicitando_correo'
                primer_nombre = extraer_primer_nombre(nombre_completo) if nombre_completo else "cliente"
                response = obtener_pregunta('correo', primer_nombre=primer_nombre)
            else:
                session_data['state'] = 'solicitando_tipo_inmueble'
                primer_nombre = extraer_primer_nombre(nombre_completo) if nombre_completo else "cliente"
                response = obtener_pregunta('tipo_inmueble', primer_nombre=primer_nombre)
                options = [
                    {'text': 'Departamento', 'value': 'departamento'},
                    {'text': 'Casa', 'value': 'casa'}
                ]
        else:
            response = 'Lo siento, no encontramos productos disponibles para el proyecto seleccionado. ¿Deseas intentar con otro proyecto?'
            session_data['state'] = 'inicio'
            options = [
                {'text': 'Sí, intentar con otro proyecto', 'value': 'cotizar'},
                {'text': 'No, gracias', 'value': 'inicio'}
            ]
            
    elif session_data['state'] == 'solicitando_nombre':
        if es_nombre_potencial(user_message):
            prompt_validar_nombre = f"El usuario dijo: '{user_message}'. Teniendo en cuenta que el usuario puede incluir agradecimientos o frases adicionales antes y/o después de dar su nombre (recordar que es opcional), el usuario en la frase que ha dicho, ¿En alguna parte menciona su nombre? responde si o no (tener en cuenta de que algunas personas de manera opcional puede que ingresen sus dos nombres y dos apellidos). Sólo es obligatorio ingresar el primer nombre"
            response_openai = llamar_openai(prompt_validar_nombre)
            if "sí" in response_openai.lower():
                prompt_extraer_nombre = f"Extrae el nombre completo (nombre y apellido) del siguiente texto: '{user_message}' (En caso de sólo haber un nombre sólo extrae eso, ya que el segundo nombre y los apellidos son opcionales)."
                nombre_completo = llamar_openai(prompt_extraer_nombre).strip()
                primer_nombre = extraer_primer_nombre(nombre_completo)
                session_data['context'].append({'nombre_completo': nombre_completo, 'primer_nombre': primer_nombre})
                session_data['state'] = 'solicitando_comuna'
                response = obtener_pregunta('comuna', primer_nombre=primer_nombre)
            else:
                response = 'Parece que no has ingresado tu nombre de manera válida. Por favor, intenta nuevamente ingresando al menos tu primer nombre.'
        else:
            response = 'Por favor, ingresa al menos tu primer nombre.'

    elif session_data['state'] == 'solicitando_comuna':
        # Normaliza y capitaliza la entrada del usuario
        comuna_usuario = capitalizar_comuna(quitar_acentos(user_message))

        # Verifica si el usuario ingresó una variante de Santiago Centro
        if "santiago centro" in comuna_usuario.lower():
            comuna_usuario = "Santiago"

        # Normaliza las claves del diccionario comunas_chile
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
            
            response = obtener_pregunta('tipo_inmueble', primer_nombre=primer_nombre) if primer_nombre else 'Genial, ¿qué tipo de inmueble estás buscando?'
            options = [
                {'text': 'Departamento', 'value': 'departamento'},
                {'text': 'Casa', 'value': 'casa'}
            ]
        else:
            response = 'No he podido identificar una comuna válida en tu respuesta. Por favor, intenta ingresando el nombre de una comuna en Chile como Las Condes, Providencia o La Florida, etc.'

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
        response = obtener_pregunta('rango_precios')

    elif session_data['state'] == 'solicitando_rango_precio':
        # Eliminar cualquier entrada previa de rango_precio para evitar conflictos
        session_data['context'] = [item for item in session_data['context'] if 'rango_precio' not in item]
        
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
            response = obtener_pregunta('dormitorios', primer_nombre=primer_nombre)
        else:
            # Solicitar el correo en una nueva cotización
            session_data['state'] = 'solicitando_correo'
            response = obtener_pregunta('correo', primer_nombre=primer_nombre)
            options = []

    elif session_data['state'] == 'solicitando_correo':
        primer_nombre = next((item['primer_nombre'] for item in session_data['context'] if 'primer_nombre' in item), "cliente")
        
        # Verifica si el mensaje del usuario contiene un correo electrónico
        prompt_verificar_correo = f"El usuario dijo: '{user_message}'. ¿Contiene esto una dirección de correo electrónico válida? Responde 'sí' o 'no'."
        respuesta_verificar_correo = llamar_openai(prompt_verificar_correo)
        
        if "sí" in respuesta_verificar_correo.lower():
            # Si hay un correo, intenta extraerlo
            prompt_extraer_correo = f"Extrae la dirección de correo electrónico del siguiente mensaje del usuario: '{user_message}'."
            correo_extraido = llamar_openai(prompt_extraer_correo).strip()
            
            # Valida el correo extraído
            if validar_correo(correo_extraido):
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
                response = obtener_pregunta('dormitorios', primer_nombre=primer_nombre)
            else:
                # Si OpenAI proporciona una cadena que no es un correo válido, solicita que se ingrese de nuevo
                response = obtener_pregunta('correo_invalido')
        else:
            # Si OpenAI indica que no hay un correo, solicita que se ingrese de nuevo
            response = obtener_pregunta('correo_no_detectado')

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
        response = obtener_pregunta('banos')

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
        tipo_inmueble = rango_precio = dormitorios = banos = proyecto = None

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
            elif 'proyecto' in item:
                proyecto = item['proyecto']

        # Verifica que todos los valores necesarios estén presentes
        if all(value is not None for value in [tipo_inmueble, rango_precio, url_cliente, dormitorios, banos, proyecto]):
            todos_los_productos = next((item['todos_los_productos'] for item in session_data['context'] if 'todos_los_productos' in item), [])
            try:
                if dormitorios == '5+':
                    productos = [producto for producto in todos_los_productos if (producto['TipoInmueble'].lower() == tipo_inmueble) and (int(producto['Dormitorios']) > 4) and (int(producto['Banos']) == int(banos))]
                elif banos == '4+':
                    productos = [producto for producto in todos_los_productos if (producto['TipoInmueble'].lower() == tipo_inmueble) and (int(producto['Dormitorios']) == int(dormitorios)) and (int(producto['Banos']) > 3)]
                else:
                    productos = [
                        producto for producto in todos_los_productos
                        if (producto['TipoInmueble'].lower() == tipo_inmueble) and
                        (int(producto['Dormitorios']) == int(dormitorios)) and
                        (int(producto['Banos']) == int(banos))
                    ]
            except ValueError as e:
                # Maneja el error de conversión de valores a enteros
                response = "Ha ocurrido un error al procesar tu solicitud. Por favor, verifica los datos ingresados y vuelve a intentarlo."
                session_data['state'] = 'solicitando_banos'
                options = [
                    {'text': '1 baño', 'value': '1'},
                    {'text': '2 baños', 'value': '2'},
                    {'text': '3 baños', 'value': '3'},
                    {'text': '4 o más baños', 'value': '4+'},
                ]
                return JsonResponse({'respuesta': response, 'options': options})

            # Decide qué hacer con los productos obtenidos
            producto_destacado = obtener_producto_mas_barato(productos) if productos else None

            if producto_destacado:
                # Marca la búsqueda como exitosa
                session_data['busqueda_exitosa'] = True

                if session_data.get('ha_dado_telefono') is not None and session_data.get('cotizacion_subsecuente', False):
                    # Suponiendo que 'cotizacion_subsecuente' se establece a True después de la primera cotización
                    nombre_completo = next((item['nombre_completo'] for item in session_data['context'] if 'nombre_completo' in item), "Desconocido")
                    comuna = next((item['comuna'] for item in session_data['context'] if 'comuna' in item), "Desconocida")

                    # Aplicar la corrección si el nombre de la comuna necesita ser ajustado
                    comuna_corregida = correcciones.get(comuna.lower(), comuna)
                    correo = next((item['correo'] for item in session_data['context'] if 'correo' in item), "Desconocido")
                    telefono = next((item['telefono'] for item in session_data['context'] if 'telefono' in item), "")
                    convertir_rango_precio_a_texto = next((precio_a_texto[item['rango_precio']] for item in session_data['context'] if 'rango_precio' in item), "Desconocido")
                    tipo_inmueble = next((item['tipo_inmueble'] for item in session_data['context'] if 'tipo_inmueble' in item), "Desconocido")
                    dormitorios = next((item['dormitorios'] for item in session_data['context'] if 'dormitorios' in item), "Desconocido")
                    banos = next((item['banos'] for item in session_data['context'] if 'banos' in item), "Desconocido")
                    proyecto = next((item['proyecto'] for item in session_data['context'] if 'proyecto' in item), "Desconocido")
                    
                    # Enviar correo a Iconcreta para procesar al cotizante y subirlo al CRM
                    enviar_correo_iconcreta(nombre_completo, comuna_corregida, correo, telefono, convertir_rango_precio_a_texto, tipo_inmueble, dormitorios, banos, url_cliente, proyecto)

                # Determina el tipo de inmueble para el mensaje, basado en la elección del usuario
                tipo_inmueble_texto = "Departamento" if tipo_inmueble.lower() == "departamento" else "Casa"
                url_plano_comercial = producto_destacado.get('URLPlanoComercial', 'no especificado')
                # Determina el prefijo adecuado ('el' o 'la') según el tipo de inmueble
                if tipo_inmueble.lower() == 'departamento':
                    tipo_inmueble_texto = 'el departamento'
                elif tipo_inmueble.lower() == 'casa':
                    tipo_inmueble_texto = 'la casa'
                else:
                    tipo_inmueble_texto = f"el {tipo_inmueble}"  # O cualquier formato por defecto que prefieras

                # Lista de mensajes de despedida
                mensajes_despedida = [
                    f"Te hemos enviado a tu correo electrónico más productos según tu cotización. Ha sido un placer ayudarte, {primer_nombre}.",
                    f"Revisa tu correo para más opciones que hemos seleccionado especialmente para ti. ¡Gracias por confiar en nosotros, {primer_nombre}!",
                    f"Hemos enviado detalles adicionales a tu email. ¡Esperamos haberte sido de ayuda, {primer_nombre}!",
                    f"Consulta tu correo para encontrar más propiedades que se ajusten a tus preferencias. ¡Fue un gusto asistirte, {primer_nombre}!",
                    f"En tu email encontrarás más información sobre las propiedades seleccionadas. ¡Agradecemos la oportunidad de servirte, {primer_nombre}!",
                ]

                # Selecciona un mensaje de despedida al azar
                mensaje_despedida_seleccionado = random.choice(mensajes_despedida)

                mensaje_respuesta = (
                    f"Tenemos {tipo_inmueble_texto} número {producto_destacado.get('Numero', 'no especificado')} "
                    f"del proyecto {producto_destacado.get('NombreProyecto', 'no especificado').lower()} "
                    f"a un precio total de {producto_destacado.get('PrecioTotalUF', 'no especificado')} UF. "
                    f"En esta imagen puedes ver el plano del inmueble:<br>(Haz click para verla en tamaño completo)<br>"
                    f"<a href='{url_plano_comercial}' target='_blank'><img src='{url_plano_comercial}' style='width: 100px; height: auto;' alt='Plano Comercial'></a><br>"
                    f"{mensaje_despedida_seleccionado}"
                )
                
                # Añade el mensaje construido a la variable de respuesta
                response = mensaje_respuesta

                productos_aleatorios = random.sample(productos, min(len(productos), 5))
                correo_destinatario = next((item['correo'] for item in session_data['context'] if 'correo' in item), None)

                if correo_destinatario and productos_aleatorios:
                    # Leer la configuración personalizada
                    configuracion = leer_archivo_configuracion(url_cliente, proyecto)
                    max_productos = int(configuracion.get('MAX_PRODUCTOS', 5))
                    saludo_correo = configuracion.get('SALUDO_CORREO', 'Saludo por defecto').format(primer_nombre=primer_nombre)
                    cierre_correo = configuracion.get('CIERRE_CORREO', 'Cierre por defecto')
                    template_name = configuracion.get('EMAIL_TEMPLATE', 'email_template.html')

                    # Generar la lista de productos con imágenes de planos
                    productos_html = ""
                    for producto in productos_aleatorios[:max_productos]:
                        numero_producto = producto.get('Numero', 'desconocido')
                        nombre_proyecto = producto.get('NombreProyecto', 'desconocido').lower()
                        tipo_texto = 'Departamento' if tipo_inmueble.lower() == 'departamento' else 'Casa' if tipo_inmueble.lower() == 'casa' else 'Inmueble'
                        
                        url_plano_comercial = producto.get('URLPlanoComercial', '')

                        productos_html += f"""
                        <div class='producto'>
                            {tipo_texto} número {numero_producto} de {dormitorios} dormitorios y {banos} baños del proyecto {nombre_proyecto} a un precio de {producto['PrecioTotalUF']} UF
                            <div class='plano'>
                                <p>Plano del inmueble:</p>
                                <a href='{url_plano_comercial}' target='_blank'>
                                    <img class='plano' src='{url_plano_comercial}' alt='Plano Comercial'>
                                </a>
                            </div>
                        </div>
                        """

                    # Leer el contenido del archivo HTML
                    template_path = os.path.join(settings.BASE_DIR, 'templates', template_name)
                    try:
                        with open(template_path, 'r', encoding='utf-8') as file:
                            contenido_correo = file.read()
                    except UnicodeDecodeError:
                        with open(template_path, 'r', encoding='latin-1') as file:
                            contenido_correo = file.read()

                    # Reemplazar los marcadores de posición en el HTML
                    contenido_correo = contenido_correo.replace('{{ saludo_correo }}', saludo_correo)
                    contenido_correo = contenido_correo.replace('{{ productos_html }}', productos_html)
                    contenido_correo = contenido_correo.replace('{{ cierre_correo }}', cierre_correo)

                    # Enviar el correo con el contenido generado al cotizante
                    enviar_correo_a_cotizante(correo_destinatario, contenido_correo, url_cliente, proyecto)

                # Verifica si ya se ha proporcionado el número de teléfono
                if not session_data.get('ha_dado_telefono', False):
                    print("ha_dado_telefono es False, se debería pedir el teléfono.")  # Depuración
                    response += obtener_pregunta('numero_telefono')
                    options = [
                        {'text': 'Sí, deseo dar mi número de teléfono', 'value': 'dar_telefono'},
                        {'text': 'No, gracias', 'value': 'no_dar_telefono'}
                    ]
                    session_data['state'] = 'solicitando_telefono'
                else:
                    print("ha_dado_telefono es True, no se pide el teléfono.")  # Depuración
                    # Continuar al estado de finalización si ya se ha dado el teléfono
                    response += obtener_pregunta('necesitas_ayuda')
                    options = [
                        {'text': 'Sí, quiero seguir cotizando', 'value': 'cotizar'},
                        {'text': 'No, volver a inicio', 'value': 'inicio'}
                    ]
                    session_data['state'] = 'finalizacion'
            else:
                if not producto_destacado:
                    # Verifica si ya se ha proporcionado el número de teléfono
                    if not session_data.get('ha_dado_telefono', False):
                        response = obtener_pregunta('no_inmuebles_ayuda_telefono')
                        options = [
                            {'text': 'Sí, deseo dar mi número de teléfono', 'value': 'dar_telefono'},
                            {'text': 'No, gracias', 'value': 'no_dar_telefono'}  
                        ]
                        session_data['state'] = 'solicitando_telefono'  # Cambio de estado para solicitar el teléfono
                    else:
                        response = obtener_pregunta('no_inmuebles_ayuda')
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
            response = obtener_pregunta('ingresar_telefono')
            session_data['state'] = 'ingresando_telefono'
            options = []
        elif user_message == 'no_dar_telefono':
            session_data['ha_dado_telefono'] = True
            response = obtener_pregunta('necesitas_ayuda')
            session_data['state'] = 'finalizacion'
            options = [
                {'text': 'Sí, quiero seguir cotizando', 'value': 'cotizar'},
                {'text': 'No, volver a inicio', 'value': 'inicio'}
            ]
            
            # Obtener datos del contexto para enviar por correo
            nombre_completo = next((item['nombre_completo'] for item in session_data['context'] if 'nombre_completo' in item), "Desconocido")
            comuna = next((item['comuna'] for item in session_data['context'] if 'comuna' in item), "Desconocida")

            # Aplicar la corrección si el nombre de la comuna necesita ser ajustado
            comuna_corregida = correcciones.get(comuna.lower(), comuna)
            correo = next((item['correo'] for item in session_data['context'] if 'correo' in item), "Desconocido")
            telefono = next((item['telefono'] for item in session_data['context'] if 'telefono' in item), "")
            convertir_rango_precio_a_texto = next((precio_a_texto[item['rango_precio']] for item in session_data['context'] if 'rango_precio' in item), "Desconocido")
            tipo_inmueble = next((item['tipo_inmueble'] for item in session_data['context'] if 'tipo_inmueble' in item), "Desconocido")
            dormitorios = next((item['dormitorios'] for item in session_data['context'] if 'dormitorios' in item), "Desconocido")
            banos = next((item['banos'] for item in session_data['context'] if 'banos' in item), "Desconocido")
            proyecto = next((item['proyecto'] for item in session_data['context'] if 'proyecto' in item), "Desconocido")

            # Enviar correo a Iconcreta para procesar al cotizante y subirlo al CRM
            enviar_correo_iconcreta(nombre_completo, comuna_corregida, correo, telefono, convertir_rango_precio_a_texto, tipo_inmueble, dormitorios, banos, url_cliente, proyecto)

    elif session_data['state'] == 'ingresando_telefono':
        # Extracción de datos previos necesarios para enviar por correo
        nombre_completo = next((item['nombre_completo'] for item in session_data['context'] if 'nombre_completo' in item), "Desconocido")
        comuna = next((item['comuna'] for item in session_data['context'] if 'comuna' in item), "Desconocida")
        correo = next((item['correo'] for item in session_data['context'] if 'correo' in item), "Desconocido")
        convertir_rango_precio_a_texto = next((precio_a_texto[item['rango_precio']] for item in session_data['context'] if 'rango_precio' in item), "Desconocido")
        tipo_inmueble = next((item['tipo_inmueble'] for item in session_data['context'] if 'tipo_inmueble' in item), "Desconocido")
        dormitorios = next((item['dormitorios'] for item in session_data['context'] if 'dormitorios' in item), "Desconocido")
        banos = next((item['banos'] for item in session_data['context'] if 'banos' in item), "Desconocido")
        proyecto = next((item['proyecto'] for item in session_data['context'] if 'proyecto' in item), "Desconocido")

        comuna_corregida = correcciones.get(comuna.lower(), comuna)

        # Eliminar espacios en blanco y el carácter '+' para la verificación
        mensaje_limpio = user_message.replace(' ', '').replace('+', '')
        if mensaje_limpio.isdigit():
            # Procesamiento para un número que parece ser chileno
            numero = mensaje_limpio
            if len(numero) == 8:  # Número local sin código de área, asumir que es un móvil
                telefono = '+569' + numero
            elif len(numero) == 9:  # Número con 9 dígitos
                if numero.startswith('9'):  # Móvil sin código de país
                    telefono = '+56' + numero
                elif numero.startswith('2'):  # Fijo potencial, pero con un dígito adicional
                    telefono = '+562' + numero[1:]  # Se asume el número corregido, quitando el dígito extra
                else:
                    telefono = None
            elif len(numero) in [11, 12] and (numero.startswith('569') or numero.startswith('562')):  # Número completo con o sin '+'
                telefono = '+' + numero
            else:
                telefono = None

            if telefono:
                session_data['context'].append({'telefono': telefono})
                session_data['ha_dado_telefono'] = True
                response = f"Gracias por proporcionar tu número de teléfono. ¿Te puedo ayudar en algo más?"
                # Enviar correo con datos recopilados, incluyendo el teléfono
                enviar_correo_iconcreta(nombre_completo, comuna_corregida, correo, telefono, convertir_rango_precio_a_texto, tipo_inmueble, dormitorios, banos, url_cliente, proyecto)
                options = [{'text': 'Sí, quiero seguir cotizando', 'value': 'cotizar'},
                        {'text': 'No, volver al inicio', 'value': 'inicio'}]
                session_data['state'] = 'finalizacion'
            else:
                response = "No pude reconocer el número de teléfono en el formato esperado. ¿Puedes intentar de nuevo?"
                options = []
        else:
            prompt_validar_telefono = f"¿La frase '{user_message}' contiene un número de teléfono con al menos 8 dígitos numéricos? Solo responde sí o no."
            respuesta_verificacion = llamar_openai(prompt_validar_telefono)

            if respuesta_verificacion.lower() == "sí":
                prompt_ajustar_telefono = f"Extrae y ajusta al formato chileno el número de teléfono presente en la frase '{user_message}'. El formato chileno es '+569' seguido de los 8 dígitos locales para teléfonos móviles o '+562' seguido de los 8 dígitos locales para teléfonos fijos, entrégame como respuesta solo el número junto con el prefijo."
                telefono = llamar_openai(prompt_ajustar_telefono)
                
                if telefono:
                    session_data['context'].append({'telefono': telefono})
                    session_data['ha_dado_telefono'] = True
                    response = "Gracias por proporcionar tu número de teléfono. ¿Te puedo ayudar en algo más?"
                    enviar_correo_iconcreta(nombre_completo, comuna_corregida, correo, telefono, convertir_rango_precio_a_texto, tipo_inmueble, dormitorios, banos, url_cliente)
                    options = [{'text': 'Sí, quiero seguir cotizando', 'value': 'cotizar'},
                            {'text': 'No, volver al inicio', 'value': 'inicio'}]
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
            # Mantener los datos previos excepto los específicos de la cotización anterior
            datos_a_mantener = ['nombre_completo', 'comuna', 'correo']
            session_data['context'] = [
                item for item in session_data['context']
                if any(clave in item for clave in datos_a_mantener)
            ]
            session_data['state'] = 'seleccionando_proyecto'
            response = "Genial, ¿en cuál proyecto deseas cotizar?"
            # Obtener las opciones de proyecto basadas en la URL del cliente
            options = obtener_opciones_proyectos(url_cliente)
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

    request.session[session_key] = session_data

    return JsonResponse({'respuesta': response, 'options': options, 'state': session_data['state']})

def chatbot_index(request):
    return render(request, 'chatbot_index.html', {})