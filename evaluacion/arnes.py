"""El arnes de evaluacion: convierte el gold set anotado a mano (Tarea 11)
y la salida del sistema (`motor.pipeline.procesar_mto`) en las metricas del
spec (`docs/superpowers/specs/2026-08-31-reconciliacion-mto-design.md`,
seccion 8).

Alineacion de lineas (la parte delicada). El gold y el sistema pueden
discrepar en CUANTAS lineas produce una fila del MTO -- eso no es un fallo
de atributo, es un fallo estructural, y ninguna metrica por atributo lo
detecta. Por eso la evaluacion agrupa primero por `fila` del MTO, compara
numero y tipos (multiset de nombres) por fila, y solo si coinciden empareja
linea a linea por nombre, en orden. Las filas que no coinciden se reportan
aparte (`fallas_segmentacion`) y sus lineas no entran en el desglose por
atributo ni en la tasa de escape: no hay con que emparejarlas.

Comparacion de valores: cero coincidencia difusa. Se normaliza (mayusculas,
espacios colapsados, None/''/N-A como el mismo hueco) y despues se compara
por igualdad exacta -- nunca por parecido.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from evaluacion.cargar_gold import ConfianzaGold, LineaGold, cargar_gold
from motor.modelos import ATRIBUTOS, Estado, LineaSalida


def _normalizar(valor: Optional[str]) -> Optional[str]:
    """Mayusculas, espacios colapsados. None, '' y N/A son el mismo hueco."""
    if valor is None:
        return None
    texto = " ".join(str(valor).split()).upper()
    if texto in ("", "N/A"):
        return None
    return texto


class MetricaAtributo(BaseModel):
    aciertos: int
    evaluables: int
    indecidibles: int


class FallaEscape(BaseModel):
    id: str
    atributo: str
    valor_gold: Optional[str]
    valor_sistema: Optional[str]


class FallaSegmentacion(BaseModel):
    fila: int
    nombres_sistema: list[Optional[str]]
    nombres_gold: list[Optional[str]]


class Metricas(BaseModel):
    total_lineas: int
    tasa_escape: float
    cobertura: float
    ruido_revision: Optional[float]
    exactitud_segmentacion: float
    celdas_indecidibles: int
    por_atributo: dict[str, MetricaAtributo]
    fallas_escape: list[FallaEscape]
    fallas_segmentacion: list[FallaSegmentacion]


def _agrupar_por_fila_sistema(lineas: list[LineaSalida]) -> dict[int, list[LineaSalida]]:
    agrupado: dict[int, list[LineaSalida]] = defaultdict(list)
    for linea in lineas:
        agrupado[linea.fila_origen].append(linea)
    return agrupado


def _agrupar_por_fila_gold(gold: list[LineaGold]) -> dict[int, list[LineaGold]]:
    agrupado: dict[int, list[LineaGold]] = defaultdict(list)
    for linea in gold:
        agrupado[linea.fila].append(linea)
    return agrupado


def _emparejar_fila(lineas_sistema: list[LineaSalida], lineas_gold: list[LineaGold]
                    ) -> Optional[list[tuple[LineaSalida, LineaGold]]]:
    """`None` si la fila es un fallo de segmentacion (numero o tipos no
    coinciden). Si no, los pares (linea_sistema, linea_gold), en orden,
    emparejados por nombre dentro de la fila."""
    nombres_sistema = [_normalizar(l.nombre.valor) for l in lineas_sistema]
    nombres_gold = [_normalizar(l.nombre) for l in lineas_gold]
    if Counter(nombres_sistema) != Counter(nombres_gold):
        return None

    por_nombre: dict[Optional[str], list[LineaSalida]] = defaultdict(list)
    for linea, nombre in zip(lineas_sistema, nombres_sistema):
        por_nombre[nombre].append(linea)

    siguiente_indice: dict[Optional[str], int] = defaultdict(int)
    pares: list[tuple[LineaSalida, LineaGold]] = []
    for linea_gold, nombre in zip(lineas_gold, nombres_gold):
        i = siguiente_indice[nombre]
        pares.append((por_nombre[nombre][i], linea_gold))
        siguiente_indice[nombre] += 1
    return pares


def evaluar(lineas: list[LineaSalida], gold: list[LineaGold]) -> Metricas:
    if not lineas:
        raise ValueError("lineas esta vacio: no hay salida del sistema que evaluar")
    if not gold:
        raise ValueError("gold esta vacio: no hay contra que evaluar")

    sistema_por_fila = _agrupar_por_fila_sistema(lineas)
    gold_por_fila = _agrupar_por_fila_gold(gold)

    fallas_segmentacion: list[FallaSegmentacion] = []
    pares: list[tuple[LineaSalida, LineaGold]] = []
    filas_alineadas = 0

    for fila in sorted(gold_por_fila):
        lineas_sistema_fila = sistema_por_fila.get(fila, [])
        lineas_gold_fila = gold_por_fila[fila]
        emparejados = _emparejar_fila(lineas_sistema_fila, lineas_gold_fila)
        if emparejados is None:
            fallas_segmentacion.append(FallaSegmentacion(
                fila=fila,
                nombres_sistema=[_normalizar(l.nombre.valor) for l in lineas_sistema_fila],
                nombres_gold=[_normalizar(l.nombre) for l in lineas_gold_fila],
            ))
            continue
        filas_alineadas += 1
        pares.extend(emparejados)

    exactitud_segmentacion = filas_alineadas / len(gold_por_fila)

    por_atributo: dict[str, MetricaAtributo] = {
        atributo: MetricaAtributo(aciertos=0, evaluables=0, indecidibles=0)
        for atributo in ATRIBUTOS
    }
    celdas_indecidibles = 0
    fallas_escape: list[FallaEscape] = []
    n_escapadas = 0
    revisiones_evaluables = 0
    revisiones_sin_ruido = 0

    for linea_sistema, linea_gold in pares:
        celdas_sistema = linea_sistema.celdas()
        celdas_gold = linea_gold.celdas()
        algun_fallo = False
        for atributo in ATRIBUTOS:
            valor_gold, confianza_gold = celdas_gold[atributo]
            valor_sistema = celdas_sistema[atributo].valor
            if confianza_gold is ConfianzaGold.INDECIDIBLE:
                por_atributo[atributo].indecidibles += 1
                celdas_indecidibles += 1
                continue
            por_atributo[atributo].evaluables += 1
            gold_norm = _normalizar(valor_gold)
            sistema_norm = _normalizar(valor_sistema)
            if gold_norm == sistema_norm:
                por_atributo[atributo].aciertos += 1
                continue
            algun_fallo = True
            if linea_sistema.estado is Estado.RESUELTA:
                fallas_escape.append(FallaEscape(
                    id=linea_gold.id, atributo=atributo,
                    valor_gold=gold_norm, valor_sistema=sistema_norm,
                ))

        if linea_sistema.estado is Estado.RESUELTA and algun_fallo:
            n_escapadas += 1
        if linea_sistema.estado is Estado.REVISION_MANUAL:
            revisiones_evaluables += 1
            if not algun_fallo:
                revisiones_sin_ruido += 1

    total_lineas = len(lineas)
    resueltas = sum(1 for l in lineas if l.estado is Estado.RESUELTA)
    ruido_revision = (revisiones_sin_ruido / revisiones_evaluables) if revisiones_evaluables else None

    return Metricas(
        total_lineas=total_lineas,
        tasa_escape=n_escapadas / total_lineas,
        cobertura=resueltas / total_lineas,
        ruido_revision=ruido_revision,
        exactitud_segmentacion=exactitud_segmentacion,
        celdas_indecidibles=celdas_indecidibles,
        por_atributo=por_atributo,
        fallas_escape=fallas_escape,
        fallas_segmentacion=fallas_segmentacion,
    )


# --------------------------------------------------------------------------
# Informe en markdown por consola.
# --------------------------------------------------------------------------

_A = chr(0xe1)  # a con tilde
_E = chr(0xe9)  # e con tilde
_I = chr(0xed)  # i con tilde
_O = chr(0xf3)  # o con tilde
_U = chr(0xfa)  # u con tilde
_N = chr(0xf1)  # n con tilde


def _pct(valor: Optional[float]) -> str:
    return f"{valor:.1%}" if valor is not None else "sin datos (0 l" + _I + "neas)"


def _formatear_informe(m: Metricas) -> str:
    l = []
    l.append("# Informe de evaluaci" + _O + "n " + chr(0x2014) + " arn" + _E + "s")
    l.append("")
    l.append("## Cifras globales")
    l.append("")
    l.append(f"- Total de l" + _I + f"neas: {m.total_lineas}")
    l.append(f"- Cobertura: {_pct(m.cobertura)}")
    l.append(f"- Tasa de escape: {_pct(m.tasa_escape)} " +
             chr(0x2014) + " es el n" + _U + "mero que se compromete con el cliente")
    l.append(f"- Ruido de revisi" + _O + f"n: {_pct(m.ruido_revision)}")
    l.append(f"- Exactitud de segmentaci" + _O + f"n: {_pct(m.exactitud_segmentacion)}")
    l.append(f"- Celdas indecidibles (excluidas de la comparaci" + _O + "n): "
             f"{m.celdas_indecidibles}")
    l.append("")
    l.append("## Desglose por atributo")
    l.append("")
    l.append("| atributo | aciertos | evaluables | tasa | indecidibles |")
    l.append("|---|---|---|---|---|")
    for atributo in ATRIBUTOS:
        ma = m.por_atributo[atributo]
        tasa = _pct(ma.aciertos / ma.evaluables) if ma.evaluables else "sin celdas evaluables"
        l.append(f"| {atributo} | {ma.aciertos} | {ma.evaluables} | {tasa} | {ma.indecidibles} |")
    l.append("")
    l.append("## L" + _I + "neas ca" + _I + "das (escape)")
    l.append("")
    if not m.fallas_escape:
        l.append("Ninguna l" + _I + "nea RESUELTA se cay" + _O + " contra el gold.")
    else:
        l.append("| id | atributo | gold deca | sistema dijo |".replace("deca", "dec" + _I + "a"))
        l.append("|---|---|---|---|")
        for f in m.fallas_escape:
            l.append(f"| {f.id} | {f.atributo} | {f.valor_gold} | {f.valor_sistema} |")
    l.append("")
    l.append("## Fallos de segmentaci" + _O + "n")
    l.append("")
    if not m.fallas_segmentacion:
        l.append("Ninguna fila discrepa en n" + _U + "mero o tipo de l" + _I + "neas.")
    else:
        l.append("| fila | nombres gold | nombres sistema |")
        l.append("|---|---|---|")
        for f in m.fallas_segmentacion:
            l.append(f"| {f.fila} | {f.nombres_gold} | {f.nombres_sistema} |")
    return "\n".join(l)


if __name__ == "__main__":
    from datos.guion_falso import puerto_de_guion
    from motor.pipeline import procesar_mto

    RUTA_MTO = Path("datos/MTO_tornilleria.xlsx")
    RUTA_GOLD = Path("datos/gold_set_v1.xlsx")

    lineas_sistema = procesar_mto(RUTA_MTO, puerto_de_guion())
    lineas_gold = cargar_gold(RUTA_GOLD)
    metricas = evaluar(lineas_sistema, lineas_gold)
    print(_formatear_informe(metricas))
