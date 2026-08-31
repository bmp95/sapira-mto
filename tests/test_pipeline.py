from pathlib import Path

from datos.guion_falso import puerto_de_guion
from motor.modelos import Estado, Procedencia
from motor.pipeline import procesar_mto

RUTA = Path("datos/MTO_tornilleria.xlsx")


def test_quince_filas_dan_treinta_lineas():
    lineas = procesar_mto(RUTA, puerto_de_guion())
    assert len(lineas) == 30


def test_reparto_por_tipo():
    lineas = procesar_mto(RUTA, puerto_de_guion())
    tipos = [l.nombre.valor for l in lineas]
    assert tipos.count("TUERCA") == 11
    assert tipos.count("ARANDELA") == 7


def test_las_siete_arandelas_van_a_revision_por_falta_de_calidad():
    lineas = procesar_mto(RUTA, puerto_de_guion())
    arandelas = [l for l in lineas if l.nombre.valor == "ARANDELA"]
    assert len(arandelas) == 7
    assert all(l.estado is Estado.REVISION_MANUAL for l in arandelas)
    assert all(l.calidad.procedencia is Procedencia.AUSENTE for l in arandelas)


def test_cantidades_de_la_fila_uno():
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion())
              if l.fila_origen == 1]
    assert sorted(l.cantidad for l in lineas) == [40, 80, 80]


def test_ninguna_celda_sin_procedencia():
    lineas = procesar_mto(RUTA, puerto_de_guion())
    assert len(lineas) > 0
    for l in lineas:
        for nombre, celda in l.celdas().items():
            assert celda.procedencia is not None, f"{l.id}.{nombre} sin procedencia"


def test_longitud_imperial_sin_unidad_es_inferida():
    """Decision seccion 4.3 del diseno: fila 12, 'STUD BOLT 3/4" X 110 LG, ASTM A193,
    GR B7'. La norma es imperial (ASTM) y el 110 no trae unidad: la
    alternativa (110 pulgadas = 2,8 m) existe pero es absurda, asi que es
    INFERIDO, no DERIVADO, y la linea va a revision con el valor propuesto
    en el motivo -- no en silencio."""
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion()) if l.fila_origen == 12]
    assert len(lineas) == 1
    linea = lineas[0]
    assert linea.longitud.procedencia is Procedencia.INFERIDO
    assert linea.longitud.literal == "110"
    assert linea.estado is Estado.REVISION_MANUAL
    motivo = next(m for m in linea.motivos if m.codigo == "LONGITUD_SIN_UNIDAD")
    assert motivo.valor_propuesto is not None
    assert "110" in motivo.valor_propuesto


def test_linea_sin_norma_va_a_revision():
    """Decision seccion 4.2 del diseno: fila 8, 'HEX BOLT M16 x 70 c/w NUT AND
    WASHER, 8.8, ZN' no menciona DIN/ISO/ASTM/ASME/MSS en ningun tramo.
    Sin norma no se puede pedir a un proveedor (motivo SIN_NORMA), y esto
    manda a revision incluso al tornillo, que por lo demas trae calidad y
    acabado propios."""
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion()) if l.fila_origen == 8]
    assert len(lineas) == 3
    for linea in lineas:
        assert linea.norma.procedencia is Procedencia.AUSENTE
        assert linea.estado is Estado.REVISION_MANUAL
        assert any(m.codigo == "SIN_NORMA" for m in linea.motivos)
