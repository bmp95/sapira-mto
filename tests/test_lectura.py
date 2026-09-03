from pathlib import Path

from motor.lectura_mto import leer_mto


def test_lee_las_quince_filas():
    filas = leer_mto(Path("datos/MTO_tornilleria.xlsx"))
    assert len(filas) == 15
    assert filas[0].item == 1
    assert filas[0].cantidad == 40
    assert "STUD BOLT" in filas[0].descripcion


def test_la_descripcion_llega_saneada():
    filas = leer_mto(Path("datos/MTO_tornilleria.xlsx"))
    assert "DIN 931" in filas[1].descripcion  # el fichero trae "DIN931"
