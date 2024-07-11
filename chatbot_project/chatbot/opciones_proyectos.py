# Función para establecer las opciones de proyectos que ofrecerá el chatbot para cotizar en cada página en la que esté insertada
def obtener_opciones_proyectos(url_cliente):
    opciones_proyectos = {
        "localhost": [
            {'text': 'Parque Machalí', 'value': 'pmc'},
            {'text': 'Altos de Asís', 'value': 'ada'},
            {'text': 'Parque Estébanez', 'value': 'pae'},
            # Agregar más proyectos según sea necesario
        ],
        "127.0.0.1": [
            {'text': 'Parque Machalí', 'value': 'pmc'},
            # Agregar más proyectos según sea necesario
        ],
        "desarrollo.iconcreta.com": [
            {'text': 'Proyecto CZA', 'value': 'cza'},
            {'text': 'Proyecto CHI', 'value': 'chi'},
            # Agregar más proyectos según sea necesario
        ],
        # Agregar más URLs y sus opciones de proyecto según sea necesario
    }

    for key in opciones_proyectos:
        if key in url_cliente:
            return opciones_proyectos[key]
    return []