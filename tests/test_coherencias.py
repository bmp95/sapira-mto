import pytest

from motor.coherencias import TODAS_ACTIVAS, comprobar
from motor.modelos import LineaSalida, Procedencia, Valor


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


def test_los_textos_de_motivo_conservan_sus_tildes():
    """Verifica que las palabras completas con tildes aparecen en los textos de motivos."""
    # CALIDAD_SOLO_TUERCA: debe contener "sólo" completo
    palabra_solo = "s" + chr(0xf3) + "lo"
    motivos = comprobar(_linea(nombre="TORNILLO", calidad="10"), TODAS_ACTIVAS)
    assert any(palabra_solo in m.texto for m in motivos if m.codigo == "CALIDAD_SOLO_TUERCA"), \
        f"CALIDAD_SOLO_TUERCA debe contener la palabra '{palabra_solo}' completa"

    # INOX_CON_ACABADO_ZINC: debe contener "austenítico" completo (con una sola tilde)
    palabra_austenitico = "austen" + chr(0xed) + "tico"
    motivos = comprobar(_linea(nombre="TUERCA", calidad="A4-80", acabado="CINCADO"), TODAS_ACTIVAS)
    assert any(palabra_austenitico in m.texto for m in motivos if m.codigo == "INOX_CON_ACABADO_ZINC"), \
        f"INOX_CON_ACABADO_ZINC debe contener la palabra '{palabra_austenitico}' completa"

    # SISTEMA_MEDIDA_INCOHERENTE (imperial->metrica): debe contener "métrica" completo
    palabra_metrica = "m" + chr(0xe9) + "trica"
    motivos = comprobar(_linea(nombre="ESPARRAGO", norma="ASTM A193", medida="M20"), TODAS_ACTIVAS)
    assert any(palabra_metrica in m.texto for m in motivos if m.codigo == "SISTEMA_MEDIDA_INCOHERENTE"), \
        f"SISTEMA_MEDIDA_INCOHERENTE debe contener la palabra '{palabra_metrica}' completa"

    # GRADO_ASTM_INCOHERENTE (B7): debe contener "tornillería" completo
    palabra_tornilleria = "torniller" + chr(0xed) + "a"
    motivos = comprobar(_linea(nombre="ARANDELA", calidad="B7"), TODAS_ACTIVAS)
    assert any(palabra_tornilleria in m.texto for m in motivos if m.codigo == "GRADO_ASTM_INCOHERENTE"), \
        f"GRADO_ASTM_INCOHERENTE debe contener la palabra '{palabra_tornilleria}' completa"


# Nuevas comprobaciones (6 más)

def test_aluminio_con_calidad_acero_es_incoherente():
    codigos = [m.codigo for m in comprobar(
        _linea(material="ALUMINIO", calidad="8.8"), TODAS_ACTIVAS)]
    assert "MATERIAL_CONTRADICE_CALIDAD" in codigos


def test_material_con_calidad_compatible_no_es_incoherencia():
    """AC con 8.8 es válido (8.8 es acero)."""
    codigos = [m.codigo for m in comprobar(
        _linea(material="AC", calidad="8.8"), TODAS_ACTIVAS)]
    assert "MATERIAL_CONTRADICE_CALIDAD" not in codigos


def test_inox_con_norma_acero_es_incoherente():
    codigos = [m.codigo for m in comprobar(
        _linea(material="INOX", norma="ASTM F436"), TODAS_ACTIVAS)]
    assert "MATERIAL_CONTRADICE_NORMA" in codigos


def test_material_con_norma_compatible_no_es_incoherencia():
    """AC con ASTM F436 es válido (F436 es acero)."""
    codigos = [m.codigo for m in comprobar(
        _linea(material="AC", norma="ASTM F436"), TODAS_ACTIVAS)]
    assert "MATERIAL_CONTRADICE_NORMA" not in codigos


def test_tornillo_con_norma_tuerca_es_incoherente():
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="TORNILLO", norma="ISO 4032"), TODAS_ACTIVAS)]
    assert "NOMBRE_CONTRADICE_NORMA" in codigos


def test_nombre_con_norma_compatible_no_es_incoherencia():
    """TORNILLO con ISO 4017 es válido (ISO 4017 es norma de tornillo)."""
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="TORNILLO", norma="ISO 4017"), TODAS_ACTIVAS)]
    assert "NOMBRE_CONTRADICE_NORMA" not in codigos


def test_esparrago_con_norma_varilla_es_equivalencia():
    """ESPARRAGO con DIN 975 (norma de varilla) emite nota informativa, no contradicción."""
    motivos = comprobar(_linea(nombre="ESPARRAGO", norma="DIN 975"), TODAS_ACTIVAS)
    codigos = [m.codigo for m in motivos]
    assert "NOMBRE_Y_NORMA_EQUIVALENTES" in codigos
    assert "NOMBRE_CONTRADICE_NORMA" not in codigos


def test_varilla_roscada_con_norma_varilla_no_es_incoherencia():
    """VARILLA ROSCADA con DIN 975 coinciden, no hay motivo."""
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="VARILLA ROSCADA", norma="DIN 975"), TODAS_ACTIVAS)]
    assert "NOMBRE_CONTRADICE_NORMA" not in codigos
    assert "NOMBRE_Y_NORMA_EQUIVALENTES" not in codigos


def test_tuerca_con_norma_tornillo_es_incoherencia():
    """TUERCA con ISO 4017 (norma de tornillo) es contradicción."""
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="TUERCA", norma="ISO 4017"), TODAS_ACTIVAS)]
    assert "NOMBRE_CONTRADICE_NORMA" in codigos


def test_arandela_con_norma_tuerca_es_incoherencia():
    """ARANDELA con ISO 4032 (norma de tuerca) es contradicción."""
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="ARANDELA", norma="ISO 4032"), TODAS_ACTIVAS)]
    assert "NOMBRE_CONTRADICE_NORMA" in codigos


def test_esparrago_varilla_equivalencia_desactivada():
    """Con esparrago_equivale_a_varilla apagado, vuelve a ser contradicción."""
    apagado = {**TODAS_ACTIVAS, "esparrago_equivale_a_varilla": False}
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="ESPARRAGO", norma="DIN 975"), apagado)]
    assert "NOMBRE_CONTRADICE_NORMA" in codigos
    assert "NOMBRE_Y_NORMA_EQUIVALENTES" not in codigos


def test_aluminio_cincado_es_incoherente():
    codigos = [m.codigo for m in comprobar(
        _linea(material="ALUMINIO", acabado="CINCADO"), TODAS_ACTIVAS)]
    assert "MATERIAL_NO_ADMITE_ZINC" in codigos


def test_laton_galvanizado_es_incoherente():
    codigos = [m.codigo for m in comprobar(
        _linea(material="LATON", acabado="GALVANIZADO EN CALIENTE"), TODAS_ACTIVAS)]
    assert "MATERIAL_NO_ADMITE_ZINC" in codigos


def test_inox_pavonado_no_es_incoherencia():
    """INOX con PAVONADO es válido (pavonado no es zinc)."""
    codigos = [m.codigo for m in comprobar(
        _linea(material="INOX", acabado="PAVONADO"), TODAS_ACTIVAS)]
    assert "INOX_CON_ACABADO_ZINC" not in codigos
    assert "MATERIAL_NO_ADMITE_ZINC" not in codigos


def test_tuerca_con_longitud_es_nota_informativa():
    motivos = comprobar(_linea(nombre="TUERCA", longitud="30"), TODAS_ACTIVAS)
    codigos = [m.codigo for m in motivos]
    assert "LONGITUD_INESPERADA" in codigos


def test_arandela_con_longitud_es_nota_informativa():
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="ARANDELA", longitud="5"), TODAS_ACTIVAS)]
    assert "LONGITUD_INESPERADA" in codigos


def test_tornillo_con_longitud_no_es_incoherencia():
    """TORNILLO con longitud es válido."""
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="TORNILLO", longitud="20"), TODAS_ACTIVAS)]
    assert "LONGITUD_INESPERADA" not in codigos


def test_tornillo_m20_corto_es_imposible():
    """Un tornillo M20 más corto que el diámetro es imposible."""
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="TORNILLO", medida="M20", longitud="10"), TODAS_ACTIVAS)]
    assert "LONGITUD_IMPOSIBLE" in codigos


def test_tornillo_m20_largo_es_valido():
    """Un tornillo M20 de 60 mm es válido."""
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="TORNILLO", medida="M20", longitud="60"), TODAS_ACTIVAS)]
    assert "LONGITUD_IMPOSIBLE" not in codigos


# --------------------------------------------------------------------------
# Guardian de los MENSAJES, no de las reglas. Encontrado en el repaso final:
# INOX_CON_ACABADO_ZINC cerraba la f-string antes de tiempo y le ensenaba al
# comprador el texto literal "{acabado.lower()}" como motivo de revision.
# El motivo es la mitad util de una revision; uno roto la inutiliza.
# --------------------------------------------------------------------------

def _linea(**celdas):
    linea = LineaSalida.vacia(id="L1", fila_origen=1, cantidad=1)
    for atributo, valor in celdas.items():
        setattr(linea, atributo, Valor(valor=valor, literal=valor, span=(0, len(valor)),
                                       procedencia=Procedencia.EXTRAIDO))
    return linea


# Cada entrada dispara una comprobacion distinta. No estan todas, pero si las
# que construyen su mensaje interpolando valores, que son las que pueden
# romperse de esta forma.
CASOS_QUE_DISPARAN = [
    {"nombre": "TORNILLO", "calidad": "8"},                                  # solo tuerca
    {"nombre": "TORNILLO", "calidad": "200HV"},                              # solo arandela
    {"nombre": "TORNILLO", "material": "INOX", "acabado": "CINCADO"},           # inox + zinc
    {"nombre": "TORNILLO", "material": "ALUMINIO", "acabado": "CINCADO"},       # no admite zinc
    {"nombre": "TORNILLO", "norma": "ASTM A193", "medida": "M20"},              # sistema de medida
    {"nombre": "TORNILLO", "material": "INOX", "calidad": "8.8"},               # material vs calidad
    {"nombre": "ESPARRAGO", "norma": "ISO 4017"},                            # nombre vs norma
    {"nombre": "TUERCA", "longitud": "80 mm"},                               # longitud en tuerca
]


@pytest.mark.parametrize("celdas", CASOS_QUE_DISPARAN)
def test_ningun_motivo_ensena_un_marcador_sin_sustituir(celdas):
    motivos = comprobar(_linea(**celdas), TODAS_ACTIVAS)
    assert motivos, f"el caso {celdas} deberia disparar alguna coherencia"
    for motivo in motivos:
        assert "{" not in motivo.texto, f"{motivo.codigo} deja un marcador sin sustituir: {motivo.texto}"
        assert "}" not in motivo.texto, f"{motivo.codigo} deja un marcador sin sustituir: {motivo.texto}"


def test_el_mensaje_del_inox_nombra_el_acabado_de_verdad():
    """La regresion concreta: antes decia '{acabado.lower()}' en vez de 'cincado'."""
    motivos = comprobar(_linea(nombre="TORNILLO", material="INOX", acabado="CINCADO"), TODAS_ACTIVAS)
    texto = next(m.texto for m in motivos if m.codigo == "INOX_CON_ACABADO_ZINC")
    assert "cincado" in texto
    assert "acabado.lower" not in texto
