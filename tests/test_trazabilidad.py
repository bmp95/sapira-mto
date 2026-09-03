"""El auditor de invenciones, y los cuatro errores que costo construirlo.

Cada test de aqui es un falso positivo real que este comprobador dio antes de
estar bien. Un auditor que marca invenciones donde no las hay es peor que no
tener auditor: gasta la credibilidad del unico numero que de verdad importa.

Y el ultimo test es el que sostiene a los otros cuatro: si el auditor dejara de
detectar una invencion de verdad, los demas seguirian en verde.
"""
from evaluacion.trazabilidad import auditar_invenciones, cobertura_de_la_evaluacion, valor_rastreable
from motor.modelos import Procedencia, Valor


def _celda(valor, literal, procedencia=Procedencia.EXTRAIDO):
    return Valor(valor=valor, literal=literal, span=(0, len(literal or "")),
                 procedencia=procedencia)


def test_un_valor_de_la_columna_material_no_es_una_invencion():
    """El MTO tiene DOS fuentes de texto. La calidad del elemento principal
    puede venir de la columna MATERIAL, y ahi no la ve quien mire solo la
    descripcion."""
    celda = _celda("8.8", "8.8")
    texto = "Esparrago M20 x 200 DIN 975 y varilla roscada M20 DIN 975"
    assert not valor_rastreable(celda, texto)                    # no esta en la descripcion
    assert valor_rastreable(celda, texto, material_col="8.8")    # si en la columna


def test_una_comilla_tipografica_saneada_no_es_una_invencion():
    """El pipeline trabaja sobre texto saneado: la prima doble se convierte en
    comilla recta. Comparar contra el crudo marca la conversion como invento."""
    celda = _celda('7/8"', '7/8"')
    crudo = "STUD BOLT 7/8" + chr(0x2033) + " X 130 LG, ASTM A193, GR B7"
    assert valor_rastreable(celda, crudo)


def test_los_espacios_multiples_saneados_no_son_una_invencion():
    """El literal se extrae del texto YA saneado, asi que llega con un solo
    espacio. Si el auditor comparase contra el crudo -- con los espacios
    originales -- no lo encontraria y lo marcaria como inventado."""
    celda = _celda("ISO 4017", "DIN 933")
    assert valor_rastreable(celda, "Tornillo    DIN   933   M10  x  40,  8.8")


def test_una_normalizacion_de_catalogo_no_es_una_invencion():
    """Se comprueba el LITERAL, no el VALOR: el catalogo normaliza a proposito
    y exigir que el valor canonico aparezca tal cual marcaria como inventada
    cada normalizacion correcta."""
    assert valor_rastreable(_celda("CINCADO", "zincado"), "Tornillo DIN 933 M10, zincado")
    assert valor_rastreable(_celda("ISO 4017", "DIN 933"), "Tornillo DIN 933 M10 x 40")


def test_lo_derivado_y_lo_heredado_se_auditan_por_su_regla_no_por_el_texto():
    """Ninguno de los dos tiene literal en el texto: su evidencia es la regla
    que lo dedujo o el registro historico que lo contesto."""
    for procedencia in (Procedencia.DERIVADO, Procedencia.HEREDADO):
        celda = Valor(valor="AC", procedencia=procedencia, regla="calidad->material")
        assert valor_rastreable(celda, "M10 x 40")     # no aparece en el texto, y da igual

    # Y no hace falta que el auditor vigile el caso sin regla, porque el propio
    # modelo lo hace imposible de construir. Se comprueba aqui para que, si esa
    # validacion se cayera algun dia, salte por aqui y no en silencio.
    for procedencia in (Procedencia.DERIVADO, Procedencia.HEREDADO):
        try:
            Valor(valor="AC", procedencia=procedencia)
        except ValueError:
            continue
        raise AssertionError(f"{procedencia.value} sin regla deberia ser inconstruible")


def test_una_invencion_de_verdad_si_se_detecta():
    """El guardian de los guardianes. Sin este, los cuatro tests de arriba
    seguirian pasando con un auditor que devolviese True siempre."""
    inventada = _celda("A4-80", "A4-80")
    assert not valor_rastreable(inventada, "Tornillo DIN 933 M10 x 40, 8.8, zincado")
    assert not valor_rastreable(inventada, "Tornillo DIN 933 M10", material_col="8.8")


class _LineaFalsa:
    """Lo minimo que mira el auditor, sin montar un LineaSalida entero."""
    def __init__(self, id_, fila, texto, **celdas):
        self.id, self.fila_origen, self.texto_origen = id_, fila, texto
        vacia = Valor(procedencia=Procedencia.AUSENTE)
        for atributo in ("nombre", "material", "calidad", "medida",
                         "longitud", "norma", "acabado"):
            setattr(self, atributo, celdas.get(atributo, vacia))


def test_auditar_recorre_todas_las_lineas_y_no_solo_las_principales():
    lineas = [
        _LineaFalsa("L001", 1, "Tornillo DIN 933 M10, 8.8", calidad=_celda("8.8", "8.8")),
        _LineaFalsa("L002", 1, "Tornillo DIN 933 M10, 8.8", calidad=_celda("A4-80", "A4-80")),
    ]
    hallazgos = auditar_invenciones(lineas)
    assert [h["linea"] for h in hallazgos] == ["L002"]
    assert hallazgos[0]["atributo"] == "calidad"


def test_la_cobertura_dice_cuantas_lineas_salen_sin_que_nadie_las_mire():
    """El numero incomodo: el gold cubre una linea por fila, y una fila de set
    produce tres. Publicar el escape sin decir esto es media verdad."""
    lineas = [_LineaFalsa("L001", 1, "t"), _LineaFalsa("L002", 1, "t"),
              _LineaFalsa("L003", 1, "t"), _LineaFalsa("L004", 2, "t")]
    cobertura = cobertura_de_la_evaluacion(lineas, {1, 2})
    assert cobertura["lineas_producidas"] == 4
    assert cobertura["evaluadas_contra_gold"] == 2
    assert cobertura["sin_gold"] == 2
