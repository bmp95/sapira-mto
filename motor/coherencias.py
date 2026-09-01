"""Conocimiento de dominio que las reglas NO contienen. Cada una con interruptor.

Se declaran como aporte propio. Si el cliente dice 'nosotros a veces cincamos inox',
se apaga la suya y se dice.
"""
from motor.modelos import LineaSalida, Motivo
from motor.derivaciones import material_de_calidad, material_de_norma, nombre_de_norma
from motor.catalogos import MATERIALES

TODAS_ACTIVAS = {
    "calidad_solo_tuerca": True, "calidad_solo_arandela": True,
    "inox_acabado": True, "sistema_medida": True, "grado_astm_nombre": True,
    "material_vs_calidad": True, "material_vs_norma": True, "nombre_vs_norma": True,
    "material_vs_acabado": True, "longitud_tuerca_arandela": True, "longitud_medida": True,
    "esparrago_equivale_a_varilla": True,
}

_INOX = {"A2", "A2-70", "A2-80", "18-8", "304", "A4", "A4-70", "A4-80", "316"}
_ZINC = {"CINCADO", "GALVANIZADO EN CALIENTE", "BICROMATADO"}
_NO_ZINC = {"ALUMINIO", "LATON", "BRONCE"}
_NOMBRES_ESPERADOS = {"TORNILLO", "TUERCA", "ARANDELA", "ESPARRAGO", "VARILLA ROSCADA"}


def _v(linea, atributo):
    return (getattr(linea, atributo).valor or "").upper()


def comprobar(linea: LineaSalida, interruptores: dict[str, bool]) -> list[Motivo]:
    motivos: list[Motivo] = []
    nombre, calidad = _v(linea, "nombre"), _v(linea, "calidad")
    acabado, norma, medida = _v(linea, "acabado"), _v(linea, "norma"), _v(linea, "medida")
    material, longitud = _v(linea, "material"), _v(linea, "longitud")

    if interruptores.get("calidad_solo_tuerca") and calidad in {"8", "10"} and nombre and nombre != "TUERCA":
        motivos.append(Motivo(codigo="CALIDAD_SOLO_TUERCA", atributo="calidad",
                              texto=f"La calidad {calidad} s{chr(0xf3)}lo aplica a tuercas (§5) y esto es {nombre}."))

    if interruptores.get("calidad_solo_arandela") and calidad.endswith("HV") and nombre and nombre != "ARANDELA":
        motivos.append(Motivo(codigo="CALIDAD_SOLO_ARANDELA", atributo="calidad",
                              texto=f"Las clases HV son durezas de arandela y esto es {nombre}."))

    if interruptores.get("inox_acabado") and calidad in _INOX and acabado in _ZINC:
        _austenitico = "austen" + chr(0xed) + "tico"
        motivos.append(Motivo(codigo="INOX_CON_ACABADO_ZINC", atributo="acabado",
                              texto=f"{calidad} es inox {_austenitico}, as{chr(0xed)} que un acabado {acabado.lower()} es incoherente."))

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

    # Material vs Calidad
    if interruptores.get("material_vs_calidad") and material and calidad:
        mat_calidad = material_de_calidad(calidad)
        if mat_calidad:
            mat_esperado, _ = mat_calidad
            if material != mat_esperado:
                motivos.append(Motivo(codigo="MATERIAL_CONTRADICE_CALIDAD", atributo="material",
                                      texto=f"La calidad {calidad} implica material {mat_esperado}, pero se indica {material}."))

    # Material vs Norma
    if interruptores.get("material_vs_norma") and material and norma:
        mat_norma = material_de_norma(norma)
        if mat_norma:
            mat_esperado, _ = mat_norma
            if material != mat_esperado:
                motivos.append(Motivo(codigo="MATERIAL_CONTRADICE_NORMA", atributo="material",
                                      texto=f"La norma {norma} implica material {mat_esperado}, pero se indica {material}."))

    # Nombre vs Norma
    if interruptores.get("nombre_vs_norma") and nombre and norma:
        nom_norma = nombre_de_norma(norma)
        if nom_norma:
            nom_esperado, _ = nom_norma
            if nombre != nom_esperado:
                # ESPARRAGO y VARILLA ROSCADA son equivalentes en el oficio
                es_equivalencia = (
                    interruptores.get("esparrago_equivale_a_varilla") and
                    {nombre, nom_esperado} == {"ESPARRAGO", "VARILLA ROSCADA"}
                )
                if es_equivalencia:
                    motivos.append(Motivo(codigo="NOMBRE_Y_NORMA_EQUIVALENTES",
                                          texto=f"La norma {norma} sugiere {nom_esperado}, pero se indica {nombre} — equivalentes en el oficio."))
                else:
                    motivos.append(Motivo(codigo="NOMBRE_CONTRADICE_NORMA", atributo="nombre",
                                          texto=f"La norma {norma} implica nombre {nom_esperado}, pero se indica {nombre}."))

    # Material vs Acabado (generaliza inox_acabado)
    if interruptores.get("material_vs_acabado"):
        if material == "INOX" and acabado in _ZINC:
            _austenitico = "austen" + chr(0xed) + "tico"
            motivos.append(Motivo(codigo="INOX_CON_ACABADO_ZINC", atributo="acabado",
                                  texto=f"{material} es inox {_austenitico}, as" + chr(0xed) + " que un acabado {acabado.lower()} es incoherente."))
        elif material in _NO_ZINC and acabado in _ZINC:
            motivos.append(Motivo(codigo="MATERIAL_NO_ADMITE_ZINC", atributo="acabado",
                                  texto=f"{material} no admite recubrimiento de zinc; {acabado.lower()} es incoherente."))

    # Longitud en tuerca o arandela
    if interruptores.get("longitud_tuerca_arandela") and longitud and nombre in {"TUERCA", "ARANDELA"}:
        motivos.append(Motivo(codigo="LONGITUD_INESPERADA", atributo="longitud",
                              texto=f"La longitud no aplica a {nombre.lower()}; este dato es inesperado."))

    # Longitud menor que medida
    if interruptores.get("longitud_medida") and longitud and medida:
        try:
            if medida.startswith("M"):
                # Medida métrica: extraer el número
                medida_num = float(medida[1:])
                longitud_num = float(longitud)
                if longitud_num < medida_num:
                    motivos.append(Motivo(codigo="LONGITUD_IMPOSIBLE", atributo="longitud",
                                          texto=f"Un tornillo {medida} ({medida_num} mm) no puede medir {longitud_num} mm."))
        except (ValueError, IndexError):
            # Si no podemos parsear, no disparamos (prudencia)
            pass

    return motivos
