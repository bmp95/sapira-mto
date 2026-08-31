from motor.modelos import Elemento, Segmentacion
from motor.invariantes import verificar_literal, cobertura, hay_solape, contar_sustantivos


def test_literal_verificado():
    t = 'STUD BOLT 7/8" X 130'
    assert verificar_literal("BOLT", t, (5, 9)) is True
    assert verificar_literal("BOLT", t, (0, 4)) is False   # ahi pone STUD
    assert verificar_literal("A193", t, (0, 4)) is False   # no aparece


def test_cobertura_detecta_elemento_perdido():
    t = "BOLT M16 with NUT and WASHER"
    completa = Segmentacion(elementos=[
        Elemento(tipo_indicado="BOLT", span=(0, 11)),
        Elemento(tipo_indicado="NUT", span=(14, 17)),
        Elemento(tipo_indicado="WASHER", span=(22, 28))])
    assert cobertura(t, completa) > 0.75
    coja = Segmentacion(elementos=completa.elementos[:2])
    assert cobertura(t, coja) < 0.75


def test_solape():
    s = Segmentacion(elementos=[Elemento(tipo_indicado="A", span=(0, 10)),
                                Elemento(tipo_indicado="B", span=(5, 15))])
    assert hay_solape(s) is True


def test_recuento_independiente_de_sustantivos():
    assert contar_sustantivos("BOLT DIN 933 M16 with NUT and WASHER") == 3
    assert contar_sustantivos("Tornillo hexagonal DIN 933 con tuerca y arandela") == 3
    assert contar_sustantivos("STUD BOLT 7/8, 2 HEX. NUT, 2 WASHER") == 3
    assert contar_sustantivos("Tuerca hexagonal DIN 934 M16") == 1
