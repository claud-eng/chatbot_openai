from django.conf import settings
import openai
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import requests
from xml.etree import ElementTree
import random
import os 
import unicodedata
import json 
from .rutas import *

def generate_openai_response(prompt):
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=1000,
            temperature=0.3
        )
        openai_response = response.choices[0].text.strip()
        print(f"OpenAI response: {openai_response}")  
        return openai_response
    except Exception as e:
        return f"Ocurrió un error al generar la respuesta: {str(e)}"

def cargar_configuracion(ruta_archivo):
    config = {}
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:  # Especifica la codificación UTF-8
            for linea in archivo:
                linea_limpia = linea.strip()
                if linea_limpia.startswith('#') or not linea_limpia:
                    continue  # Ignora comentarios o líneas vacías
                clave, valor = linea_limpia.split('=', 1)
                config[clave] = valor.strip()  # Elimina espacios en blanco adicionales alrededor del valor
    except Exception as e:
        print(f"Error al cargar la configuración: {e}")
    return config

def leer_configuracion(url_cliente):
    ruta_configuracion = seleccionar_ruta_configuracion(url_cliente)
    configuracion = {}
    with open(ruta_configuracion, 'r', encoding='utf-8') as file:
        for line in file:
            if "=" in line:
                key, value = line.strip().split('=', 1)
                configuracion[key] = value.strip()  
    return configuracion

def send_email(name, comuna_corregida, email, telefono, precio_texto_amigable, tipo_inmueble, dormitorios, banos, url_cliente):

    # Seleccionar el archivo de configuración basado en la URL del cliente
    ruta_config = seleccionar_ruta_configuracion(url_cliente)
    config = cargar_configuracion(ruta_config)
    proyecto_correo = config.get('PROYECTO_CORREO', 'Valor por defecto si no se encuentra PROYECTO_CORREO')

    sg = SendGridAPIClient(settings.EMAIL_HOST_PASSWORD)
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = config.get('EMAIL_RECIPIENT')
    subject = config.get('EMAIL_SUBJECT')

    # Determina el artículo adecuado para el tipo de inmueble
    articulo = 'un' if tipo_inmueble == 'departamento' else 'una'

    # Pluraliza correctamente "dormitorio" y "baño"
    dormitorio_texto = 'dormitorio' if dormitorios == '1' else 'dormitorios'
    bano_texto = 'baño' if banos == '1' else 'baños'
    precio_texto_amigable_modificado = precio_texto_amigable[:-2].lower() + precio_texto_amigable[-2:].upper()

    # Formato del mensaje de comentarios
    comentario = f'La persona cotizó {articulo} {tipo_inmueble} del proyecto {proyecto_correo}, con {dormitorios} {dormitorio_texto} y {banos} {bano_texto} a un precio {precio_texto_amigable_modificado}.'

    content = f'ORIGEN: ChatBot\nPROYECTO: {proyecto_correo}\nNOMBRE Y APELLIDO: {name}\nCOMUNA: {comuna_corregida}\nEMAIL: {email}\nTELEFONO: {telefono}\nPRECIO: {precio_texto_amigable}\nCOMENTARIO: {comentario}'

    message = Mail(from_email=from_email, to_emails=to_email, subject=subject, plain_text_content=content)
    try:
        sg.send(message)
    except Exception as e:
        print(f"Error al enviar correo: {e}")

def obtener_productos_activos(tipo_inmueble, rango_precio, url_cliente, dormitorios=None, banos=None, cantidad=0):

    # Seleccionar el archivo de configuración basado en la URL del cliente
    ruta_config = seleccionar_ruta_configuracion(url_cliente)
    config = cargar_configuracion(ruta_config)

    # Usar los valores de configuración en la solicitud
    url = "https://ws.iconcreta.com/Productos.asmx/ProductosActivos"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "orgNombre": config['ORG_NOMBRE'],
        "Dominio": config['DOMINIO'],
        "Usuario": config['USUARIO'],
        "Password": config['PASSWORD'],
        "Proyecto": config['PROYECTO'],  
    }
    response = requests.post(url, data=data, headers=headers)

    if response.status_code == 200:
        root = ElementTree.fromstring(response.content)
        productos = []
        for producto in root.findall('.//Producto'):
            try:
                nombre_producto = producto.find('Nombre').text.strip()
                tipo_inmueble_producto = ('departamento' if 'departamento' in nombre_producto.lower() else 'casa' if 'casa' in nombre_producto.lower() else 'otro')
                precio_producto = float(producto.find('PrecioTotalUF').text.strip())

                if tipo_inmueble_producto != tipo_inmueble:
                    continue

                if not cumple_con_rango_precio(precio_producto, rango_precio):
                    continue

                dormitorios_producto = int(float(producto.find('Dormitorios').text.strip()))
                banos_producto = int(producto.find('Banos').text.strip())

                if dormitorios and dormitorios_producto != int(dormitorios):
                    continue
                if banos and banos_producto != int(banos):
                    continue

                datos_producto = {
                    'Nombre': nombre_producto,
                    'NumeroProducto': producto.find('NumeroProducto').text.strip(),
                    'PrecioTotalUF': precio_producto,
                    'TipoInmueble': tipo_inmueble_producto,
                    'Numero': producto.find('Numero').text.strip(),  
                    'NombreProyecto': producto.find('NombreProyecto').text.strip() 
                    # Añadir aquí más campos si son necesarios
                }
                productos.append(datos_producto)
            except Exception as e:
                print(f"Error al procesar un producto: {e}")

        # Si se solicita una cantidad específica de productos y hay suficientes productos, selecciona al azar
        if cantidad > 0 and len(productos) >= cantidad:
            return random.sample(productos, cantidad)
        
        return productos
    else:
        print("Error en la solicitud:", response.status_code)
        return None
    
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