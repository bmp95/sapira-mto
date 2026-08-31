from motor.catalogos import emparejar, ACABADOS, CALIDADES_ALIAS, NORMAS_DIN_ISO, normalizar_norma


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
