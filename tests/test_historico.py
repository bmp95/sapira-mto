from motor.historico import Hallazgo, Historico, RespuestaHistorica, clave_de
from motor.modelos import LineaSalida, Procedencia, Valor


def _linea(**kw):
    l = LineaSalida.vacia(id="L1", fila_origen=1, cantidad=1)
    for k, v in kw.items():
        setattr(l, k, Valor(valor=v, literal=v, span=(0, 1), procedencia=Procedencia.EXTRAIDO))
    return l


def _respuesta(clave, valor="200HV", autor="ingenieria@epc.es"):
    return RespuestaHistorica(clave=clave, atributo="calidad", valor=valor, autor=autor,
                              origen="ingenieria", fecha="2026-08-31",
                              mto_origen="MTO_rev9.xlsx", revision_origen="9")


def test_clave_ignora_el_atributo_que_se_pregunta():
    """La clave son los OTROS seis atributos: es la identidad de la pieza sin la incognita."""
    linea = _linea(nombre="ARANDELA", norma="ISO 7089", medida="M10", acabado="CINCADO")
    clave = clave_de(linea, "calidad")
    assert ("calidad", "200HV") not in clave
    assert ("nombre", "ARANDELA") in clave
    assert ("norma", "ISO 7089") in clave


def test_los_ausentes_van_marcados_explicitamente():
    clave = clave_de(_linea(nombre="ARANDELA"), "calidad")
    assert ("longitud", "AUSENTE") in clave


def test_coincidencia_exacta_devuelve_la_respuesta():
    h = Historico()
    linea = _linea(nombre="ARANDELA", norma="ISO 7089", medida="M10", acabado="CINCADO")
    clave = clave_de(linea, "calidad")
    h.registrar(_respuesta(clave))
    r = h.buscar(clave, "calidad")
    assert r.hallazgo is Hallazgo.UNICA
    assert r.valor == "200HV"
    assert r.respuesta.autor == "ingenieria@epc.es"


def test_un_solo_atributo_distinto_ya_no_coincide():
    """Cero coincidencia difusa: la arandela cincada y la sin acabado son piezas distintas (seccion 9)."""
    h = Historico()
    con_acabado = clave_de(_linea(nombre="ARANDELA", norma="ISO 7089", medida="M10",
                                  acabado="CINCADO"), "calidad")
    sin_acabado = clave_de(_linea(nombre="ARANDELA", norma="ISO 7089", medida="M10"), "calidad")
    h.registrar(_respuesta(con_acabado))
    assert h.buscar(sin_acabado, "calidad").hallazgo is Hallazgo.NINGUNA


def test_dos_respuestas_distintas_para_la_misma_clave_dan_conflicto():
    """Un historico que se contradice es peor que uno vacio: no se hereda nada."""
    h = Historico()
    clave = clave_de(_linea(nombre="ARANDELA", norma="ISO 7089", medida="M10"), "calidad")
    h.registrar(_respuesta(clave, valor="200HV"))
    h.registrar(_respuesta(clave, valor="140HV", autor="comprador@epc.es"))
    r = h.buscar(clave, "calidad")
    assert r.hallazgo is Hallazgo.CONFLICTO
    assert r.valor is None
    assert len(r.candidatas) == 2


def test_repetir_la_misma_respuesta_no_es_conflicto():
    h = Historico()
    clave = clave_de(_linea(nombre="ARANDELA", norma="ISO 7089"), "calidad")
    h.registrar(_respuesta(clave, valor="200HV"))
    h.registrar(_respuesta(clave, valor="200HV", autor="otro@epc.es"))
    assert h.buscar(clave, "calidad").hallazgo is Hallazgo.UNICA


def test_no_hay_sugerencias_aproximadas():
    """Si no hay coincidencia exacta no pasa nada. Nada de 'materiales parecidos'."""
    h = Historico()
    h.registrar(_respuesta(clave_de(_linea(nombre="ARANDELA", medida="M10"), "calidad")))
    otra = clave_de(_linea(nombre="ARANDELA", medida="M12"), "calidad")
    r = h.buscar(otra, "calidad")
    assert r.hallazgo is Hallazgo.NINGUNA
    assert r.valor is None
    assert r.candidatas == []


def test_persiste_y_recarga(tmp_path):
    ruta = tmp_path / "historico.json"
    h = Historico()
    clave = clave_de(_linea(nombre="ARANDELA", medida="M10"), "calidad")
    h.registrar(_respuesta(clave))
    h.guardar(ruta)
    assert Historico.cargar(ruta).buscar(clave, "calidad").valor == "200HV"
