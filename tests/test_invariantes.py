from motor.invariantes import (
    ambito_sin_dimensiones,
    cobertura,
    contar_sustantivos,
    hay_solape,
    verificar_literal,
)
from motor.modelos import Elemento, Segmentacion


def test_literal_verificado():
    t = 'STUD BOLT 7/8" X 130'
    assert verificar_literal("BOLT", t, (5, 9)) is True
    assert verificar_literal("BOLT", t, (0, 4)) is False   # ahi pone STUD
    assert verificar_literal("A193", t, (0, 4)) is False   # no aparece


def test_cobertura_detecta_elemento_perdido():
    t = "BOLT M16 with NUT and WASHER"
    completa = Segmentacion(elementos=[
        Elemento(tipo_indicado="BOLT", span=(0, 8)),
        Elemento(tipo_indicado="NUT", span=(14, 17)),
        Elemento(tipo_indicado="WASHER", span=(22, 28))],
        conectores=[(9, 13), (18, 21)])
    assert cobertura(t, completa) > 0.75
    coja = Segmentacion(elementos=completa.elementos[:2],
                        conectores=[(9, 13), (18, 21)])
    assert cobertura(t, coja) < 0.75


def test_los_conectores_no_penalizan_la_cobertura():
    t = "BOLT M16 with NUT and WASHER"
    con_conectores = Segmentacion(elementos=[
        Elemento(tipo_indicado="BOLT", span=(0, 8)),
        Elemento(tipo_indicado="NUT", span=(14, 17)),
        Elemento(tipo_indicado="WASHER", span=(22, 28))],
        conectores=[(9, 13), (18, 21)])
    assert cobertura(t, con_conectores) == 1.0


def test_solape():
    s = Segmentacion(elementos=[Elemento(tipo_indicado="A", span=(0, 10)),
                                Elemento(tipo_indicado="B", span=(5, 15))])
    assert hay_solape(s) is True


def test_recuento_independiente_de_sustantivos():
    assert contar_sustantivos("BOLT DIN 933 M16 with NUT and WASHER") == 3
    assert contar_sustantivos("Tornillo hexagonal DIN 933 con tuerca y arandela") == 3
    assert contar_sustantivos("STUD BOLT 7/8, 2 HEX. NUT, 2 WASHER") == 3
    assert contar_sustantivos("Tuerca hexagonal DIN 934 M16") == 1

def test_ambito_sin_dimensiones_con_calidad_y_acabado_no_dispara():
    """El ambito de fila describe la fila entera: calidad y acabado son
    validos, no dimensiones."""
    t = "NUT DIN 934, 8.8, zincado"
    seg = Segmentacion(elementos=[Elemento(tipo_indicado="NUT", span=(0, 11))],
                       ambito_fila=[(11, 25)])
    assert ambito_sin_dimensiones(t, seg) is True


def test_ambito_sin_dimensiones_con_medida_metrica_dispara():
    """Una medida (M20) en el ambito de fila describe una pieza concreta,
    no la fila entera: es la senal de que el segmentador metio ahi la
    descripcion de un elemento que nunca nombro."""
    t = "NUT DIN 934, M20"
    seg = Segmentacion(elementos=[Elemento(tipo_indicado="NUT", span=(0, 11))],
                       ambito_fila=[(11, 16)])
    assert ambito_sin_dimensiones(t, seg) is False
