import re
from django.core.mail import send_mail
from django.conf import settings
from .functions import *

# Función para comprobar si se ha ingresado al menos una palabra
def es_nombre_potencial(name):
    # Comprobar si hay al menos una palabra en la entrada
    return len(re.findall(r'\b\w+\b', name)) >= 1

# Función para validar un correo electrónico
def validar_correo(email):
    # Una expresión regular simple para validar correos electrónicos
    return re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email)

# Función para extraer el primer nombre del nombre completo
def extraer_primer_nombre(nombre_completo):
    primer_nombre = nombre_completo.split()[0]  # Divide el nombre completo por espacios y toma el primer elemento
    return primer_nombre

# Función para enviar correo con los productos al cotizante al llegar al final del flujo
def enviar_correo_a_cotizante(correo_destinatario, contenido_correo, url_cliente, proyecto):
    ruta_archivo_configuracion = seleccionar_ruta_configuracion(url_cliente, proyecto)
    parametros_archivo_configuracion = leer_archivo_configuracion(ruta_archivo=ruta_archivo_configuracion)  # Pasamos ruta_archivo_configuracion como ruta_archivo

    subject_asunto = parametros_archivo_configuracion.get('EMAIL_SUBJECT_COTIZANTE')
    from_email = parametros_archivo_configuracion.get('DEFAULT_FROM_EMAIL')

    send_mail(
        subject_asunto,
        '',  # El cuerpo del mensaje se envía vacío porque se usará `html_message`
        from_email,
        [correo_destinatario],
        fail_silently=False,
        html_message=contenido_correo  # El contenido del correo como HTML
    )