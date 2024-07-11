from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from xml.etree import ElementTree
from .rutas import *
import requests
import openai
import random
import json 
import os 
import unicodedata

# Función para establecer la conexión con openAI
def llamar_openai(prompt):
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=1000,
            temperature=0.3
        )
        respuesta_openai = response.choices[0].text.strip()
        print(f"OpenAI response: {respuesta_openai}")  
        return respuesta_openai
    except Exception as e:
        return f"Ocurrió un error al generar la respuesta: {str(e)}"

# Función para leer los archivos de configuración por proyecto en un formato específico
def leer_archivo_configuracion(url_cliente=None, proyecto=None, ruta_archivo=None):
    if ruta_archivo is None:
        if url_cliente is None or proyecto is None:
            raise ValueError("Debe proporcionar 'ruta_archivo' o ambos 'url_cliente' y 'proyecto'")
        ruta_archivo = seleccionar_ruta_configuracion(url_cliente, proyecto)
    
    configuracion = {}
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            for linea in archivo:
                linea_limpia = linea.strip()
                if linea_limpia.startswith('#') or not linea_limpia:
                    continue  # Ignora comentarios o líneas vacías
                if "=" in linea_limpia:
                    clave, valor = linea_limpia.split('=', 1)
                    configuracion[clave] = valor.strip()  # Elimina espacios en blanco adicionales alrededor del valor
    except Exception as e:
        print(f"Error al cargar la configuración: {e}")
    
    return configuracion

# Función para enviar correo electrónico a Iconcreta tras realizar una cotización y que pueda ser procesada para ser subida al CRM
def enviar_correo_iconcreta(name, comuna_corregida, email, telefono, convertir_rango_precio_a_texto, tipo_inmueble, dormitorios, banos, url_cliente, proyecto):
    # Seleccionar el archivo de configuración basado en la URL del cliente y el proyecto
    ruta_archivo_configuracion = seleccionar_ruta_configuracion(url_cliente, proyecto)
    parametros_archivo_configuracion = leer_archivo_configuracion(ruta_archivo=ruta_archivo_configuracion)  # Pasar ruta_archivo_configuracion como ruta_archivo
    proyecto_correo = parametros_archivo_configuracion.get('PROYECTO_CORREO', 'Valor por defecto si no se encuentra PROYECTO_CORREO')

    sg = SendGridAPIClient(settings.EMAIL_HOST_PASSWORD)
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = parametros_archivo_configuracion.get('EMAIL_RECIPIENT')
    subject = parametros_archivo_configuracion.get('EMAIL_SUBJECT')

    # Determina el artículo adecuado para el tipo de inmueble
    articulo = 'un' if tipo_inmueble == 'departamento' else 'una'

    # Pluraliza correctamente "dormitorio" y "baño"
    pluralizar_dormitorio = 'dormitorio' if dormitorios == '1' else 'dormitorios'
    pluralizar_bano = 'baño' if banos == '1' else 'baños'
    # Modifica el texto del precio para que los últimos dos caracteres estén en mayúsculas
    modificar_texto_precio = convertir_rango_precio_a_texto[:-2].lower() + convertir_rango_precio_a_texto[-2:].upper()

    # Formato del mensaje de comentarios
    comentario = f'La persona cotizó {articulo} {tipo_inmueble} del proyecto {proyecto_correo}, con {dormitorios} {pluralizar_dormitorio} y {banos} {pluralizar_bano} a un precio {modificar_texto_precio}.'

    content = f'ORIGEN: ChatBot\nPROYECTO: {proyecto_correo}\nNOMBRE Y APELLIDO: {name}\nCOMUNA: {comuna_corregida}\nEMAIL: {email}\nTELEFONO: {telefono}\nPRECIO: {convertir_rango_precio_a_texto}\nCOMENTARIO: {comentario}'

    message = Mail(from_email=from_email, to_emails=to_email, subject=subject, plain_text_content=content)
    try:
        sg.send(message)
    except Exception as e:
        print(f"Error al enviar correo: {e}")

# Función para obtener los productos activos en Iconcreta provenientes de un webservice
def obtener_productos_activos(url_cliente, proyecto):
    ruta_archivo_configuracion = seleccionar_ruta_configuracion(url_cliente, proyecto)
    parametros_archivo_configuracion = leer_archivo_configuracion(ruta_archivo=ruta_archivo_configuracion)  # Pasamos ruta_archivo_configuracion como ruta_archivo

    print(f"Parámetros archivo configuración: {parametros_archivo_configuracion}")  # Depuración

    url = "https://ws.iconcreta.com/Productos.asmx/ProductosActivos"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "orgNombre": parametros_archivo_configuracion['ORG_NOMBRE'],
        "Dominio": parametros_archivo_configuracion['DOMINIO'],
        "Usuario": parametros_archivo_configuracion['USUARIO'],
        "Password": parametros_archivo_configuracion['PASSWORD'],
        "Proyecto": parametros_archivo_configuracion['PROYECTO'],  
    }
    response = requests.post(url, data=data, headers=headers)

    if response.status_code == 200:
        root = ElementTree.fromstring(response.content)
        productos = []
        for producto in root.findall('.//Producto'):
            try:
                nombre_producto = producto.find('Nombre').text.strip()
                precio_producto = float(producto.find('PrecioTotalUF').text.strip())

                dormitorios_producto = int(float(producto.find('Dormitorios').text.strip()))
                banos_producto = int(float(producto.find('Banos').text.strip()))
                url_plano_comercial = producto.find('URLPlanoComercial').text.strip()
                datos_producto = {
                    'Nombre': nombre_producto,
                    'NumeroProducto': producto.find('NumeroProducto').text.strip(),
                    'PrecioTotalUF': precio_producto,
                    'TipoInmueble': 'departamento' if 'departamento' in nombre_producto.lower() else 'casa' if 'casa' in nombre_producto.lower() else 'otro',
                    'Numero': producto.find('Numero').text.strip(),
                    'NombreProyecto': producto.find('NombreProyecto').text.strip(),
                    'Dormitorios': dormitorios_producto,
                    'Banos': banos_producto,
                    'URLPlanoComercial': url_plano_comercial
                }
                productos.append(datos_producto)
            except Exception as e:
                print(f"Error al procesar un producto: {e}")

        return productos
    else:
        print("Error en la solicitud:", response.status_code)
        return None

# Función para evaluar el rango de los precios
def cumple_con_rango_precio(precio, rango_precio):
    """
    Evalúa si un precio se encuentra dentro de un rango de precio determinado.

    :param precio: Precio del producto a evaluar.
    :param rango_precio: Rango de precio seleccionado por el usuario.
    :return: True si el precio está dentro del rango, False en caso contrario.
    """
    if rango_precio == 'menos_1800':
        return precio < 1800
    elif rango_precio == 'entre_1800_2499':
        return 1800 <= precio <= 2499
    elif rango_precio == 'entre_2500_3999':
        return 2500 <= precio <= 3999
    elif rango_precio == 'entre_4000_6999':
        return 4000 <= precio <= 6999
    elif rango_precio == 'mas_7000':
        return precio > 7000
    else:
        # Si no se encuentra el rango, se considera que no cumple con el rango de precios.
        return False

# Función para obtener el producto más barato
def obtener_producto_mas_barato(productos):
    if not productos:
        return None
    producto_mas_barato = min(productos, key=lambda x: x['PrecioTotalUF'])
    return producto_mas_barato

# Función para remover acentos de una cadena de texto
def quitar_acentos(texto):
    texto_sin_acentos = ''.join((c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn'))
    return texto_sin_acentos

# Función para capitalizar cada palabra en el nombre de la comuna
def capitalizar_comuna(comuna):
    return ' '.join(palabra.capitalize() for palabra in comuna.split())

# Función para cargar las comunas de Chile provenientes del diccionario
def cargar_comunas():
    # Ruta al archivo comunas.jsonl
    jsonl_path = os.path.join(settings.BASE_DIR, 'chatbot/comunas.jsonl')
    comunas = {}
    with open(jsonl_path, 'r', encoding='utf-8') as file:  
        for line in file:
            comuna = json.loads(line)
            comunas[comuna["Comuna Oficial"]] = True
    return comunas