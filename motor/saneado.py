"""Etapa 1. Un MTO de un estudio externo no viene en ASCII limpio."""
import re
import unicodedata

_COMILLAS = {
    chr(0x201c): '"',  # comilla curva doble de apertura
    chr(0x201d): '"',  # comilla curva doble de cierre
    chr(0x2033): '"',  # doble prima
    chr(0x2032) + chr(0x2032): '"',  # doble prima simple (resultado de NFKC)
    chr(0x2032): "'",  # prima simple
    chr(0x2018): "'",  # comilla curva simple de apertura
    chr(0x2019): "'",  # comilla curva simple de cierre
    chr(0x00b4): "'",  # acento agudo (sin normalizar)
    chr(0x0301): "'",  # combining acute accent (resultado de NFKC sobre U+00B4)
}
_NORMA = re.compile(r"\b(DIN|ISO|ASME|ASTM|EN|MSS)[\s\-]*((?:SP[\s\-]*)?\d[\w\-]*)", re.I)


def sanear(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto)
    for malo, bueno in _COMILLAS.items():
        t = t.replace(malo, bueno)
    t = t.replace(chr(0x00d8), "DIA ")  # reemplaza símbolo de diámetro
    t = _NORMA.sub(lambda m: f"{m.group(1).upper()} {m.group(2).upper()}", t)
    return re.sub(r"\s+", " ", t).strip()
