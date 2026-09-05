from datetime import datetime


def calcular_estado(usuario):
    """Devuelve el texto de estado de actividad, o None si el usuario
    desactivó mostrar su estado en configuración."""
    if usuario.preferencia and usuario.preferencia.mostrar_estado is False:
        return None

    if usuario.en_linea:
        return "Activo"

    if not usuario.ultima_conexion:
        return "Inactivo"

    segundos = (datetime.utcnow() - usuario.ultima_conexion).total_seconds()

    if segundos < 5 * 60:
        return "Inactivo"
    if segundos < 60 * 60:
        minutos = int(segundos // 60)
        return f"Activo hace {minutos} min"
    if segundos < 24 * 60 * 60:
        horas = int(segundos // 3600)
        return f"Activo hace {horas} h"
    dias = int(segundos // 86400)
    return f"Activo hace {dias} d"
