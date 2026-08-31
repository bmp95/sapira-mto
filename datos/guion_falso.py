"""ANDAMIO DE PRUEBAS, NO EL GOLD SET.

Este fichero congela, a mano, la segmentacion que un segmentador real
(A1, tres pasadas) deberia devolver para cada una de las 15 filas del
MTO de muestra. No decide que es correcto -- eso lo hara el gold set
anotado a mano de la Tarea 11 -- solo permite ejercitar
`motor.pipeline.procesar_mto` de punta a punta sin red, contra
`motor.puerto_llm.PuertoFalso`.

Los tramos (spans) de cada elemento se calcularon con un script auxiliar
que localiza cada substring con `str.find` sobre la descripcion ya
saneada (`motor.lectura_mto.leer_mto` aplica `motor.saneado.sanear`), y
se verificaron con las invariantes reales de `motor/invariantes.py`
(cobertura >= 0.75, sin solape, recuento de sustantivos == numero de
elementos) antes de congelarlos aqui. Las 15 filas dan cobertura 1.0.

Convenios seguidos al trazar los tramos:
- El "ambito de fila" (`Segmentacion.ambito_fila`) solo se usa en filas
  con mas de un elemento: es el ', 8.8, zincado' compartido que aparece
  una vez al final y que, segun el diseno (spec.md seccion 4, decision 4), se
  atribuye EXTRAIDO al elemento principal (el primero) e INFERIDO al
  resto -- nunca la calidad, que no se atribuye jamas entre elementos.
- En una fila de un solo elemento no hace falta ambito de fila: todo el
  texto describe a ese elemento, no hay entre-quien repartir nada, asi
  que el tramo del elemento cubre la fila entera.
- Los conectores ("with", "and", "con", "y", "c/w", "Conjunto ", las
  comas de separacion) se listan aparte para que no penalicen la
  cobertura (son prosa de union, no datos).
"""
from __future__ import annotations

from pathlib import Path

from motor.lectura_mto import leer_mto
from motor.modelos import Elemento, Segmentacion
from motor.puerto_llm import PuertoFalso

RUTA_MTO = Path("datos/MTO_tornilleria.xlsx")

# item -> (elementos [(tipo_indicado, span)], ambito_fila [span], conectores [span])
_SEGMENTACION_POR_ITEM: dict[int, tuple[list[tuple[str, tuple[int, int]]],
                                        list[tuple[int, int]],
                                        list[tuple[int, int]]]] = {
    # 'STUD BOLT 7/8" X 130 LG, ASTM A193, GR B7 W/2 HEX. NUT 7/8", ASTM A194, GR 2H, 2 WASHER 7/8", ASTM F436'
    1: ([("ESPARRAGO", (0, 41)), ("TUERCA", (42, 77)), ("ARANDELA", (79, 103))],
        [], [(41, 42), (77, 79)]),
    # 'BOLT DIN 931 M20x90 with NUT DIN 934 M20'
    2: ([("TORNILLO", (0, 19)), ("TUERCA", (25, 40))],
        [], [(19, 25)]),
    # 'Tornillo hexagonal DIN 933 M12 x 50 con tuerca y arandela'
    3: ([("TORNILLO", (0, 35)), ("TUERCA", (40, 46)), ("ARANDELA", (49, 57))],
        [], [(35, 40), (46, 49)]),
    # 'BOLT DIN 933 M16x60 with NUT DIN 934 and WASHER DIN 125, 8.8, zinc plated'
    4: ([("TORNILLO", (0, 19)), ("TUERCA", (25, 36)), ("ARANDELA", (41, 55))],
        [(55, 73)], [(19, 25), (36, 41)]),
    # 'STUD BOLT 1" X 150 LG, ASTM A193, GR B7, W/ 2 NUT ASTM A194, GR 2H, 1 WASHER ASTM F436'
    5: ([("ESPARRAGO", (0, 39)), ("TUERCA", (41, 66)), ("ARANDELA", (68, 86))],
        [], [(39, 41), (66, 68)]),
    # 'Tornillo DIN 931 M16 x 80 con tuerca DIN 934, 8.8, zincado'
    6: ([("TORNILLO", (0, 25)), ("TUERCA", (30, 44))],
        [(44, 58)], [(25, 30)]),
    # 'BOLT DIN 931 M12x60 A4-70 with NUT DIN 934 M12 A4-80'
    7: ([("TORNILLO", (0, 25)), ("TUERCA", (31, 52))],
        [], [(25, 31)]),
    # 'HEX BOLT M16 x 70 c/w NUT AND WASHER, 8.8, ZN'
    8: ([("TORNILLO", (0, 17)), ("TUERCA", (22, 25)), ("ARANDELA", (30, 36))],
        [(36, 45)], [(17, 22), (25, 30)]),
    # 'Conjunto esparrago M20 x 200 DIN 975 con 2 tuercas DIN 934 y 2 arandelas DIN 125, 8.8, zincado'
    9: ([("ESPARRAGO", (9, 36)), ("TUERCA", (41, 58)), ("ARANDELA", (61, 80))],
        [(80, 94)], [(0, 9), (36, 41), (58, 61)]),
    # 'Tornillo hexagonal DIN 933 M10 x 40, 8.8, zincado' (un solo elemento)
    10: ([("TORNILLO", (0, 49))], [], []),
    # 'Tuerca hexagonal DIN 934 M16, A4-80' (un solo elemento)
    11: ([("TUERCA", (0, 35))], [], []),
    # 'STUD BOLT 3/4" X 110 LG, ASTM A193, GR B7' (un solo elemento)
    12: ([("ESPARRAGO", (0, 41))], [], []),
    # 'Tuerca autoblocante DIN 985 M12, 8.8, zincada' (un solo elemento)
    13: ([("TUERCA", (0, 45))], [], []),
    # 'Arandela plana DIN 125 M10, acero, zincada' (un solo elemento)
    14: ([("ARANDELA", (0, 42))], [], []),
    # 'Tornillo Allen cilindrico DIN 912 M10 x 40, 12.9, geomet' (un solo elemento)
    15: ([("TORNILLO", (0, 56))], [], []),
}


def _segmentacion_de(item: int) -> Segmentacion:
    elementos_spec, ambito, conectores = _SEGMENTACION_POR_ITEM[item]
    elementos = [Elemento(tipo_indicado=tipo, span=span) for tipo, span in elementos_spec]
    return Segmentacion(elementos=elementos, ambito_fila=ambito, conectores=conectores)


def puerto_de_guion(ruta: Path = RUTA_MTO) -> PuertoFalso:
    """Construye el `PuertoFalso` guionizado para las 15 filas de `ruta`.

    Las claves del diccionario de respuestas son las descripciones ya
    saneadas tal como las devuelve `leer_mto` -- las mismas que
    `motor.pipeline.procesar_mto` va a pedir --, no las 15 cadenas
    transcritas a mano: si `sanear` cambia, esto se reconstruye solo con
    volver a leer el fichero, sin tocar un caracter aqui.
    """
    filas = leer_mto(ruta)
    respuestas = {fila.descripcion: _segmentacion_de(fila.item) for fila in filas}
    return PuertoFalso(respuestas=respuestas)
