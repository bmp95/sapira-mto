"""Entailments deterministas. No es 'lo mas probable': la alternativa no existe.

8.8 pertenece a ISO 898-1, que es la norma de acero al carbono y aleado. Si la pieza
fuera inox se llamaria A4-70 bajo ISO 3506. Una calidad no puede pertenecer a los dos
sistemas de designacion, asi que la derivacion es una funcion, no una probabilidad.
"""
from typing import Optional

_MATERIAL = {
    # ISO 898-1/2 - acero al carbono y aleado
    "8.8": "AC", "10.9": "AC", "12.9": "AC",
    "GRADE 5": "AC", "GRADO 5": "AC", "GRADE 8": "AC", "GRADO 8": "AC",
    "8": "AC", "10": "AC",
    # ISO 3506 - inox austenitico
    "A2": "INOX", "A2-70": "INOX", "A2-80": "INOX", "18-8": "INOX", "304": "INOX",
    "A4": "INOX", "A4-70": "INOX", "A4-80": "INOX", "316": "INOX",
    # ISO 7089/7090 - clases de dureza de arandela de acero
    "100HV": "AC", "140HV": "AC", "160HV": "AC", "200HV": "AC", "300HV": "AC",
    # Grados ASTM
    "GR B7": "AC", "B7": "AC", "GR 2H": "AC", "2H": "AC", "ASTM F436": "AC", "F436": "AC",
}

_NOMBRE_POR_NORMA = {
    **{n: "TORNILLO" for n in ("ISO 1207", "ISO 8677", "ISO 4762", "ISO 4026", "ISO 4029",
                               "ISO 4014", "ISO 4017", "ISO 8765", "ISO 1665", "ISO 2009",
                               "ISO 7046", "ISO 7049", "ISO 7050", "ISO 7045", "ISO 10642")},
    **{n: "TUERCA" for n in ("ISO 4032", "ISO 7035", "ISO 4035", "ISO 7042", "ISO 7040",
                             "ISO 10511", "EN 1661", "ASTM A194")},
    **{n: "ARANDELA" for n in ("ISO 7089", "ISO 7093", "ISO 7094", "ASTM F436")},
    "ASTM A193": "ESPARRAGO",
    "DIN 975": "VARILLA ROSCADA",
}


def material_de_calidad(calidad: str) -> Optional[tuple[str, str]]:
    v = _MATERIAL.get(calidad.upper().strip())
    return (v, f"MAT-{calidad.upper().strip()}") if v else None


def nombre_de_norma(norma: str) -> Optional[tuple[str, str]]:
    v = _NOMBRE_POR_NORMA.get(norma.upper().strip())
    return (v, f"NOM-{norma.upper().strip()}") if v else None
