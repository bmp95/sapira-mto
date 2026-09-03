"""Ablaciones: que le pasa al KPI si quito cada pieza.

La pregunta del enunciado es literal: "de cada uno: que hace, por que existe, y
que le pasa al KPI si lo quitas. Si no sabes que pasa si lo quitas, no sabes por
que esta". Esto lo responde midiendo, no opinando.

Dos bloques, y el segundo existe porque el primero no basta:

  POLITICAS Y COHERENCIAS sobre el MTO del cliente. Deterministas y gratis: el
  segmentador va de guion, asi que el numero es reproducible sin red ni clave.

  CORPUS DE ESTRES (--estres). El MTO del cliente es coherente, asi que apagar
  las coherencias no le mueve ni una linea -- y de ahi se sacaria la conclusion
  falsa de que no sirven. Su valor solo se ve contra texto que si se contradice.
  Ese bloque necesita modelo real porque son 55 textos que ningun guion cubre.

Uso:
    python -m evaluacion.ablaciones              # solo lo determinista
    python -m evaluacion.ablaciones --estres     # tambien el corpus (con red)
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import openpyxl

from datos.corpus_estres import CASOS
from datos.guion_falso import puerto_de_guion
from motor.coherencias import TODAS_ACTIVAS
from motor.modelos import Estado, Procedencia
from motor.pipeline import POLITICAS_POR_DEFECTO, contar_fallos_de_proceso, procesar_mto
from motor.saneado import sanear

RUTA_MTO = Path("datos/MTO_tornilleria.xlsx")

# Que compra cada politica, en una linea, para que la tabla se lea sola.
QUE_HACE = {
    "derivar_material": "deduce el material de la calidad y de la norma",
    "columna_material_al_principal": "usa la columna MATERIAL como ultimo respaldo",
    "acabado_de_cierre_a_todo_el_set": "extiende el acabado final a todo el set",
    "longitud_imperial_sin_unidad_a_revision": "no supone milimetros en un ASTM",
    "dimensiones_en_ambito_a_revision": "detecta la pieza principal sin nombrar",
}


def _resueltas(lineas) -> int:
    return sum(1 for l in lineas if l.estado is Estado.RESUELTA)


def ablaciones_de_politicas() -> list[tuple[str, str, int, int]]:
    """Cada politica apagada de una en una, contra la linea base."""
    base = _resueltas(procesar_mto(RUTA_MTO, puerto_de_guion(), POLITICAS_POR_DEFECTO))
    filas = [("base (todas activas)", "", base, 0)]
    for nombre in POLITICAS_POR_DEFECTO:
        politicas = {**POLITICAS_POR_DEFECTO, nombre: False}
        n = _resueltas(procesar_mto(RUTA_MTO, puerto_de_guion(), politicas))
        filas.append((f"sin {nombre}", QUE_HACE.get(nombre, ""), n, n - base))
    return filas


def ablaciones_de_coherencias() -> list[tuple[str, int, int]]:
    """Las once comprobaciones apagadas de una en una, y todas a la vez."""
    base = _resueltas(procesar_mto(RUTA_MTO, puerto_de_guion(), POLITICAS_POR_DEFECTO,
                                   TODAS_ACTIVAS))
    filas = [("base (todas activas)", base, 0)]
    for nombre in TODAS_ACTIVAS:
        apagadas = {**TODAS_ACTIVAS, nombre: False}
        n = _resueltas(procesar_mto(RUTA_MTO, puerto_de_guion(), POLITICAS_POR_DEFECTO, apagadas))
        filas.append((f"sin {nombre}", n, n - base))
    todas_off = dict.fromkeys(TODAS_ACTIVAS, False)
    n = _resueltas(procesar_mto(RUTA_MTO, puerto_de_guion(), POLITICAS_POR_DEFECTO, todas_off))
    filas.append(("SIN NINGUNA coherencia", n, n - base))
    return filas


# --------------------------------------------------------------------------
# Corpus de estres: la pregunta no es "acierta?" sino "falla del lado seguro?"
# --------------------------------------------------------------------------

def _xlsx_del_corpus(destino: Path) -> None:
    """El corpus vive como lista de textos; el pipeline lee un xlsx con la
    cabecera en la fila 4 y los datos desde la 5 (motor/lectura_mto.py)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MTO"
    ws.append(["CORPUS DE ESTRES"])
    ws.append([])
    ws.append([])
    ws.append(["ITEM", "DESCRIPCION", "MATERIAL", "MEDIDA", "CANT.", "UD"])
    for i, (_, texto, _) in enumerate(CASOS, start=1):
        ws.append([i, texto, "", "", 10, "uds"])
    wb.save(destino)


def _valor_rastreable(celda, texto: str) -> bool:
    """Un valor es rastreable si esta LITERALMENTE en el texto de origen, o si
    lo produjo una regla nombrada. Lo demas seria una invencion."""
    if celda.valor is None:
        return True
    if celda.procedencia in (Procedencia.DERIVADO, Procedencia.HEREDADO):
        return bool(celda.regla)
    # Se compara contra el texto SANEADO, que es el que vio el pipeline, no
    # contra el crudo del corpus. Comparar con el crudo marcaba como invencion
    # justo lo que el saneado arregla: 7/8" (prima doble a comilla recta) y los
    # espacios multiples de "DIN   933". Es el mismo error que ya se colo una
    # vez midiendo el blind set -- buscar el valor normalizado en texto crudo.
    #
    # Y se comprueba el LITERAL, que es lo que se leyo, no el valor, que es lo
    # que significa: el catalogo normaliza a proposito (ZINCADO -> CINCADO,
    # DIN 933 -> ISO 4017) y eso no es inventar.
    return bool(celda.literal) and celda.literal.upper() in sanear(texto).upper()


def corpus_de_estres(puerto) -> dict:
    """Tres preguntas distintas, que antes estaban mezcladas en una:

      INVENCION      un celada con un valor que no se puede rastrear al texto.
                     Es el unico fallo que cuesta 50.000 euros.
      HUECO SILENCIOSO  el texto SI dice algo (un acabado, una norma) que el
                     sistema no reconoce, lo descarta, y la linea se resuelve
                     igual porque ese atributo no es obligatorio. No es una
                     invencion, pero es un escape: se compra sin el acabado.
      HUECO RESPETADO   el sistema deja el hueco y manda a revision. Correcto.
    """
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "estres.xlsx"
        _xlsx_del_corpus(ruta)
        lineas = procesar_mto(ruta, puerto, POLITICAS_POR_DEFECTO)

    por_fila: dict[int, list] = {}
    for linea in lineas:
        por_fila.setdefault(linea.fila_origen, []).append(linea)

    r = {"total": len(CASOS), "ok_resueltos": 0, "ok_en_revision": 0,
         "huecos_respetados": 0, "invenciones": [], "huecos_silenciosos": []}
    for i, (categoria, texto, esperado) in enumerate(CASOS, start=1):
        del_caso = por_fila.get(i, [])
        resuelto = any(l.estado is Estado.RESUELTA for l in del_caso)

        for linea in del_caso:
            for nombre, celda in linea.celdas().items():
                if not _valor_rastreable(celda, texto):
                    r["invenciones"].append((i, nombre, celda.valor, texto))

        if esperado == "HUECO":
            if resuelto:
                r["huecos_silenciosos"].append((i, categoria, texto))
            else:
                r["huecos_respetados"] += 1
        elif resuelto:
            r["ok_resueltos"] += 1
        else:
            r["ok_en_revision"] += 1
    return r


# --------------------------------------------------------------------------
# Comparativa de modelos
# --------------------------------------------------------------------------

def comparar_modelos(modelos=("gemini-3.7-flash", "gemini-3.5-flash-lite")) -> list[dict]:
    """Mismo MTO, mismo codigo, distinto modelo.

    Se compara por calidad, tokens y latencia. El COSTE solo se da para los
    modelos con precio en `TABLA_PRECIOS_POR_DEFECTO`, que hoy es uno: el pliego
    dio precio de 3.7-flash y no del ligero. Poner aqui una cifra sacada de la
    memoria seria justo lo que el sistema no hace con los datos del cliente.
    """
    from motor.puerto_gemini import PuertoGemini
    filas = []
    for modelo in modelos:
        # Cada modelo con su cache VACIA. Con la cache del repo, el modelo que
        # ya se ha usado sale con 0 tokens, 0 segundos y 0 $, y la tabla dice
        # que es gratis e instantaneo. Comparar una ejecucion cacheada contra
        # una en vivo no es una comparativa: es un artefacto de medida.
        with tempfile.TemporaryDirectory() as cache_vacia:
            puerto = PuertoGemini(modelo=modelo, directorio_cache=Path(cache_vacia))
            inicio = time.monotonic()
            lineas = procesar_mto(RUTA_MTO, puerto, POLITICAS_POR_DEFECTO)
            segundos = time.monotonic() - inicio
            try:
                coste = f"{puerto.coste_estimado():.5f} $"
            except ValueError:
                coste = "sin precio publicado"
            filas.append({
                "modelo": modelo,
                "resueltas": f"{_resueltas(lineas)}/{len(lineas)}",
                "fallos": contar_fallos_de_proceso(lineas),
                "tokens": puerto.tokens_prompt_acumulados + puerto.tokens_candidatos_acumulados,
                "segundos": f"{segundos:.1f}",
                "coste": coste,
            })
    return filas


# --------------------------------------------------------------------------
# Salida en markdown, lista para pegar en el one-pager
# --------------------------------------------------------------------------

def _tabla(cabeceras: list[str], filas: list[tuple]) -> str:
    lineas = ["| " + " | ".join(cabeceras) + " |",
              "|" + "|".join("---" for _ in cabeceras) + "|"]
    for fila in filas:
        lineas.append("| " + " | ".join(str(c) for c in fila) + " |")
    return "\n".join(lineas)


def _delta(d: int) -> str:
    return "0" if d == 0 else f"{d:+d}"


def informe(con_estres: bool = False) -> str:
    partes = ["## Ablaciones sobre el MTO del cliente (30 lineas)", ""]

    politicas = ablaciones_de_politicas()
    partes.append(_tabla(["Configuracion", "Que compra", "Resueltas", "Delta"],
                         [(n, q, f"{r}/30", _delta(d)) for n, q, r, d in politicas]))
    partes += ["", "## Ablaciones de coherencias sobre el mismo MTO", ""]

    coherencias = ablaciones_de_coherencias()
    partes.append(_tabla(["Configuracion", "Resueltas", "Delta"],
                         [(n, f"{r}/30", _delta(d)) for n, r, d in coherencias]))

    # La tabla parece contradecirse -- apagar un interruptor pierde una linea y
    # apagarlos TODOS no -- asi que la interaccion se explica, no se deja suelta.
    solo_esparrago = next((d for n, _, d in coherencias
                           if n == "sin esparrago_equivale_a_varilla"), 0)
    todas = next((d for n, _, d in coherencias if n.startswith("SIN NINGUNA")), 0)
    if solo_esparrago < 0 and todas == 0:
        partes += ["",
                   "**Por que apagar un solo interruptor pierde una linea y apagarlos todos no.** "
                   "`esparrago_equivale_a_varilla` no es una comprobacion: es un SUPRESOR de "
                   "`nombre_vs_norma` para ese par concreto. La linea L022 dice `Conjunto "
                   "esparrago M20 x 200 DIN 975`, y DIN 975 es varilla roscada. Con el supresor "
                   "apagado salta NOMBRE_CONTRADICE_NORMA y la linea va a revision; con TODAS "
                   "apagadas, `nombre_vs_norma` tampoco corre y no hay nada que saltar.", "",
                   "Eso le pone precio a una pregunta abierta para el cliente: **si esparrago y "
                   "varilla roscada son una referencia o dos en su maestro vale exactamente una "
                   "linea de treinta.** No es una decision que pueda tomar yo."]

    sin_efecto = [n for n, _, d in coherencias
                  if d == 0 and n.startswith("sin") and "esparrago" not in n]
    if len(sin_efecto) >= len(TODAS_ACTIVAS) - 1:
        partes += ["",
                   "**Ninguna coherencia mueve el numero en este MTO, y eso NO significa que "
                   "sobren.** Significa que el MTO del cliente es coherente consigo mismo: no "
                   "hay ni una fila donde dos atributos escritos se contradigan. Lo que compran "
                   "las coherencias solo se ve contra texto que si se contradice, y para eso "
                   "esta el corpus de estres."]

    if con_estres:
        from motor.puerto_gemini import PuertoGemini
        r = corpus_de_estres(PuertoGemini())
        partes += ["", f"## Corpus de estres ({r['total']} filas que el MTO nunca toca)", "",
                   _tabla(["Resultado", "Filas"], [
                       ("Casos correctos resueltos", r["ok_resueltos"]),
                       ("Casos correctos que fueron a revision", r["ok_en_revision"]),
                       ("Huecos respetados (deja vacio y manda a revision)", r["huecos_respetados"]),
                       ("Huecos silenciosos (resuelve descartando lo que no conoce)",
                        len(r["huecos_silenciosos"])),
                       ("**Invenciones** (celda con valor no rastreable)",
                        f"**{len(r['invenciones'])}**"),
                   ])]
        if r["invenciones"]:
            partes += ["", "**Invenciones detectadas:**"]
            partes += [f"- fila {i}, `{a}` = `{v}` sobre `{tx}`" for i, a, v, tx in r["invenciones"]]
        if r["huecos_silenciosos"]:
            partes += ["", "**Huecos silenciosos.** El texto dice algo que el sistema no reconoce, "
                           "lo descarta, y la linea se resuelve igual porque ese atributo no es "
                           "obligatorio. No inventa nada, pero se compra sin ello:"]
            partes += [f"- fila {i} ({c}): `{tx}`" for i, c, tx in r["huecos_silenciosos"]]
    if con_estres:
        partes += ["", "## Comparativa de modelos sobre el MTO del cliente", "",
                   _tabla(["Modelo", "Resueltas", "Fallos", "Tokens", "Segundos", "Coste"],
                          [(f["modelo"], f["resueltas"], f["fallos"], f["tokens"],
                            f["segundos"], f["coste"]) for f in comparar_modelos()]),
                   "",
                   "El coste solo aparece para el modelo cuyo precio dio el pliego. Para el "
                   "ligero no pongo cifra: no tengo un precio publicado que citar, y estimarlo "
                   "de memoria seria inventar un dato con aspecto de medido."]

    return "\n".join(partes)


DESTINO = Path("docs/metricas.md")

if __name__ == "__main__":
    texto = informe(con_estres="--estres" in sys.argv)
    # A fichero y en UTF-8 a proposito: el informe lleva simbolos de pulgada
    # (1-1/4") que la consola cp1252 de Windows no sabe imprimir, y no tiene
    # sentido perder el informe entero por como esta configurada una terminal.
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(texto, encoding="utf-8")
    print(f"Informe escrito en {DESTINO}")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print()
    print(texto)
