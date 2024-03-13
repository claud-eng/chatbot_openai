import re
from django.core.mail import send_mail
from django.conf import settings
from .functions import *

def is_potential_name(name):
    # Comprobar si hay al menos una palabra en la entrada
    return len(re.findall(r'\b\w+\b', name)) >= 1

def validate_email(email):
    # Una expresión regular simple para validar correos electrónicos
    return re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email)

# Función para extraer el primer nombre del nombre completo
def extraer_primer_nombre(nombre_completo):
    primer_nombre = nombre_completo.split()[0]  # Divide el nombre completo por espacios y toma el primer elemento
    return primer_nombre

def enviar_correo_con_seleccion(correo_destinatario, contenido_correo, url_cliente):
    ruta_config = seleccionar_ruta_configuracion(url_cliente)
    config = cargar_configuracion(ruta_config)
    subject_asunto = config.get('EMAIL_SUBJECT_COTIZANTE')

    send_mail(
        subject_asunto,
        '',
        settings.DEFAULT_FROM_EMAIL,
        [correo_destinatario],
        fail_silently=False,
        html_message=contenido_correo
    )