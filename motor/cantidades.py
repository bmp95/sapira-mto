"""Multiplicadores de cantidad del set.

La cantidad en la columna es la del elemento principal.
El multiplicador va encima de cada sustantivo de tipo.
Por ejemplo: "2 WASHER" significa 2 arandelas; si la cantidad es 40,
hay 2*40 = 80 arandelas.
"""
import re


_PATRONES_SUSTANTIVOS = (
    # Compuestos primero (más específicos)
    r"STUD\s+BOLTS?",
    # Sustantivos individuales
    r"TORNILLOS?",
    r"BOLTS?",
    r"SCREWS?",
    r"TUERCAS?",
    r"NUTS?",
    r"ARANDELAS?",
    r"WASHERS?",
    r"ESPARRAGOS?",
    r"STUDS?",
    r"VARILLAS?\s+ROSCADAS?",
    r"THREADED\s+RODS?",
)

# Patrones que NO pueden ser multiplicadores
# Las normas pueden tener una o dos palabras clave (DIN EN, MSS SP)
# y el identificador puede ir separado por espacio, guion o pegado,
# contiendo letras, dígitos y puntos
_PATRON_NORMA = r"(?:DIN\s+EN|MSS\s+SP|DIN|ISO|ASME|ASTM|EN)[\s\-]*\S+"
_PATRON_MEDIDA_METRICA = r"M\d+(?:X\d+)?"
_PATRON_MEDIDA_PULGADA = r"\d+/\d+|\d+\""


def _limpiar_texto_anterior(texto: str) -> str:
    """Elimina tokens que no pueden ser multiplicadores.

    Elimina:
    - Normas (DIN, ISO, ASTM, ASME, EN, MSS) con su número
    - Medidas métricas (M20, M20x90, etc.)
    - Medidas en pulgadas (7/8, 3/4, 7", etc.)
    """
    # Eliminar normas
    texto = re.sub(_PATRON_NORMA, " ", texto, flags=re.IGNORECASE)
    # Eliminar medidas métricas
    texto = re.sub(_PATRON_MEDIDA_METRICA, " ", texto, flags=re.IGNORECASE)
    # Eliminar medidas en pulgadas
    texto = re.sub(_PATRON_MEDIDA_PULGADA, " ", texto, flags=re.IGNORECASE)
    return texto


def multiplicador(tramo: str) -> int:
    """Extrae el multiplicador del tramo.

    El multiplicador es el número que aparece antes del primer sustantivo
    de tipo (tornillo, tuerca, arandela, etc.), excluyendo normas y medidas.
    Si no hay número, devuelve 1.

    Args:
        tramo: Texto del tramo (p.ej., "W/2 HEX. NUT 7/8\", ASTM A194, GR 2H")

    Returns:
        El multiplicador encontrado, o 1 si no hay número.
    """
    tramo_upper = tramo.upper().strip()

    # Buscar el primer sustantivo de tipo
    primer_sustantivo_match = None
    posicion_sustantivo = len(tramo_upper)

    for patron in _PATRONES_SUSTANTIVOS:
        m = re.search(patron, tramo_upper, re.IGNORECASE)
        if m and m.start() < posicion_sustantivo:
            primer_sustantivo_match = m
            posicion_sustantivo = m.start()

    # Si no hay sustantivo, no hay multiplicador
    if primer_sustantivo_match is None:
        return 1

    # Extraer el texto antes del primer sustantivo
    texto_anterior = tramo_upper[:primer_sustantivo_match.start()]

    # Limpiar el texto anterior de normas y medidas
    texto_limpio = _limpiar_texto_anterior(texto_anterior)

    # Buscar el último número en el texto limpio
    numeros = re.findall(r"\d+", texto_limpio)
    if numeros:
        return int(numeros[-1])
    else:
        return 1
