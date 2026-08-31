"""La confianza NO la reporta el modelo: la calcula el codigo con cuatro hechos medidos.

Un '95 %' generado por un LLM es un numero inventado con aspecto de evidencia.
Aqui cada factor es una observacion, y por ser un minimo siempre hay un motivo
concreto: '67 porque la segmentacion fue 2 de 3'.

El factor 'literal' NO se aprueba porque exista un span: se aprueba porque
verificar_literal (motor/invariantes.py) confirmo que el texto bajo ese span
es, caracter a caracter, el literal declarado. Esa comprobacion vive fuera de
este modulo porque necesita el texto original de la fila; quien orquesta el
pipeline la calcula una vez por celda y la pasa aqui como literales_ok.
"""
from motor.modelos import LineaSalida, Motivo, Procedencia, Valor

PUNTOS_VOTOS = {3: 100, 2: 67, 1: 33, 0: 0}


def confianza_celda(valor: Valor, literal_ok: bool, votos: int, coherente: bool) -> tuple[int, str]:
    if valor.procedencia is Procedencia.AUSENTE:
        return 0, "ausente"
    factores = {
        "procedencia": valor.confianza_procedencia or 0,
        "literal": 100 if (literal_ok or valor.procedencia is Procedencia.DERIVADO) else 0,
        "segmentacion": PUNTOS_VOTOS.get(votos, 0),
        "coherencia": 100 if coherente else 0,
    }
    valor.factores = factores
    minimo = min(factores.values())
    limitante = "ninguno" if minimo == 100 else min(factores, key=lambda k: factores[k])
    valor.confianza = minimo
    return minimo, limitante


def aplicar_confianza(linea: LineaSalida, votos: int, motivos: list[Motivo],
                      literales_ok: dict[str, bool]) -> LineaSalida:
    atributos_incoherentes = {m.atributo for m in motivos if m.atributo}
    peor, peor_atributo, peor_factor = 100, None, "ninguno"
    evaluada = False
    for nombre, celda in linea.celdas().items():
        if celda.procedencia is Procedencia.AUSENTE:
            continue
        evaluada = True
        # Un valor DERIVADO no tiene literal en el texto que verificar: se da
        # por bueno sin consultar el diccionario. Cualquier otra procedencia
        # exige que el llamador ya haya calculado su entrada; sin ella, KeyError
        # (sin valores por defecto silenciosos).
        literal_ok = True if celda.procedencia is Procedencia.DERIVADO else literales_ok[nombre]
        c, factor = confianza_celda(celda, literal_ok, votos, nombre not in atributos_incoherentes)
        if c < peor:
            peor, peor_atributo, peor_factor = c, nombre, factor

    linea.motivos = list(motivos)

    if not evaluada:
        # LineaSalida.vacia() deja las siete celdas en AUSENTE. Sin ninguna celda
        # evaluable no hay nada que sostenga una confianza de 100: la linea es 0.
        linea.confianza = 0
        linea.motivos.append(Motivo(
            codigo="LINEA_SIN_CELDAS_EVALUABLES",
            texto="La l" + chr(0xed) + "nea no tiene ninguna celda con datos: "
                  "las siete est" + chr(0xe1) + "n ausentes.",
            factor_limitante="ausente"))
        return linea

    linea.confianza = peor
    if peor < 100 and not any(m.atributo == peor_atributo for m in motivos):
        linea.motivos.append(Motivo(
            codigo="CONFIANZA_INSUFICIENTE", atributo=peor_atributo,
            texto=f"La celda '{peor_atributo}' se queda en {peor} por el factor {peor_factor}.",
            factor_limitante=peor_factor))
    return linea
