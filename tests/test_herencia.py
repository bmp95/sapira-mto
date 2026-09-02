"""Herencia desde el historico (§13.2).

La regla de negocio: una obra pasa por hasta 25 revisiones y la misma pieza
sin calidad reaparece en casi todas. Preguntar una vez y heredar las otras
veinticuatro es el argumento de negocio principal del sistema.

Las cuatro condiciones que no se negocian: coincidencia EXACTA de clave, el
conflicto no hereda, nada de sugerencias aproximadas, y heredar no salta las
comprobaciones de dominio.
"""
import pytest

from motor.coherencias import TODAS_ACTIVAS
from motor.historico import Historico, RespuestaHistorica, clave_de
from motor.lectura_mto import FilaMTO
from motor.modelos import Elemento, Estado, Procedencia, Segmentacion
from motor.pipeline import POLITICAS_POR_DEFECTO, _procesar_fila
from motor.puerto_llm import PuertoFalso

ARANDELA = "ARANDELA M16 DIN 125 CINCADA"
TORNILLO = "TORNILLO M16 X 80 DIN 931 CINCADO"


def _procesar_una(descripcion: str, historico: Historico | None = None):
    """Una fila de un solo elemento: el guion la declara entera como un tramo."""
    fila = FilaMTO(item=1, descripcion=descripcion, material_col="", medida_col="",
                   cantidad=10, unidad="ud")
    puerto = PuertoFalso({descripcion: Segmentacion(
        elementos=[Elemento(tipo_indicado=descripcion.split()[0], span=(0, len(descripcion)))])})
    contador = {"n": 0}

    def siguiente_id():
        contador["n"] += 1
        return f"L{contador['n']:03d}"

    lineas = _procesar_fila(fila, puerto, POLITICAS_POR_DEFECTO, TODAS_ACTIVAS,
                            siguiente_id, historico=historico)
    assert len(lineas) == 1
    return lineas[0]


def _respuesta(linea, valor: str, autor: str = "ingenieria@epc.es") -> RespuestaHistorica:
    return RespuestaHistorica(clave=clave_de(linea, "calidad"), atributo="calidad",
                              valor=valor, autor=autor, origen="ingenieria",
                              fecha="2026-08-31", mto_origen="rev9.xlsx",
                              revision_origen="9")


@pytest.fixture
def arandela_en_revision():
    """La misma arandela procesada sin historico: el patron contra el que se
    calcula la clave y el estado que se quiere cambiar."""
    return _procesar_una(ARANDELA)


def test_sin_historico_la_arandela_va_a_revision(arandela_en_revision):
    assert arandela_en_revision.calidad.procedencia is Procedencia.AUSENTE
    assert arandela_en_revision.estado is Estado.REVISION_MANUAL


def test_una_linea_sin_calidad_se_resuelve_desde_el_historico(arandela_en_revision):
    """El caso de negocio entero: preguntar una vez y heredar en las siguientes."""
    h = Historico()
    h.registrar(_respuesta(arandela_en_revision, "200HV"))

    r = _procesar_una(ARANDELA, historico=h)
    assert r.calidad.valor == "200HV"
    assert r.calidad.procedencia is Procedencia.HEREDADO
    assert r.confianza == 100
    assert r.estado is Estado.RESUELTA


def test_lo_heredado_dice_quien_y_cuando(arandela_en_revision):
    h = Historico()
    h.registrar(_respuesta(arandela_en_revision, "200HV"))

    r = _procesar_una(ARANDELA, historico=h)
    assert "ingenieria@epc.es" in r.calidad.regla
    heredados = [m for m in r.motivos if m.codigo == "VALOR_HEREDADO"]
    assert len(heredados) == 1
    assert "2026-08-31" in heredados[0].texto


# La pieza de este test tiene calidad, asi que se resuelve sola: es la unica
# forma de que el conflicto sea lo UNICO que puede mandarla a revision. Con la
# arandela sin calidad el test pasaria igual con la regla del conflicto
# desactivada, porque la obligatoriedad ya la tumba por otro motivo.
COMPLETA = "ARANDELA M16 DIN 125 300HV"


def test_la_pieza_del_test_de_conflicto_se_resuelve_sola():
    """Guardian del guardian: si esto dejara de ser RESUELTA, el test de
    conflicto de abajo pasaria sin comprobar nada."""
    r = _procesar_una(COMPLETA)
    assert r.estado is Estado.RESUELTA
    assert r.acabado.procedencia is Procedencia.AUSENTE


def test_el_conflicto_no_hereda_y_manda_a_revision():
    """Dos personas contestaron cosas distintas: el sistema no elige, y no se
    queda callado -- saca la linea de la cola de resueltas."""
    base = _procesar_una(COMPLETA)
    h = Historico()
    for autor, valor in (("ana@epc.es", "CINCADO"), ("luis@epc.es", "GALVANIZADO EN CALIENTE")):
        h.registrar(RespuestaHistorica(clave=clave_de(base, "acabado"), atributo="acabado",
                                       valor=valor, autor=autor, origen="ingenieria",
                                       fecha="2026-08-31", mto_origen="rev9.xlsx",
                                       revision_origen="9"))

    r = _procesar_una(COMPLETA, historico=h)
    assert r.acabado.procedencia is Procedencia.AUSENTE
    assert r.estado is Estado.REVISION_MANUAL
    assert any(m.codigo == "HISTORICO_EN_CONFLICTO" for m in r.motivos)


def test_el_conflicto_tampoco_propone_un_candidato():
    """Condicion 3: nada de sugerencias aproximadas. Ni el mas frecuente ni el
    mas reciente -- si hay conflicto, la celda se queda vacia."""
    base = _procesar_una(COMPLETA)
    h = Historico()
    for autor, valor in (("ana@epc.es", "CINCADO"), ("luis@epc.es", "GALVANIZADO EN CALIENTE")):
        h.registrar(RespuestaHistorica(clave=clave_de(base, "acabado"), atributo="acabado",
                                       valor=valor, autor=autor, origen="ingenieria",
                                       fecha="2026-08-31", mto_origen="rev9.xlsx",
                                       revision_origen="9"))

    r = _procesar_una(COMPLETA, historico=h)
    assert r.acabado.valor is None
    conflicto = [m for m in r.motivos if m.codigo == "HISTORICO_EN_CONFLICTO"]
    assert len(conflicto) == 1
    assert conflicto[0].valor_propuesto is None


def test_una_incoherencia_cruzada_tumba_la_herencia():
    """Condicion 4: heredar no salta las comprobaciones de dominio.

    200HV es una dureza de arandela. Aunque el historico la ofrezca para un
    tornillo con clave valida, CALIDAD_SOLO_ARANDELA tiene que tumbarla.
    """
    tornillo = _procesar_una(TORNILLO)
    h = Historico()
    h.registrar(RespuestaHistorica(clave=clave_de(tornillo, "calidad"), atributo="calidad",
                                   valor="200HV", autor="ingenieria@epc.es", origen="ingenieria",
                                   fecha="2026-08-31", mto_origen="rev9.xlsx", revision_origen="9"))

    r = _procesar_una(TORNILLO, historico=h)
    assert r.estado is Estado.REVISION_MANUAL
    assert any(m.codigo == "CALIDAD_SOLO_ARANDELA" for m in r.motivos)


def test_una_clave_que_no_es_exactamente_la_misma_no_hereda(arandela_en_revision):
    """Condicion 1: coincidencia exacta. La misma arandela SIN acabado es otra
    pieza a efectos de clave, y se vuelve a preguntar."""
    h = Historico()
    h.registrar(_respuesta(arandela_en_revision, "200HV"))

    r = _procesar_una("ARANDELA M16 DIN 125", historico=h)
    assert r.calidad.procedencia is Procedencia.AUSENTE
    assert r.estado is Estado.REVISION_MANUAL
    assert not any(m.codigo == "VALOR_HEREDADO" for m in r.motivos)


def test_lo_escrito_en_el_mto_gana_a_lo_heredado():
    """La herencia es el ultimo recurso: solo toca atributos AUSENTE."""
    con_calidad = _procesar_una("ARANDELA M16 DIN 125 CINCADA 300HV")
    assert con_calidad.calidad.valor == "300HV"

    h = Historico()
    h.registrar(RespuestaHistorica(clave=clave_de(con_calidad, "calidad"), atributo="calidad",
                                   valor="200HV", autor="ingenieria@epc.es", origen="ingenieria",
                                   fecha="2026-08-31", mto_origen="rev9.xlsx", revision_origen="9"))

    r = _procesar_una("ARANDELA M16 DIN 125 CINCADA 300HV", historico=h)
    assert r.calidad.valor == "300HV"
    assert r.calidad.procedencia is Procedencia.EXTRAIDO
