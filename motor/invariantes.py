"""Las comprobaciones que impiden inventar y, sobre todo, la que impide OMITIR.

La verificacion de literales impide que el modelo se invente un valor. No impide que
se deje un elemento fuera: si el segmentador se salta '2 WASHER 7/8", ASTM F436',
ninguna comprobacion por elemento lo detecta porque ese elemento no existe.
Solo la cobertura del texto lo caza.
"""
import re

from motor.modelos import Segmentacion

UMBRAL_COBERTURA = 0.75

_SUSTANTIVOS = {
    "TORNILLO": r"TORNILLOS?|BOLTS?|SCREWS?",
    "TUERCA": r"TUERCAS?|NUTS?",
    "ARANDELA": r"ARANDELAS?|WASHERS?",
    "ESPARRAGO": r"ESPARRAGOS?|STUDS?",
    "VARILLA": r"VARILLAS?\s+ROSCADAS?|THREADED\s+RODS?",
}
# STUD BOLT es un solo elemento, no un esparrago mas un tornillo.
_COMPUESTOS = [(r"STUD\s+BOLTS?", "ESPARRAGO")]


def verificar_literal(literal: str, texto: str, span: tuple[int, int]) -> bool:
    if literal is None or span is None:
        return False
    ini, fin = span
    if not (0 <= ini < fin <= len(texto)):
        return False
    return texto[ini:fin].upper() == literal.upper()


def cobertura(texto: str, seg: Segmentacion) -> float:
    """Proporcion de caracteres no-conector cubiertos por algun tramo."""
    marcas = bytearray(len(texto))
    for e in seg.elementos:
        for i in range(max(0, e.span[0]), min(len(texto), e.span[1])):
            marcas[i] = 1
    for ini, fin in seg.ambito_fila:
        for i in range(max(0, ini), min(len(texto), fin)):
            marcas[i] = 1
    # Marcar conectores para excluirlos del denominador
    es_conector = bytearray(len(texto))
    for ini, fin in seg.conectores:
        for i in range(max(0, ini), min(len(texto), fin)):
            es_conector[i] = 1
    # Significativos son los alfanumericos que NO estan en conectores
    significativos = [i for i, c in enumerate(texto) if c.isalnum() and not es_conector[i]]
    if not significativos:
        return 1.0
    return sum(marcas[i] for i in significativos) / len(significativos)


def hay_solape(seg: Segmentacion) -> bool:
    tramos = sorted(e.span for e in seg.elementos)
    return any(tramos[i][1] > tramos[i + 1][0] for i in range(len(tramos) - 1))


# El ambito de fila solo puede contener calidad y acabado (describen la fila
# entera); una medida o una longitud describen una pieza concreta. M seguida
# de digitos (M20), fraccion en pulgadas (3/4), numero+comillas (7/8", 200"),
# numero+MM/LG/LONG (200MM, 40 LG).
_RE_DIMENSION_AMBITO = re.compile(r'\bM\d+\b|\b\d+/\d+\b|\d+"|\b\d+\s*(?:MM|LG|LONG)\b',
                                  re.IGNORECASE)


def ambito_sin_dimensiones(texto: str, seg: Segmentacion) -> bool:
    """False si algun tramo de `ambito_fila` contiene una medida o una
    longitud reconocibles.

    Caza un hueco real de la red que ni la cobertura ni el recuento de
    sustantivos ven: cuando el texto nunca nombra una pieza (ningun "stud",
    "bolt", "esparrago"...  solo sus dimensiones, p.ej. '3/4" IN DIA X
    200MM LONG'), el segmentador mete esa descripcion en el ambito de fila
    en vez de crear un elemento. El texto queda asignado igual (cobertura
    1.0) y el recuento de sustantivos cuadra (de verdad solo hay uno), asi
    que ninguna otra invariante lo detecta -- no es una omision, es una
    mala clasificacion."""
    for ini, fin in seg.ambito_fila:
        if _RE_DIMENSION_AMBITO.search(texto[ini:fin]):
            return False
    return True


def contar_sustantivos(texto: str) -> int:
    """Escaner determinista, independiente del modelo. Solo cuenta; no parsea."""
    t = texto.upper()
    total, consumido = 0, t
    for patron, _ in _COMPUESTOS:
        hallados = re.findall(patron, consumido)
        total += len(hallados)
        consumido = re.sub(patron, " ", consumido)
    for patron in _SUSTANTIVOS.values():
        total += len(re.findall(patron, consumido))
    return total
