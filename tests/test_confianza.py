import pytest

from motor.confianza import aplicar_confianza, confianza_celda
from motor.invariantes import verificar_literal
from motor.modelos import Estado, LineaSalida, Procedencia, Valor


def _v(p, **kw):
    base = {"valor": "X", "literal": "X", "span": (0, 1)}
    if p is Procedencia.DERIVADO:
        base = {"valor": "X", "regla": "MAT-8.8"}
    if p is Procedencia.AUSENTE:
        base = {}
    return Valor(procedencia=p, **{**base, **kw})


def test_extraido_verificado_unanime_y_coherente_da_100():
    c, factor = confianza_celda(_v(Procedencia.EXTRAIDO), True, 3, True)
    assert c == 100 and factor == "ninguno"


def test_derivado_tambien_llega_a_100():
    assert confianza_celda(_v(Procedencia.DERIVADO), True, 3, True)[0] == 100


def test_inferido_topa_en_70():
    c, factor = confianza_celda(_v(Procedencia.INFERIDO), True, 3, True)
    assert c == 70 and factor == "procedencia"


def test_literal_no_verificado_deja_la_celda_en_cero():
    c, factor = confianza_celda(_v(Procedencia.EXTRAIDO), False, 3, True)
    assert c == 0 and factor == "literal"


def test_dos_de_tres_votos_baja_a_67():
    c, factor = confianza_celda(_v(Procedencia.EXTRAIDO), True, 2, True)
    assert c == 67 and factor == "segmentacion"


def test_incoherencia_deja_la_celda_en_cero():
    assert confianza_celda(_v(Procedencia.EXTRAIDO), True, 3, False) == (0, "coherencia")


def test_la_linea_toma_el_minimo_y_deriva_su_estado():
    linea = LineaSalida.vacia(id="L1", fila_origen=1, cantidad=1)
    linea.nombre = _v(Procedencia.EXTRAIDO)
    linea.calidad = _v(Procedencia.INFERIDO)
    r = aplicar_confianza(linea, votos=3, motivos=[],
                          literales_ok={"nombre": True, "calidad": True})
    assert r.confianza == 70
    assert r.estado is Estado.REVISION_MANUAL
    assert any(m.factor_limitante == "procedencia" for m in r.motivos)


def test_span_presente_pero_literal_no_coincide_deja_la_celda_en_cero():
    """Correccion A: el viejo cheque 'celda.span is not None' habria dado el factor
    literal en 100 aqui, porque el span existe. verificar_literal compara el texto
    real bajo ese span contra el literal declarado, y aqui no coinciden: debe caer a 0.
    """
    texto = "TUERCA DIN 934"
    valor = Valor(valor="TORNILLO", literal="TORNILLO", span=(0, 6), procedencia=Procedencia.EXTRAIDO)
    assert valor.span is not None
    ok = verificar_literal(valor.literal, texto, valor.span)
    assert ok is False

    linea = LineaSalida.vacia(id="L2", fila_origen=2, cantidad=1)
    linea.nombre = valor
    r = aplicar_confianza(linea, votos=3, motivos=[], literales_ok={"nombre": ok})
    assert r.confianza == 0
    assert any(m.factor_limitante == "literal" for m in r.motivos)


def test_derivado_no_necesita_entrada_en_literales_ok():
    """Un valor DERIVADO no tiene literal en el texto que verificar: el factor
    literal se da por bueno sin consultar el diccionario, aunque venga vacio.
    """
    linea = LineaSalida.vacia(id="L3", fila_origen=3, cantidad=1)
    linea.material = Valor(valor="A4-80", procedencia=Procedencia.DERIVADO, regla="MAT-8.8")
    r = aplicar_confianza(linea, votos=3, motivos=[], literales_ok={})
    assert r.confianza == 100


def test_literales_ok_sin_clave_para_celda_no_derivada_revienta():
    """Sin valores por defecto silenciosos: si la celda no es DERIVADO y el llamador
    no calculo su entrada en literales_ok, debe reventar, no asumir un booleano.
    """
    linea = LineaSalida.vacia(id="L4", fila_origen=4, cantidad=1)
    linea.nombre = _v(Procedencia.EXTRAIDO)
    with pytest.raises(KeyError):
        aplicar_confianza(linea, votos=3, motivos=[], literales_ok={})


def test_linea_sin_celdas_evaluables_da_confianza_cero():
    """Correccion B: LineaSalida.vacia() deja las siete celdas en AUSENTE. Si
    ninguna es evaluable, la confianza de la linea es 0, no 100.
    """
    linea = LineaSalida.vacia(id="L5", fila_origen=5, cantidad=1)
    r = aplicar_confianza(linea, votos=3, motivos=[], literales_ok={})
    assert r.confianza == 0
    assert r.estado is Estado.REVISION_MANUAL
    assert len(r.motivos) == 1
    assert r.motivos[0].factor_limitante == "ausente"
