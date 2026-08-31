"""Etapa 1. Un MTO de un estudio externo no viene en ASCII limpio."""
import re
import unicodedata

_COMILLAS = {
    '“': '"',  # '“'
    '”': '"',  # '”'
    '″': '"',  # '″'
    '′′': '"',  # '′′'
    '′': "'",  # '′'
    '‘': "'",  # '‘'
    '’': "'",  # '’'
    '´': "'",  # '´'
}
_NORMA = re.compile(r"\b(DIN|ISO|ASME|ASTM|EN|MSS)[\s\-]*((?:SP[\s\-]*)?\d[\w\-]*)", re.I)


def sanear(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto)
    for malo, bueno in _COMILLAS.items():
        t = t.replace(malo, bueno)
    t = t.replace("'Ø'", "DIA ")
    t = _NORMA.sub(lambda m: f"{m.group(1).upper()} {m.group(2).upper()}", t)
    return re.sub(r"\s+", " ", t).strip()
