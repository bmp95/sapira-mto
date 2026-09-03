from motor.catalogos import ACABADOS, CALIDADES_ALIAS, GRUPOS_CALIDAD, emparejar, normalizar_norma
from motor.saneado import sanear


def test_BL_no_casa_dentro_de_AUTOBLOCANTE():
    """DIN 985 es tuerca autoblocante. 'BL' es alias de PAVONADO."""
    t = "TUERCA AUTOBLOCANTE DIN 985 M12, 8.8, ZINCADA"
    hallados = {v for v, _, _ in emparejar(t, ACABADOS)}
    assert hallados == {"CINCADO"}


def test_ZP_no_se_come_YZP():
    assert {v for v, _, _ in emparejar("TORNILLO M10 YZP", ACABADOS)} == {"BICROMATADO"}
    assert {v for v, _, _ in emparejar("TORNILLO M10 ZP", ACABADOS)} == {"CINCADO"}


def test_calidad_10_no_sale_de_M10():
    t = "ARANDELA PLANA DIN 125 M10, ACERO, ZINCADA"
    assert emparejar(t, CALIDADES_ALIAS) == []


def test_calidad_8_no_sale_de_8_8():
    hallados = [v for v, _, _ in emparejar("TORNILLO DIN 933 M10 X 40, 8.8", CALIDADES_ALIAS)]
    assert hallados == ["8.8"]


def test_A4_70_gana_a_A4():
    t = "BOLT DIN 931 M12X60 A4-70 WITH NUT DIN 934 M12 A4-80"
    assert [v for v, _, _ in emparejar(t, CALIDADES_ALIAS)] == ["A4-70", "A4-80"]


def test_normalizacion_de_norma():
    assert normalizar_norma("DIN 933") == "ISO 4017"
    assert normalizar_norma("DIN 125 A") == "ISO 7089"
    assert normalizar_norma("DIN 975") == "DIN 975"   # sin equivalente: se conserva
    assert normalizar_norma("ASTM A193") == "ASTM A193"


def test_no_hay_coincidencia_difusa():
    assert normalizar_norma("DIN 9331") == "DIN 9331"  # NO es DIN 933


def test_calidad_8_no_sale_de_fraccion_5_8():
    t = 'STUD BOLT 5/8" X 4-1/2" LG'
    assert emparejar(t, CALIDADES_ALIAS) == []


def test_calidad_8_no_sale_de_fraccion_7_8():
    t = 'STUD BOLT 7/8" X 130 LG, ASTM A193, GR B7'
    assert "8" not in {v for v, _, _ in emparejar(t, CALIDADES_ALIAS)}


def test_calidad_10_no_sale_de_DIA_10():
    t = "Tornillo DIN 933 DIA 10 x 40, 8.8"
    assert [v for v, _, _ in emparejar(t, CALIDADES_ALIAS)] == ["8.8"]


def test_calidad_8_desnuda_en_posicion_de_calidad_si_se_extrae():
    t = "Tuerca DIN 6923 M10, 8, bicromatada"
    assert [v for v, _, _ in emparejar(t, CALIDADES_ALIAS)] == ["8"]


def test_calidad_10_desnuda_en_posicion_de_calidad_si_se_extrae():
    t = "Tuerca DIN EN 1661 M10, 10, cincada"
    assert [v for v, _, _ in emparejar(t, CALIDADES_ALIAS)] == ["10"]


def test_calidad_304_no_sale_de_medida_304():
    t = sanear("Tornillo DIN 933 M20 x 304, 8.8")
    assert [v for v, _, _ in emparejar(t, CALIDADES_ALIAS)] == ["8.8"]


def test_calidad_316_no_sale_de_medida_316():
    t = sanear("VARILLA ROSCADA M12 x 316 DIN 975, 8.8")
    assert [v for v, _, _ in emparejar(t, CALIDADES_ALIAS)] == ["8.8"]


def test_calidad_304_en_posicion_de_calidad_si_se_extrae():
    t = sanear("Tuerca DIN 934 M16, 304")
    assert [v for v, _, _ in emparejar(t, CALIDADES_ALIAS)] == ["304"]


def test_calidad_316_en_posicion_de_calidad_si_se_extrae():
    t = sanear("Tornillo DIN 933 M8 x 20, 316, pavonado")
    assert [v for v, _, _ in emparejar(t, CALIDADES_ALIAS)] == ["316"]


def test_todas_las_calidades_puramente_numericas_llevan_tratamiento_estricto():
    """Regla derivada del catalogo: toda clave de GRUPOS_CALIDAD formada solo por
    digitos exige posicion de calidad (precedida por coma o principio de texto,
    seguida de coma, punto o fin). Se afirma primero cuantas hay para que este
    test no pase en falso con la coleccion vacia si algun dia dejan de existir."""
    desnudas = [c for c in GRUPOS_CALIDAD if c.isdigit()]
    assert len(desnudas) == 4
    assert set(desnudas) == {"8", "10", "304", "316"}
    for clave in desnudas:
        suelta = "MEDIDA " + clave + " X ALGO"
        assert clave not in {v for v, _, _ in emparejar(suelta, CALIDADES_ALIAS)}
        legitima = "TORNILLO DIN 933 M10, " + clave + ", ACABADO"
        assert [v for v, _, _ in emparejar(legitima, CALIDADES_ALIAS)] == [clave]
