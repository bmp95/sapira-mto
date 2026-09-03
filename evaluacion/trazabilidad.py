"""La unica comprobacion que NO necesita gold: que ningun valor sea inventado.

Un gold dice si el valor es el correcto. Esto dice algo mas debil y mas barato:
que el valor se puede rastrear hasta el texto de origen o hasta una regla con
nombre. Por eso se puede aplicar a TODAS las lineas de salida, incluidas las
que ningun anotador ha mirado -- y es justo lo que hace falta, porque los
evaluadores contra gold solo puntuan el elemento principal de cada fila.

De las 279 lineas que el bloque A del blind set produce a partir de 200 filas,
el gold solo cubre 200: las tuercas y arandelas de los sets no tienen verdad
anotada. Sin esto, 79 lineas salian del sistema sin que nadie las mirase.
"""
from __future__ import annotations

from motor.modelos import ATRIBUTOS, Procedencia
from motor.saneado import sanear

# Procedencias que no tienen literal en el texto que verificar: su evidencia es
# la regla (DERIVADO) o el registro historico (HEREDADO), no un trozo de texto.
_SIN_LITERAL = (Procedencia.DERIVADO, Procedencia.HEREDADO)


def valor_rastreable(celda, texto_origen: str, material_col: str = "") -> bool:
    """Se compara el LITERAL contra el texto SANEADO, que es el que vio el
    pipeline.

    Las dos decisiones importan y las dos se aprendieron equivocandose:

    - Contra el texto SANEADO, no el crudo. Comparar con el crudo marca como
      invencion justo lo que el saneado arregla: la prima doble de 7/8" y los
      espacios multiples de "DIN   933".
    - Se compara el LITERAL, no el VALOR. El catalogo normaliza a proposito
      (ZINCADO -> CINCADO, DIN 933 -> ISO 4017); exigir que el valor canonico
      aparezca tal cual marcaria como inventada cada normalizacion correcta.
    - El MTO tiene DOS fuentes de texto, no una: la descripcion y la columna
      MATERIAL. La calidad y el material del elemento principal pueden venir
      legitimamente de la segunda (`_calidad_de_columna_material`). Mirar solo
      la descripcion marcaba como inventado un 8.8 que estaba escrito en la
      celda de al lado.
    """
    if celda.valor is None:
        return True
    if celda.procedencia in _SIN_LITERAL:
        return bool(celda.regla)
    if not celda.literal:
        return False
    fuentes = sanear(texto_origen).upper() + chr(10) + sanear(material_col).upper()
    return celda.literal.upper() in fuentes


def auditar_invenciones(lineas, columnas_material: dict[int, str] | None = None) -> list[dict]:
    """Cada celda de cada linea contra sus dos fuentes de texto.

    `columnas_material` mapea fila de origen a su columna MATERIAL. Sin el, un
    valor legitimo tomado de esa columna se marca como invencion -- que es
    exactamente lo que paso la primera vez que se corrio esto.
    """
    columnas_material = columnas_material or {}
    hallazgos = []
    for linea in lineas:
        material_col = columnas_material.get(linea.fila_origen, "")
        for atributo in ATRIBUTOS:
            celda = getattr(linea, atributo)
            if not valor_rastreable(celda, linea.texto_origen, material_col):
                hallazgos.append({
                    "linea": linea.id,
                    "fila": linea.fila_origen,
                    "atributo": atributo,
                    "valor": celda.valor,
                    "literal": celda.literal,
                    "procedencia": celda.procedencia.value,
                    "texto": linea.texto_origen,
                    "material_col": material_col,
                })
    return hallazgos


def cobertura_de_la_evaluacion(lineas, filas_con_gold: set[int]) -> dict:
    """Cuantas lineas produce el sistema y cuantas mira de verdad un gold.

    El numero que importa es `sin_gold`: son lineas que salen a la cola de
    compra sin que ningun anotador las haya comparado con nada. Publicar una
    tasa de escape sin decir esto es publicar media verdad.
    """
    del_bloque = [l for l in lineas if l.fila_origen in filas_con_gold]
    filas_vistas = {l.fila_origen for l in del_bloque}
    return {
        "lineas_producidas": len(del_bloque),
        "filas": len(filas_vistas),
        "evaluadas_contra_gold": len(filas_vistas),   # una por fila: la principal
        "sin_gold": len(del_bloque) - len(filas_vistas),
    }
