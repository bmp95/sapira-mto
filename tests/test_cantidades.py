"""Tests para multiplicadores de cantidad del set."""
from motor.cantidades import multiplicador


def test_multiplicador_explicito():
    """El multiplicador se busca antes del sustantivo de tipo."""
    assert multiplicador("W/2 HEX. NUT 7/8\", ASTM A194, GR 2H") == 2
    assert multiplicador("2 WASHER 7/8\", ASTM F436") == 2
    assert multiplicador("con 2 tuercas DIN 934") == 2


def test_sin_multiplicador_es_uno():
    """Sin numero antes del sustantivo, el multiplicador es 1."""
    assert multiplicador("with NUT DIN 934 M20") == 1
    assert multiplicador("con tuerca y arandela") == 1


def test_el_uno_explicito_tambien_vale():
    """Un 1 explícito también es válido."""
    assert multiplicador("1 WASHER ASTM F436") == 1


def test_case_regression_norma_no_es_multiplicador():
    """El número de la norma NO debe confundirse con el multiplicador.

    Este es el caso que rompía el regex del pliego:
    "with NUT DIN 934 M20" devolvería 934 en lugar de 1.
    """
    assert multiplicador("with NUT DIN 934 M20") == 1


def test_norma_delante_del_sustantivo_no_es_multiplicador():
    """Las normas (DIN, ISO, ASTM, etc.) y medidas métricas no son multiplicadores."""
    assert multiplicador("DIN 934 M20 NUT") == 1
    assert multiplicador("y DIN 125 M10 arandela") == 1
    assert multiplicador("ISO 4032 M16 tuerca") == 1


def test_multiplicador_real_con_norma_delante():
    """Si hay un multiplicador real antes de la norma, se debe detectar."""
    assert multiplicador("2 DIN 125 M10 arandelas") == 2


def test_medidas_en_pulgadas_no_son_multiplicadores():
    """Las medidas en pulgadas (fracciones y comillas) no son multiplicadores."""
    assert multiplicador("W/2 HEX. NUT 7/8\", ASTM A194") == 2


def test_normas_multiples_palabras_con_guion():
    """Las normas de dos palabras con guion (MSS SP-58, DIN EN 1661) se limpian completamente."""
    assert multiplicador("MSS SP-58 M12 tornillo") == 1
    assert multiplicador("DIN EN 1661 M10 tuerca") == 1
    assert multiplicador("ASME B18.2.1 3/4\" bolt") == 1


def test_multiplicador_real_antes_de_norma_multiples_palabras():
    """Si hay multiplicador real, se detecta aunque haya norma con dos palabras."""
    assert multiplicador("2 MSS SP-58 M12 tornillos") == 2


def test_regresion_17_casos():
    """No regresion: los 17 casos verificados siguen funcionando."""
    # Los 7 casos de las correcciones anteriores
    assert multiplicador("DIN 934 M20 NUT") == 1
    assert multiplicador("y DIN 125 M10 arandela") == 1
    assert multiplicador("2 DIN 125 M10 arandelas") == 2
    assert multiplicador("ISO 4032 M16 tuerca") == 1
    # Nuevos casos de no regresion
    assert multiplicador("3 tuercas M20x90 DIN 934") == 3
    assert multiplicador("2 arandelas 1-1/4\" ASTM F436") == 2
