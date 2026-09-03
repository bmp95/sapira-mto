from evaluacion.arnes import evaluar
from evaluacion.cargar_gold import ConfianzaGold, LineaGold
from motor.modelos import LineaSalida, Motivo, Procedencia, Valor

CIERTA = ConfianzaGold.CIERTA
INDECIDIBLE = ConfianzaGold.INDECIDIBLE


def _gold_linea(id_: str, fila: int, nombre: str, calidad: str | None = None,
                conf_calidad: ConfianzaGold = CIERTA) -> LineaGold:
    """Helper de fixture: todo lo demas queda vacio y `cierta`, calidad es
    el unico atributo que varian estos tests."""
    return LineaGold(
        id=id_, fila=fila, cantidad=10, nombre=nombre, conf_nombre=CIERTA,
        material=None, conf_material=CIERTA,
        calidad=calidad, conf_calidad=conf_calidad,
        medida=None, conf_medida=CIERTA,
        longitud=None, conf_longitud=CIERTA,
        norma=None, conf_norma=CIERTA,
        acabado=None, conf_acabado=CIERTA,
    )


def _linea_sistema(id_: str, fila: int, confianza: int, nombre: str = "TORNILLO",
                   calidad: str | None = None) -> LineaSalida:
    linea = LineaSalida.vacia(id=id_, fila_origen=fila, cantidad=10)
    linea.nombre = Valor(valor=nombre, procedencia=Procedencia.INFERIDO)
    if calidad is not None:
        linea.calidad = Valor(valor=calidad, procedencia=Procedencia.INFERIDO)
    linea.confianza = confianza
    return linea


# --------------------------------------------------------------------------
# Escenario 1: una linea resuelta y mal, una resuelta y bien, una en
# revision. Del brief de la Tarea 12 (task-12-brief.md, paso 1).
# --------------------------------------------------------------------------

def _resuelta_mal() -> LineaSalida:
    return _linea_sistema("L001", fila=1, confianza=100, calidad="8.8")


def _resuelta_bien() -> LineaSalida:
    return _linea_sistema("L002", fila=2, confianza=100, calidad="10.9")


def _en_revision() -> LineaSalida:
    return _linea_sistema("L003", fila=3, confianza=70, calidad="10.9")


def _gold() -> list[LineaGold]:
    return [
        _gold_linea("L001", fila=1, nombre="TORNILLO", calidad="10.9"),
        _gold_linea("L002", fila=2, nombre="TORNILLO", calidad="10.9"),
        _gold_linea("L003", fila=3, nombre="TORNILLO", calidad="10.9"),
    ]


def test_escape_solo_cuenta_lineas_resueltas_y_mal():
    m = evaluar(lineas=[_resuelta_mal(), _resuelta_bien(), _en_revision()], gold=_gold())
    assert m.tasa_escape == 1 / 3
    assert m.cobertura == 2 / 3


def test_la_linea_caida_reporta_id_atributo_gold_y_sistema():
    m = evaluar(lineas=[_resuelta_mal(), _resuelta_bien(), _en_revision()], gold=_gold())
    assert len(m.fallas_escape) == 1
    falla = m.fallas_escape[0]
    assert falla.id == "L001"
    assert falla.atributo == "calidad"
    assert falla.valor_gold == "10.9"
    assert falla.valor_sistema == "8.8"


# --------------------------------------------------------------------------
# Escenario 2: una celda marcada indecidible en el gold no puntua ni a
# favor ni en contra. Tambien del brief, paso 1.
# --------------------------------------------------------------------------

def _resuelta_con_celda_indecidible() -> LineaSalida:
    return _linea_sistema("L010", fila=10, confianza=100, nombre="ARANDELA", calidad="8.8")


def _gold_con_indecidible() -> list[LineaGold]:
    return [_gold_linea("L010", fila=10, nombre="ARANDELA", calidad=None, conf_calidad=INDECIDIBLE)]


def test_las_celdas_indecidibles_no_cuentan_como_escape():
    m = evaluar(lineas=[_resuelta_con_celda_indecidible()], gold=_gold_con_indecidible())
    assert m.tasa_escape == 0.0
    assert m.celdas_indecidibles == 1


# --------------------------------------------------------------------------
# Escenario 3: una fila con fallo de segmentacion. El gold espera dos
# lineas (TORNILLO + TUERCA) y el sistema solo produce una: es un fallo
# estructural, no de atributo, y no debe puntuar en ningun desglose por
# atributo aunque la linea que si salio este marcada RESUELTA.
# --------------------------------------------------------------------------

def _gold_fallo_segmentacion() -> list[LineaGold]:
    return [
        _gold_linea("L020-1", fila=20, nombre="TORNILLO"),
        _gold_linea("L020-2", fila=20, nombre="TUERCA"),
    ]


def _sistema_fallo_segmentacion() -> list[LineaSalida]:
    return [_linea_sistema("L020", fila=20, confianza=100, nombre="TORNILLO")]


def test_fila_con_fallo_de_segmentacion_no_puntua_en_atributos():
    m = evaluar(lineas=_sistema_fallo_segmentacion(), gold=_gold_fallo_segmentacion())
    assert len(m.fallas_segmentacion) == 1
    falla = m.fallas_segmentacion[0]
    assert falla.fila == 20
    assert falla.nombres_sistema == ["TORNILLO"]
    assert falla.nombres_gold == ["TORNILLO", "TUERCA"]
    assert m.exactitud_segmentacion == 0.0
    assert m.tasa_escape == 0.0
    assert m.cobertura == 1.0
    assert m.por_atributo["nombre"].evaluables == 0
    assert m.celdas_indecidibles == 0


def test_exactitud_de_segmentacion_promedia_filas_alineadas_y_rotas():
    lineas = [*_sistema_fallo_segmentacion(), _resuelta_bien()]
    gold = [*_gold_fallo_segmentacion(), _gold_linea("L002", fila=2, nombre="TORNILLO", calidad="10.9")]
    m = evaluar(lineas=lineas, gold=gold)
    assert m.exactitud_segmentacion == 1 / 2


# --------------------------------------------------------------------------
# Escenario extra (ronda de correccion 1): ruido de revision NO compara
# valores -- compara si el MTO traia el dato. Una linea en REVISION_MANUAL
# es ruido solo si NINGUNO de los atributos que sus propios `motivos`
# senalan esta marcado `indecidible` en el gold. Si el gold tampoco podia
# saberlo, el sistema acerto al dudar: es una laguna real del dato de
# origen, no ruido -- y cuenta en la metrica hermana `revisiones_dato_ausente`.
# --------------------------------------------------------------------------

def _linea_en_revision_con_motivo(id_: str, fila: int, atributo_senalado: str,
                                  nombre: str = "TORNILLO") -> LineaSalida:
    linea = LineaSalida.vacia(id=id_, fila_origen=fila, cantidad=10)
    linea.nombre = Valor(valor=nombre, procedencia=Procedencia.INFERIDO)
    linea.confianza = 70
    linea.motivos = [Motivo(codigo="SIN_CALIDAD", atributo=atributo_senalado,
                            texto="motivo de prueba")]
    return linea


def test_ruido_de_revision_cuenta_solo_lo_que_el_gold_si_sabia():
    """El sistema duda de 'calidad' en las dos lineas (mismo motivo). En la
    30 el gold SI tenia un valor determinado -> el sistema dudo de mas,
    ruido. En la 31 el gold tambien esta indecidible -> el sistema acerto
    al dudar, no es ruido, es una laguna real del dato de origen."""
    duda_innecesaria = _linea_en_revision_con_motivo("L030", fila=30, atributo_senalado="calidad")
    duda_justificada = _linea_en_revision_con_motivo("L031", fila=31, atributo_senalado="calidad")
    gold = [
        _gold_linea("L030", fila=30, nombre="TORNILLO", calidad="10.9", conf_calidad=CIERTA),
        _gold_linea("L031", fila=31, nombre="TORNILLO", calidad=None, conf_calidad=INDECIDIBLE),
    ]
    m = evaluar(lineas=[duda_innecesaria, duda_justificada], gold=gold)
    assert m.revisiones_evaluables == 2
    assert m.revisiones_ruido == 1
    assert m.revisiones_dato_ausente == 1
    assert m.ruido_revision == 1 / 2
    assert m.tasa_dato_ausente == 1 / 2


def test_un_solo_atributo_indecidible_entre_varios_senalados_ya_marca_dato_ausente():
    """Si el motivo senala 'calidad' y ademas hay un segundo motivo que
    senala 'norma', y CUALQUIERA de los dos esta indecidible en el gold, la
    linea entera es dato ausente -- basta con que uno de los atributos
    senalados sea real y genuinamente inextraible."""
    linea = LineaSalida.vacia(id="L032", fila_origen=32, cantidad=10)
    linea.nombre = Valor(valor="TORNILLO", procedencia=Procedencia.INFERIDO)
    linea.confianza = 70
    linea.motivos = [
        Motivo(codigo="SIN_CALIDAD", atributo="calidad", texto="motivo de prueba"),
        Motivo(codigo="SIN_NORMA", atributo="norma", texto="motivo de prueba"),
    ]
    gold = [LineaGold(
        id="L032", fila=32, cantidad=10, nombre="TORNILLO", conf_nombre=CIERTA,
        material=None, conf_material=CIERTA,
        calidad="10.9", conf_calidad=CIERTA,   # esta si la sabia el gold
        medida=None, conf_medida=CIERTA,
        longitud=None, conf_longitud=CIERTA,
        norma=None, conf_norma=INDECIDIBLE,     # esta no -- basta esta sola
        acabado=None, conf_acabado=CIERTA,
    )]
    m = evaluar(lineas=[linea], gold=gold)
    assert m.revisiones_dato_ausente == 1
    assert m.revisiones_ruido == 0


def test_motivo_sin_atributo_no_cuenta_como_evidencia_de_dato_ausente():
    """Un motivo estructural (LINEA_SIN_CELDAS_EVALUABLES, sin atributo
    asociado) no aporta evidencia ni a favor ni en contra: si es el unico
    motivo, la linea cae en ruido por defecto, no en dato ausente, aunque
    el gold tenga celdas indecidibles que el motivo nunca senalo."""
    linea = LineaSalida.vacia(id="L040", fila_origen=40, cantidad=10)
    linea.nombre = Valor(valor="TORNILLO", procedencia=Procedencia.INFERIDO)
    linea.confianza = 0
    linea.motivos = [Motivo(codigo="LINEA_SIN_CELDAS_EVALUABLES", atributo=None,
                            texto="motivo de prueba", factor_limitante="ausente")]
    gold = [_gold_linea("L040", fila=40, nombre="TORNILLO", calidad=None,
                        conf_calidad=INDECIDIBLE)]
    m = evaluar(lineas=[linea], gold=gold)
    assert m.revisiones_ruido == 1
    assert m.revisiones_dato_ausente == 0


def test_ruido_y_dato_ausente_suman_las_revisiones_evaluables():
    duda_innecesaria = _linea_en_revision_con_motivo("L030", fila=30, atributo_senalado="calidad")
    duda_justificada = _linea_en_revision_con_motivo("L031", fila=31, atributo_senalado="calidad")
    gold = [
        _gold_linea("L030", fila=30, nombre="TORNILLO", calidad="10.9", conf_calidad=CIERTA),
        _gold_linea("L031", fila=31, nombre="TORNILLO", calidad=None, conf_calidad=INDECIDIBLE),
    ]
    m = evaluar(lineas=[duda_innecesaria, duda_justificada], gold=gold)
    assert m.revisiones_ruido + m.revisiones_dato_ausente == m.revisiones_evaluables


def test_ruido_de_revision_es_none_sin_lineas_en_revision():
    m = evaluar(lineas=[_resuelta_bien()],
               gold=[_gold_linea("L002", fila=2, nombre="TORNILLO", calidad="10.9")])
    assert m.revisiones_evaluables == 0
    assert m.ruido_revision is None
    assert m.tasa_dato_ausente is None


# --------------------------------------------------------------------------
# Desglose por atributo: aciertos, evaluables e indecidibles se cuentan
# celda a celda, no linea a linea.
# --------------------------------------------------------------------------

def test_desglose_por_atributo_cuenta_aciertos_evaluables_e_indecidibles():
    m = evaluar(lineas=[_resuelta_mal(), _resuelta_bien(), _en_revision()], gold=_gold())
    calidad = m.por_atributo["calidad"]
    assert calidad.evaluables == 3
    assert calidad.aciertos == 2
    assert calidad.indecidibles == 0
    nombre = m.por_atributo["nombre"]
    assert nombre.evaluables == 3
    assert nombre.aciertos == 3
