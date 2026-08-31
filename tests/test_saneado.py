from motor.saneado import sanear


def test_comillas_tipograficas_y_prima_a_recta():
    assert sanear('7/8″ X 130') == '7/8" X 130'
    assert sanear('"7/8"') == '"7/8"'


def test_colapsa_espacios():
    assert sanear("BOLT   DIN  933") == "BOLT DIN 933"


def test_forma_canonica_de_norma():
    assert sanear("BOLT DIN931 M20") == "BOLT DIN 931 M20"
    assert sanear("BOLT DIN-931 M20") == "BOLT DIN 931 M20"
    assert sanear("BOLT DIN 931 M20") == "BOLT DIN 931 M20"


def test_no_toca_el_resto():
    t = 'STUD BOLT 7/8" X 130 LG, ASTM A193, GR B7'
    assert sanear(t) == t
