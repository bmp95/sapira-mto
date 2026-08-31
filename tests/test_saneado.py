from motor.saneado import sanear


def test_comillas_tipograficas_y_prima_a_recta():
    assert sanear('7/8″ X 130') == '7/8" X 130'
    assert sanear('“7/8”') == '"7/8"'


def test_colapsa_espacios():
    assert sanear("BOLT   DIN  933") == "BOLT DIN 933"


def test_forma_canonica_de_norma():
    assert sanear("BOLT DIN931 M20") == "BOLT DIN 931 M20"
    assert sanear("BOLT DIN-931 M20") == "BOLT DIN 931 M20"
    assert sanear("BOLT DIN 931 M20") == "BOLT DIN 931 M20"


def test_no_toca_el_resto():
    t = 'STUD BOLT 7/8" X 130 LG, ASTM A193, GR B7'
    assert sanear(t) == t


def test_el_fichero_fuente_no_perdio_ningun_codepoint():
    """Verifica que motor/saneado.py contiene los codepoints no-ASCII necesarios."""
    from pathlib import Path
    
    ruta = Path("motor/saneado.py")
    contenido = ruta.read_text(encoding="utf-8")
    
    # Codepoints que _COMILLAS necesita como claves
    codepoints_requeridos = {
        0x201c,  # comilla curva doble de apertura
        0x201d,  # comilla curva doble de cierre
        0x2033,  # doble prima
        0x2032,  # prima simple
        0x2018,  # comilla curva simple de apertura
        0x2019,  # comilla curva simple de cierre
        0x00b4,  # acento agudo
    }
    
    # Extrae codepoints no-ASCII del archivo
    codepoints_presentes = set(ord(c) for c in contenido if ord(c) > 127)
    
    # Verifica que están todos los requeridos
    assert codepoints_requeridos <= codepoints_presentes, \
        f"Faltan codepoints: {codepoints_requeridos - codepoints_presentes}"
