import re
from django.core.mail import send_mail
from django.conf import settings

def is_potential_name(name):
    # Comprobar si hay al menos una palabra en la entrada
    return len(re.findall(r'\b\w+\b', name)) >= 1

def validate_email(email):
    # Una expresión regular simple para validar correos electrónicos
    return re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email)

# Nueva función para extraer el primer nombre del nombre completo
def extraer_primer_nombre(nombre_completo):
    primer_nombre = nombre_completo.split()[0]  # Divide el nombre completo por espacios y toma el primer elemento
    return primer_nombre

def enviar_correo_con_seleccion(correo_destinatario, contenido_correo):
    # Enviar el correo
    send_mail(
        "Cotización de inmueble",  # Asunto del correo ajustado a "Cotización"
        '',  # El cuerpo del correo en texto plano se deja vacío, ya que se está usando html_message para el contenido HTML
        settings.DEFAULT_FROM_EMAIL,  # El correo del remitente configurado en settings.py
        [correo_destinatario],  # Lista de destinatarios; en este caso, solo hay uno
        fail_silently=False,
        html_message=contenido_correo  # Contenido HTML del correo, directamente de OpenAI
    )
