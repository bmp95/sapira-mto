import pytest
from motor.catalogos import GRUPOS_CALIDAD
from motor.derivaciones import material_de_calidad, nombre_de_norma


@pytest.mark.parametrize("calidad,esperado", [
    ("8.8", "AC"), ("10.9", "AC"), ("12.9", "AC"), ("GRADE 5", "AC"),
    ("8", "AC"), ("10", "AC"), ("200HV", "AC"), ("100HV", "AC"),
    ("A2", "INOX"), ("A4-70", "INOX"), ("A4-80", "INOX"), ("304", "INOX"), ("316", "INOX"),
    ("GR B7", "AC"), ("GR 2H", "AC"), ("ASTM F436", "AC"),
])
def test_material_se_deriva_de_la_calidad(calidad, esperado):
    valor, regla = material_de_calidad(calidad)
    assert valor == esperado
    assert regla.startswith("MAT-")


def test_todas_las_claves_del_catalogo_mapean():
    """Ninguna queda fuera: si una nueva entra al catalogo, este test lo caza."""
    assert len(GRUPOS_CALIDAD) == 23
    sin_mapa = [c for c in GRUPOS_CALIDAD if material_de_calidad(c) is None]
    assert sin_mapa == []


def test_calidad_desconocida_no_deriva_nada():
    assert material_de_calidad("XYZ-99") is None


@pytest.mark.parametrize("norma,esperado", [
    ("ISO 4017", "TORNILLO"), ("ISO 4762", "TORNILLO"), ("ISO 4032", "TUERCA"),
    ("ISO 10511", "TUERCA"), ("ISO 7089", "ARANDELA"), ("ISO 7094", "ARANDELA"),
    ("ASTM A193", "ESPARRAGO"), ("ASTM A194", "TUERCA"), ("ASTM F436", "ARANDELA"),
    ("DIN 975", "VARILLA ROSCADA"),
])
def test_nombre_se_deriva_de_la_norma(norma, esperado):
    valor, regla = nombre_de_norma(norma)
    assert valor == esperado
