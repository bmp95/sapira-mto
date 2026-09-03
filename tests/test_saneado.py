from motor.saneado import _COMILLAS, sanear


def test_comillas_tipograficas_y_prima_a_recta():
    assert sanear('7/8' + chr(0x2033) + ' X 130') == '7/8" X 130'
    assert sanear(chr(0x201c) + '7/8' + chr(0x201d)) == '"7/8"'


def test_colapsa_espacios():
    assert sanear("BOLT   DIN  933") == "BOLT DIN 933"


def test_forma_canonica_de_norma():
    assert sanear("BOLT DIN931 M20") == "BOLT DIN 931 M20"
    assert sanear("BOLT DIN-931 M20") == "BOLT DIN 931 M20"
    assert sanear("BOLT DIN 931 M20") == "BOLT DIN 931 M20"


def test_no_toca_el_resto():
    t = 'STUD BOLT 7/8" X 130 LG, ASTM A193, GR B7'
    assert sanear(t) == t


def test_simbolo_de_diametro_a_dia():
    """Verifica que el símbolo de diámetro se convierte a 'DIA '."""
    # El símbolo Ø se reemplaza con "DIA ", que colapsará espacios
    assert sanear('50' + chr(0x00d8) + ' mm') == '50DIA mm'
    assert sanear(chr(0x00d8)) == 'DIA'


def test_comillas_curvas_siguen_en_el_diccionario():
    """Valida que el diccionario en tiempo de ejecución tiene las entradas correctas
    y que sanear realmente las convierte."""
    esperado = {
        chr(0x201c): '"', chr(0x201d): '"', chr(0x2033): '"',
        chr(0x2032) + chr(0x2032): '"', chr(0x2032): "'",
        chr(0x2018): "'", chr(0x2019): "'", 
        chr(0x00b4): "'",  # acento agudo sin normalizar
        chr(0x0301): "'",  # combining acute (resultado de NFKC)
    }
    # Verificar que el diccionario contiene todas las entradas esperadas
    assert esperado.items() <= _COMILLAS.items(), \
        f"Faltan entradas: {set(esperado.items()) - set(_COMILLAS.items())}"

    # Verificar que cada entrada funciona en sanear
    for malo, bueno in esperado.items():
        resultado = sanear(malo).strip()  # strip porque NFKC puede agregar espacios
        assert resultado == bueno, \
            f"sanear({malo!r}) devolvió {resultado!r}, esperaba {bueno!r}"
