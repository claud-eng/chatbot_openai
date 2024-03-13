def seleccionar_ruta_configuracion(url_cliente):
    if "probar.iconcreta.com/test.html" in url_cliente:
        return r"D:\\App_Data\\cfl.cfg"
    elif "probar.iconcreta.com/test2.html" in url_cliente:
        return r"D:\\App_Data\\demoinm.cfg"
    elif "localhost" in url_cliente:
        return r"D:\\App_Data\\demoinm-PMC.cfg"
    elif "desarrollo.iconcreta.com" in url_cliente:
        return r"D:\\App_Data\\demoinm.cfg"
    else:
        return r"D:\\App_Data\\demoinm.cfg"
    
