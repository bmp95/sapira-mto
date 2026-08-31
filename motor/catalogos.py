"""Las cuatro tablas cerradas. Cero modelo, cero coincidencia difusa."""
import re

NORMAS_DIN_ISO = {
    "DIN 84": "ISO 1207", "DIN 440": "ISO 7094", "DIN 603": "ISO 8677",
    "DIN 912": "ISO 4762", "DIN 913": "ISO 4026", "DIN 916": "ISO 4029",
    "DIN 931": "ISO 4014", "DIN 933": "ISO 4017", "DIN 934": "ISO 4032",
    "DIN 935": "ISO 7035", "DIN 936": "ISO 4035", "DIN 960": "ISO 8765",
    "DIN 961": "ISO 1665", "DIN 963": "ISO 2009", "DIN 965": "ISO 7046",
    "DIN 980": "ISO 7042", "DIN 982": "ISO 7040", "DIN 985": "ISO 10511",
    "DIN 6923": "EN 1661", "DIN 7981 C-H": "ISO 7049", "DIN 7982 C-H": "ISO 7050",
    "DIN 7985": "ISO 7045", "DIN 7991": "ISO 10642", "DIN 9021": "ISO 7093",
    "DIN 125": "ISO 7089", "DIN 125 A": "ISO 7089",
}

GRUPOS_CALIDAD = {
    "A2": "G1", "A2-70": "G1", "18-8": "G1", "304": "G1",
    "A2-80": "G2",
    "A4": "G3", "A4-70": "G3", "316": "G3",
    "A4-80": "G4",
    "8.8": "G5", "GRADE 5": "G5", "GRADO 5": "G5",
    "10.9": "G6", "GRADE 8": "G6", "GRADO 8": "G6",
    "12.9": "G7", "8": "G8", "10": "G9",
    "100HV": "G10", "140HV": "G11", "160HV": "G12", "200HV": "G13", "300HV": "G14",
}
CALIDADES = tuple(GRUPOS_CALIDAD)
CALIDADES_ALIAS = {c: c for c in GRUPOS_CALIDAD}

ACABADOS = {
    "GEOMET": "GEOMET", "DACROMET": "DACROMET",
    "GALVANIZADO EN CALIENTE": "GALVANIZADO EN CALIENTE", "HOT DIP GALVANIZED": "GALVANIZADO EN CALIENTE",
    "HDG": "GALVANIZADO EN CALIENTE", "GALVA": "GALVANIZADO EN CALIENTE",
    "CINCADO": "CINCADO", "CINCADA": "CINCADO", "ZINCADO": "CINCADO", "ZINCADA": "CINCADO",
    "ZINC PLATED": "CINCADO", "ZN": "CINCADO", "ZP": "CINCADO",
    "PAVONADO": "PAVONADO", "BL": "PAVONADO", "NEGRO": "PAVONADO",
    "FOSFATADO": "FOSFATADO", "PHOSPHATED": "FOSFATADO",
    "BICROMATADO": "BICROMATADO", "YZP": "BICROMATADO", "YELLOW ZINC PLATED": "BICROMATADO",
}

NOMBRES = {
    "THREADED ROD": "VARILLA ROSCADA", "VARILLA ROSCADA": "VARILLA ROSCADA",
    "STUD BOLT": "ESPARRAGO", "STUD": "ESPARRAGO", "ESPARRAGO": "ESPARRAGO",
    "SCREW": "TORNILLO", "BOLT": "TORNILLO", "TORNILLO": "TORNILLO",
    "NUT": "TUERCA", "TUERCA": "TUERCA", "TUERCAS": "TUERCA",
    "WASHER": "ARANDELA", "ARANDELA": "ARANDELA", "ARANDELAS": "ARANDELA",
}

# Un token no puede estar pegado a letra, digito, punto o guion.
# Esto es lo que impide que 'BL' case dentro de AUTOBLOCANTE y que '10' salga de M10.
_ANTES = r"(?<![A-Za-z0-9.\-])"
_DESPUES = r"(?![A-Za-z0-9.\-])"


def emparejar(texto: str, tabla: dict[str, str]) -> list[tuple[str, str, tuple[int, int]]]:
    """Devuelve (valor_normalizado, literal, span). Mas largo primero; sin solapes."""
    t = texto.upper()
    hallazgos: list[tuple[str, str, tuple[int, int]]] = []
    ocupado: list[tuple[int, int]] = []
    for clave in sorted(tabla, key=len, reverse=True):
        patron = _ANTES + re.escape(clave) + _DESPUES
        for m in re.finditer(patron, t):
            ini, fin = m.span()
            if any(ini < f and i < fin for i, f in ocupado):
                continue
            ocupado.append((ini, fin))
            hallazgos.append((tabla[clave], texto[ini:fin], (ini, fin)))
    return sorted(hallazgos, key=lambda h: h[2][0])


def normalizar_norma(literal: str) -> str:
    """Exacta o se conserva. DIN 9331 NO es DIN 933."""
    return NORMAS_DIN_ISO.get(literal.upper().strip(), literal.upper().strip())
