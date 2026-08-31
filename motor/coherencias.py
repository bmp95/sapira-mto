"""Conocimiento de dominio que las reglas NO contienen. Cada una con interruptor.

Se declaran como aporte propio. Si el cliente dice 'nosotros a veces cincamos inox',
se apaga la suya y se dice.
"""
from motor.modelos import LineaSalida, Motivo

TODAS_ACTIVAS = {
    "calidad_solo_tuerca": True, "calidad_solo_arandela": True,
    "inox_acabado": True, "sistema_medida": True, "grado_astm_nombre": True,
}

_INOX = {"A2", "A2-70", "A2-80", "18-8", "304", "A4", "A4-70", "A4-80", "316"}
_ZINC = {"CINCADO", "GALVANIZADO EN CALIENTE", "BICROMATADO"}


def _v(linea, atributo):
    return (getattr(linea, atributo).valor or "").upper()


def comprobar(linea: LineaSalida, interruptores: dict[str, bool]) -> list[Motivo]:
    motivos: list[Motivo] = []
    nombre, calidad = _v(linea, "nombre"), _v(linea, "calidad")
    acabado, norma, medida = _v(linea, "acabado"), _v(linea, "norma"), _v(linea, "medida")

    if interruptores.get("calidad_solo_tuerca") and calidad in {"8", "10"} and nombre and nombre != "TUERCA":
        motivos.append(Motivo(codigo="CALIDAD_SOLO_TUERCA", atributo="calidad",
                              texto=f"La calidad {calidad} s{chr(0xf3)}lo aplica a tuercas (§5) y esto es {nombre}."))

    if interruptores.get("calidad_solo_arandela") and calidad.endswith("HV") and nombre and nombre != "ARANDELA":
        motivos.append(Motivo(codigo="CALIDAD_SOLO_ARANDELA", atributo="calidad",
                              texto=f"Las clases HV son durezas de arandela y esto es {nombre}."))

    if interruptores.get("inox_acabado") and calidad in _INOX and acabado in _ZINC:
        motivos.append(Motivo(codigo="INOX_CON_ACABADO_ZINC", atributo="acabado",
                              texto=f"{calidad} es inox austenít{chr(0xed)}co y no se {acabado.lower()}."))

    if interruptores.get("sistema_medida") and norma and medida:
        imperial_norma = norma.startswith(("ASTM", "ASME", "MSS"))
        metrica_medida = medida.upper().startswith("M")
        if imperial_norma and metrica_medida:
            motivos.append(Motivo(codigo="SISTEMA_MEDIDA_INCOHERENTE", atributo="medida",
                                  texto=f"{norma} es norma imperial y la medida {medida} es m{chr(0xe9)}trica."))
        if norma.startswith(("DIN", "ISO", "EN")) and '"' in medida:
            motivos.append(Motivo(codigo="SISTEMA_MEDIDA_INCOHERENTE", atributo="medida",
                                  texto=f"{norma} es norma m{chr(0xe9)}trica y la medida {medida} es imperial."))

    if interruptores.get("grado_astm_nombre") and nombre:
        if calidad in {"GR 2H", "2H"} and nombre != "TUERCA":
            motivos.append(Motivo(codigo="GRADO_ASTM_INCOHERENTE", atributo="calidad",
                                  texto="GR 2H es ASTM A194, norma de tuercas."))
        if calidad in {"GR B7", "B7"} and nombre not in {"TORNILLO", "ESPARRAGO"}:
            motivos.append(Motivo(codigo="GRADO_ASTM_INCOHERENTE", atributo="calidad",
                                  texto="GR B7 es ASTM A193, norma de torniller" + chr(0xed) + "a."))
    return motivos
