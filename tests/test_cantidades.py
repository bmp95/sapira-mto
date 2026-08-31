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
