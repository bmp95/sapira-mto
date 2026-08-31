from motor.modelos import LineaSalida, Valor, Procedencia
from motor.coherencias import comprobar, TODAS_ACTIVAS


def _linea(**kw):
    l = LineaSalida.vacia(id="L1", fila_origen=1, cantidad=1)
    for k, v in kw.items():
        setattr(l, k, Valor(valor=v, literal=v, span=(0, 1), procedencia=Procedencia.EXTRAIDO))
    return l


def test_calidad_10_en_tornillo_es_incoherente():
    codigos = [m.codigo for m in comprobar(_linea(nombre="TORNILLO", calidad="10"), TODAS_ACTIVAS)]
    assert "CALIDAD_SOLO_TUERCA" in codigos


def test_HV_en_tornillo_es_incoherente():
    codigos = [m.codigo for m in comprobar(_linea(nombre="TORNILLO", calidad="200HV"), TODAS_ACTIVAS)]
    assert "CALIDAD_SOLO_ARANDELA" in codigos


def test_inox_cincado_es_incoherente():
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="TUERCA", calidad="A4-80", acabado="CINCADO"), TODAS_ACTIVAS)]
    assert "INOX_CON_ACABADO_ZINC" in codigos


def test_astm_con_metrica_es_incoherente():
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="ESPARRAGO", norma="ASTM A193", medida="M20"), TODAS_ACTIVAS)]
    assert "SISTEMA_MEDIDA_INCOHERENTE" in codigos


def test_tuerca_con_8_8_no_es_incoherencia():
    """Atestiguado en la fila 13 del MTO: es vocabulario del cliente."""
    codigos = [m.codigo for m in comprobar(_linea(nombre="TUERCA", calidad="8.8"), TODAS_ACTIVAS)]
    assert codigos == []


def test_interruptor_apaga_la_comprobacion():
    apagado = {**TODAS_ACTIVAS, "inox_acabado": False}
    assert comprobar(_linea(nombre="TUERCA", calidad="A4-80", acabado="CINCADO"), apagado) == []
