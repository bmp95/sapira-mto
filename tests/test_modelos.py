import pytest

from motor.modelos import Estado, LineaSalida, Procedencia, Valor


def test_valor_extraido_exige_span_y_literal():
    v = Valor(valor="TORNILLO", literal="BOLT", span=(0, 4), procedencia=Procedencia.EXTRAIDO)
    assert v.confianza_procedencia == 100


def test_valor_inferido_puntua_70():
    v = Valor(valor="130 mm", literal="130", span=(20, 23), procedencia=Procedencia.INFERIDO)
    assert v.confianza_procedencia == 70


def test_valor_ausente_no_exige_span():
    v = Valor(valor=None, literal=None, span=None, procedencia=Procedencia.AUSENTE)
    assert v.confianza_procedencia is None


def test_extraido_sin_span_revienta():
    with pytest.raises(ValueError, match="span"):
        Valor(valor="TORNILLO", literal="BOLT", span=None, procedencia=Procedencia.EXTRAIDO)


def test_estado_se_deriva_de_la_confianza():
    linea = LineaSalida.vacia(id="L001", fila_origen=1, cantidad=40)
    linea.confianza = 100
    assert linea.estado == Estado.RESUELTA
    linea.confianza = 99
    assert linea.estado == Estado.REVISION_MANUAL
