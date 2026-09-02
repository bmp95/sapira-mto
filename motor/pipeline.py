"""Etapa 5 y orquestacion. Convierte cada fila del MTO en una o mas
`LineaSalida`.

Cinco pasos por fila: segmentar con votacion (A1), comprobar las
invariantes 2/3/4 sobre la fila completa, extraer por elemento contra
los catalogos cerrados (nombre, norma, calidad, acabado, medida,
longitud), aplicar las derivaciones (material de la calidad, nombre de
la norma) y la extrapolacion de medida dentro del set, comprobar
coherencias cruzadas, y calcular la confianza.

La extraccion por elemento aqui es determinista (regex + catalogos.emparejar),
no un LLM: el puerto real (Tarea 13) hara `extraer()` con el modelo, pero
para ejercitar el pipeline con `PuertoFalso` (que solo guioniza
`segmentar()`) hace falta una via sin red. El limite de contencion --nunca
mirar mas texto que el propio tramo del elemento-- se respeta igual:
cada extractor solo recibe `texto[ini:fin]` del elemento, nunca la fila
completa, salvo dos casos explicitos y acotados al elemento principal
(el primero del set, normalmente el tornillo o el esparrago): el ambito
de fila (ver `_atribuir_ambito_a_principal`) y, como ultimo respaldo, la
columna MATERIAL del xlsx (ver `_calidad_de_columna_material`) cuando ni
el tramo propio ni el ambito de fila traen calidad. Ninguno de los dos
alcanza jamas a los demas elementos del set: la calidad no se atribuye
entre elementos, es la regla mas importante del caso.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from motor.cantidades import multiplicador
from motor.catalogos import ACABADOS, CALIDADES_ALIAS, NOMBRES, emparejar, normalizar_norma
from motor.coherencias import TODAS_ACTIVAS, comprobar
from motor.confianza import aplicar_confianza
from motor.derivaciones import material_de_calidad, material_de_norma, nombre_de_norma
from motor.invariantes import UMBRAL_COBERTURA, cobertura, contar_sustantivos, hay_solape, verificar_literal
from motor.lectura_mto import FilaMTO, leer_mto
from motor.modelos import ATRIBUTOS, LineaSalida, Motivo, Procedencia, Valor
from motor.puerto_llm import PuertoLLM
from motor.segmentador import segmentar_con_votacion

# Formatos de norma esperables (reglas_tornilleria.md seccion 8): DIN, DIN EN, ISO,
# ASME, ASTM, MSS SP. El identificador puede empezar por una letra (ASTM
# A193, ASTM F436) o ser puramente numerico (DIN 933).
_RE_NORMA = re.compile(r"\b(DIN\s+EN|MSS\s+SP|DIN|ISO|ASME|ASTM|EN)\s+([A-Z]{0,3}\d[\w.\-]*)", re.IGNORECASE)
_RE_MEDIDA_METRICA = re.compile(r"\bM(\d+)(?:\s*[xX]\s*(\d+))?\b")
_RE_MEDIDA_IMPERIAL = re.compile(r'\b(\d+(?:/\d+)?)"(?:\s*[xX]\s*(\d+))?')
# Grados ASTM marcados como calidad pero fuera de la tabla (reglas seccion 5): "se
# extrae tal cual". GR B7, GR 2H.
_RE_GRADO_ASTM = re.compile(r"\bGR\s+([A-Z0-9]+)\b", re.IGNORECASE)

# reglas_tornilleria.md seccion 7: "Campo obligatorio para toda la tornilleria
# excepto para tuerca y arandela."
_NOMBRES_SIN_LONGITUD_OBLIGATORIA = {"TUERCA", "ARANDELA"}

_REGLA_MEDIDA_EXTRAPOLADA = "MEDIDA-EXTRAPOLADA-SET"
_REGLA_LONGITUD_METRICA = "LONGITUD-MM-POR-MEDIDA-METRICA"
_REGLA_LONGITUD_IMPERIAL_FORZADA = "LONGITUD-MM-FORZADA-POR-POLITICA"

# Codigo del motivo con el que se marca una fila cuyo procesamiento reventó (excepcion no
# controlada: corte de red que agoto los reintentos del puerto, o cualquier otro fallo). Es
# publico -- lo usa `contar_fallos_de_proceso` mas abajo y lo puede usar el arnes/front sin
# tener que conocer el string a mano.
CODIGO_FALLO_DE_PROCESO = "FALLO_DE_PROCESO"

_LOG = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Politicas: decisiones de criterio propio, no reglas escritas del cliente.
# Ronda de correccion 2. Cada una lleva interruptor porque hay que poder
# apagarla delante del cliente y medir lo que cuesta -- este diccionario y
# su docstring por clave son el material del one-pager para esa pregunta.
# --------------------------------------------------------------------------

POLITICAS_POR_DEFECTO: dict[str, bool] = {
    # Las reglas dicen "material: se extrae el que aparezca" (reglas seccion
    # 4) pero el MTO casi nunca lo escribe; derivarlo de la calidad -- o,
    # cuando la calidad no alcanza, de una norma que lo fija por si sola
    # (ASTM F436) -- es nuestra lectura de la decision 1 del diseno, no una
    # regla citada del cliente.
    "derivar_material": True,
    # Que la columna MATERIAL del xlsx describa al elemento principal es una
    # inferencia nuestra sobre los datos del cliente (evidencia: fila 7), no
    # algo que las reglas escritas digan en ningun sitio.
    "columna_material_al_principal": True,
    # reglas_tornilleria.md seccion 10, punto 4, lo dice explicito: "no esta
    # dicho a que elementos alcanza" el acabado de cierre de un set. Repartir
    # EXTRAIDO al principal e INFERIDO al resto es criterio nuestro.
    "acabado_de_cierre_a_todo_el_set": True,
    # Que un numero sin unidad tras una norma imperial se lea como INFERIDO
    # (revision) y no como milimetros asumidos es una lectura de la decision
    # 4.3 del diseno, no una regla que las reglas del cliente escriban.
    "longitud_imperial_sin_unidad_a_revision": True,
}


# --------------------------------------------------------------------------
# Extraccion por elemento (codigo, no LLM). Cada funcion recibe el texto
# completo de la fila y el tramo [ini, fin) del elemento, y devuelve
# (valor, literal, span_absoluto) o None. El span siempre esta en la
# coordenada del texto de fila completo, nunca del tramo, porque asi lo
# exige `Valor.span` ("posicion en el texto saneado", spec seccion 6) y porque
# `verificar_literal` compara contra ese mismo texto completo.
# --------------------------------------------------------------------------

def _emparejar_absoluto(texto: str, ini: int, fin: int, tabla: dict[str, str]):
    return [(valor, literal, (s0 + ini, s1 + ini))
            for valor, literal, (s0, s1) in emparejar(texto[ini:fin], tabla)]


def _extraer_nombre(texto: str, ini: int, fin: int):
    hallazgos = _emparejar_absoluto(texto, ini, fin, NOMBRES)
    return hallazgos[0] if hallazgos else None


def _extraer_norma(texto: str, ini: int, fin: int):
    m = _RE_NORMA.search(texto[ini:fin])
    if not m:
        return None
    literal = m.group(0)
    valor = normalizar_norma(literal)
    s0, s1 = m.span()
    return valor, literal, (s0 + ini, s1 + ini)


def _extraer_acabado(texto: str, ini: int, fin: int):
    hallazgos = _emparejar_absoluto(texto, ini, fin, ACABADOS)
    return hallazgos[0] if hallazgos else None


def _extraer_medida_longitud(texto: str, ini: int, fin: int, politicas: dict[str, bool]):
    """Devuelve (medida, longitud, span_ocupado_relativo).

    `medida` es (valor, literal, span_absoluto) o None. `longitud` es
    (valor, literal, span_absoluto, procedencia, regla_o_None) o None.

    Si la medida es metrica, la longitud es DERIVADO (mm por definicion del
    formato M<n>). Si es imperial y el numero no trae unidad, la politica
    `longitud_imperial_sin_unidad_a_revision` decide: activa (por defecto,
    decision seccion 4.3 del diseno), INFERIDO -> revision; apagada, se
    asume mm igual que en el caso metrico y la celda resuelve como DERIVADO.

    `span_ocupado_relativo` es la region del tramo que ya ha sido leida como
    medida/longitud, para no dejar que un digito suelto ahi (el "8" de
    7/8") se lea luego como si fuera una calidad catalogada.
    """
    tramo = texto[ini:fin]
    m = _RE_MEDIDA_METRICA.search(tramo)
    if m:
        literal = "M" + m.group(1)
        medida = (literal, literal, (ini + m.start(), ini + m.start() + len(literal)))
        longitud = None
        if m.group(2):
            l0, l1 = m.span(2)
            longitud = (f"{m.group(2)} mm", m.group(2), (ini + l0, ini + l1),
                       Procedencia.DERIVADO, _REGLA_LONGITUD_METRICA)
        return medida, longitud, m.span()
    m = _RE_MEDIDA_IMPERIAL.search(tramo)
    if m:
        literal = m.group(1) + '"'
        medida = (literal, literal, (ini + m.start(1), ini + m.start(1) + len(literal)))
        longitud = None
        if m.group(2):
            l0, l1 = m.span(2)
            if politicas["longitud_imperial_sin_unidad_a_revision"]:
                longitud = (f"{m.group(2)} mm", m.group(2), (ini + l0, ini + l1),
                           Procedencia.INFERIDO, None)
            else:
                longitud = (f"{m.group(2)} mm", m.group(2), (ini + l0, ini + l1),
                           Procedencia.DERIVADO, _REGLA_LONGITUD_IMPERIAL_FORZADA)
        return medida, longitud, m.span()
    return None, None, None


def _extraer_calidad(texto: str, ini: int, fin: int, ocultar: list[tuple[int, int]]):
    """`ocultar`: spans absolutos (norma, medida/longitud) que se enmascaran
    antes de buscar calidad, para que un digito de la medida (el "8" de
    7/8") no case como si fuera la calidad catalogada "8" (solo tuercas,
    reglas seccion 5). `catalogos.emparejar` exige limites de token pero no excluye
    "/" ni '"' como separadores, asi que sin este enmascarado ese "8" pasa
    limpiamente los limites _ANTES/_DESPUES."""
    tramo = list(texto[ini:fin])
    for (s0, s1) in ocultar:
        for i in range(max(0, s0 - ini), max(0, min(s1 - ini, len(tramo)))):
            tramo[i] = "#"
    tramo_enmascarado = "".join(tramo)
    hallazgos = emparejar(tramo_enmascarado, CALIDADES_ALIAS)
    if hallazgos:
        valor, literal, (s0, s1) = hallazgos[0]
        return valor, literal, (s0 + ini, s1 + ini)
    m = _RE_GRADO_ASTM.search(tramo_enmascarado)
    if m:
        literal = m.group(0).upper()
        return literal, literal, (ini + m.start(), ini + m.end())
    return None


def _calidad_de_columna_material(material_col: str):
    """Ronda de correccion: la columna MATERIAL del xlsx describe el
    elemento principal de la fila, no el conjunto -- evidencia: fila 7,
    'BOLT DIN931 M12x60 A4-70 with NUT DIN934 M12 A4-80', donde la columna
    dice exactamente 'A4-70', la calidad propia del tornillo, no la 'A4-80'
    de la tuerca. Solo se usa como respaldo cuando el propio tramo del
    elemento principal no trae calidad (filas 2 y 3 del MTO: la
    descripcion no menciona ninguna calidad en absoluto).

    A veces la columna trae una norma con su grado en vez de una calidad
    suelta (fila 1: 'ASTM A193 GR B7/A194 GR 2H'): de ahi se toma solo lo
    que el catalogo reconoce como calidad -- aqui, 'GR B7', la primera
    que aparece -- nunca la cadena entera."""
    if not material_col:
        return None
    norma = _extraer_norma(material_col, 0, len(material_col))
    ocultar = [norma[2]] if norma is not None else []
    return _extraer_calidad(material_col, 0, len(material_col), ocultar)


# Arreglo 2 (ronda de correccion 3, T10): en 14 de las 15 filas la columna
# MATERIAL trae calidad o norma, no material -- pero en la fila 14
# ('Arandela plana DIN 125 M10, acero, zincada') es la unica fila donde esa
# columna SI trae material, literal: 'acero'. Normalizacion semantica de
# reglas_tornilleria.md seccion 4: ACERO/STEEL -> AC; el par INOX se anade
# por simetria del mismo par de valores (AC / INOX) que nombra esa seccion.
_MATERIALES_TEXTO = {
    "ACERO": "AC", "STEEL": "AC",
    "INOX": "INOX", "INOXIDABLE": "INOX", "STAINLESS STEEL": "INOX", "STAINLESS": "INOX",
}


def _material_de_columna_material(material_col: str):
    """Solo se toma si hay una palabra reconocible de `_MATERIALES_TEXTO`
    en la columna -- nunca se inventa. En las otras 14 filas esa columna
    trae calidad (`8.8`) o norma con grado (`ASTM A193 GR B7`), y ninguna
    de esas cadenas contiene una palabra de esta tabla, asi que no hay
    riesgo de leer un material donde en realidad hay otra cosa."""
    if not material_col:
        return None
    hallazgos = emparejar(material_col, _MATERIALES_TEXTO)
    return hallazgos[0] if hallazgos else None


# --------------------------------------------------------------------------
# Construccion de celdas
# --------------------------------------------------------------------------

def _valor_extraido(hallazgo) -> Valor:
    if hallazgo is None:
        return Valor(procedencia=Procedencia.AUSENTE)
    valor, literal, span = hallazgo
    return Valor(valor=valor, literal=literal, span=span, procedencia=Procedencia.EXTRAIDO)


class _DatosElemento:
    """Lo que se extrae de un elemento antes de saber si es principal, si
    hereda algo del ambito de fila o si su medida hay que extrapolarla."""

    __slots__ = ("nombre", "norma", "calidad", "acabado", "medida", "longitud", "calidad_fuente")

    def __init__(self, texto: str, ini: int, fin: int, politicas: dict[str, bool]):
        self.nombre = _extraer_nombre(texto, ini, fin)
        self.norma = _extraer_norma(texto, ini, fin)
        medida, longitud, span_ocupado = _extraer_medida_longitud(texto, ini, fin, politicas)
        self.medida = medida
        self.longitud = longitud
        ocultar = []
        if self.norma is not None:
            ocultar.append(self.norma[2])
        if span_ocupado is not None:
            ocultar.append((ini + span_ocupado[0], ini + span_ocupado[1]))
        self.calidad = _extraer_calidad(texto, ini, fin, ocultar)
        self.acabado = _extraer_acabado(texto, ini, fin)
        # "descripcion" (el tramo propio) salvo que se rellene desde la
        # columna MATERIAL -- ver `_calidad_de_columna_material`. Determina
        # contra que texto se verifica el literal de esta celda mas tarde.
        self.calidad_fuente = "descripcion"


# Arreglo 1 (ronda de correccion 3, T10): el elemento principal se decide
# por TIPO, no por posicion. Con el segmentador real, una fila puede
# escribir la tuerca antes que el tornillo ("2 TUERCAS ... y 2 ARANDELAS
# ... para TORNILLO ...") y `datos[0]` dejaba de ser el tornillo -- la
# calidad de la columna MATERIAL, el acabado de cierre y el origen de la
# extrapolacion de medida se iban al elemento equivocado.
_TIPOS_PRINCIPALES = {"ESPARRAGO", "TORNILLO", "VARILLA ROSCADA"}


def _indice_principal(datos: list[_DatosElemento]) -> int:
    """El primer elemento cuyo propio tramo resuelve un tipo principal
    (esparrago, tornillo o varilla roscada; tuerca y arandela son
    accesorios). Si ninguno es principal -- una fila que solo describe
    tuercas, como la 11 o la 13 -- el principal es el primer elemento,
    que es lo que ya haciamos antes de este arreglo."""
    for i, d in enumerate(datos):
        tipo = d.nombre[0] if d.nombre is not None else None
        if tipo in _TIPOS_PRINCIPALES:
            return i
    return 0


def _atribuir_ambito_a_principal(datos: list[_DatosElemento], texto: str,
                                  ambito_fila: list[tuple[int, int]],
                                  politicas: dict[str, bool],
                                  indice_principal: int) -> None:
    """Decision seccion 4 del diseno: el ambito de fila (el ', 8.8, zincado' del
    final) se lee sobre el elemento principal (por tipo -- ver
    `_indice_principal`, normalmente el tornillo o el esparrago, sea cual
    sea su posicion en la fila) como si fuera su propio tramo -- EXTRAIDO.

    Para el resto de elementos del set la calidad NUNCA se atribuye (regla
    mas importante del caso, sin interruptor: si no trae calidad propia, a
    revision). El acabado si se apunta, pero como INFERIDO (un juicio, no
    un dato) y solo si la politica `acabado_de_cierre_a_todo_el_set` esta
    activa -- reglas_tornilleria.md seccion 10 punto 4 dice explicitamente
    que esto no esta decidido por el cliente, asi que es criterio nuestro y
    lleva interruptor. Apagada, el acabado de cierre se queda en el
    elemento principal y el resto no lo ve."""
    if not ambito_fila or not datos:
        return
    ini, fin = ambito_fila[0]
    principal = datos[indice_principal]
    if principal.calidad is None:
        principal.calidad = _extraer_calidad(texto, ini, fin, [])
    if principal.acabado is None:
        principal.acabado = _extraer_acabado(texto, ini, fin)
    if not politicas["acabado_de_cierre_a_todo_el_set"]:
        return
    acabado_ambito = _extraer_acabado(texto, ini, fin)
    if acabado_ambito is None:
        return
    for i, d in enumerate(datos):
        if i == indice_principal:
            continue
        if d.acabado is None:
            d.acabado = acabado_ambito  # se marca INFERIDO mas abajo, no aqui


def _extrapolar_medida(datos: list[_DatosElemento], indice_principal: int) -> list[tuple | None]:
    """reglas seccion 2 y seccion 6: la unica extrapolacion que permiten estas reglas es
    la de la medida. Devuelve, por elemento, o bien su propia medida
    EXTRAIDO (tal cual vino de `_DatosElemento`) o una tupla
    (valor, literal) DERIVADA de la medida propia del elemento principal;
    si el principal no trae medida propia, la primera que aparezca en el
    set (dentro del mismo conjunto atornillado todas las medidas propias
    deben coincidir, asi que el origen no cambia el valor, pero preferir
    al principal es mas trazable)."""
    fuente = datos[indice_principal].medida
    if fuente is None:
        fuente = next((d.medida for d in datos if d.medida is not None), None)
    resultado = []
    for d in datos:
        if d.medida is not None:
            resultado.append(("propia", d.medida))
        elif fuente is not None:
            resultado.append(("extrapolada", fuente))
        else:
            resultado.append(("propia", None))
    return resultado


# --------------------------------------------------------------------------
# Obligatoriedad (vive aqui, no en un validador aparte -- ver brief T10)
# --------------------------------------------------------------------------

def _verificar_obligatoriedad(linea: LineaSalida) -> list[Motivo]:
    motivos: list[Motivo] = []
    if linea.nombre.procedencia is Procedencia.AUSENTE:
        # Defensivo: en las 30 lineas reales del MTO el nombre siempre se
        # resuelve (viene del propio tramo o, en su defecto, de la norma
        # via `nombre_de_norma`), pero `aplicar_confianza` salta las celdas
        # AUSENTE igual que saltaba la calidad -- sin este cheque un nombre
        # sin resolver pasaria de largo en vez de ir a revision.
        motivos.append(Motivo(
            codigo="SIN_NOMBRE", atributo="nombre",
            texto="No se pudo determinar qu" + chr(0xe9) + " tipo de pieza es; "
                  "sin nombre no hay material que comprar."))
    if linea.norma.procedencia is Procedencia.AUSENTE:
        motivos.append(Motivo(
            codigo="SIN_NORMA", atributo="norma",
            texto="Sin norma no se puede pedir a un proveedor."))
    if linea.calidad.procedencia is Procedencia.AUSENTE:
        motivos.append(Motivo(
            codigo="SIN_CALIDAD", atributo="calidad",
            texto="Falta la calidad: seg" + chr(0xfa) + "n la regla 5, sin calidad "
                  "el " + chr(0xed) + "tem se clasifica como revisi" + chr(0xf3) + "n manual."))
    nombre_val = linea.nombre.valor
    if (linea.longitud.procedencia is Procedencia.AUSENTE
            and nombre_val not in _NOMBRES_SIN_LONGITUD_OBLIGATORIA):
        motivos.append(Motivo(
            codigo="LONGITUD_OBLIGATORIA_AUSENTE", atributo="longitud",
            texto="La longitud es obligatoria para toda la torniller" + chr(0xed) + "a "
                  "salvo tuerca y arandela, y aqu" + chr(0xed) + " no aparece."))
    return motivos


def _motivo_longitud_inferida(linea: LineaSalida) -> Motivo | None:
    if linea.longitud.procedencia is not Procedencia.INFERIDO:
        return None
    return Motivo(
        codigo="LONGITUD_SIN_UNIDAD", atributo="longitud",
        valor_propuesto=linea.longitud.valor,
        texto="La longitud no trae unidad; en pulgadas ser" + chr(0xed) + "a una "
              "medida absurda, as" + chr(0xed) + " que se propone " + str(linea.longitud.valor) +
              " para revisi" + chr(0xf3) + "n.")


# --------------------------------------------------------------------------
# Invariantes de fila (2, 3, 4). Si alguna falla, la fila entera va a
# revision: ninguna comprobacion por elemento caza un elemento que el
# segmentador se salto entero (invariante 2 en motor/invariantes.py).
# --------------------------------------------------------------------------

def _motivo_invariante_rota(texto: str, seg) -> Motivo | None:
    cob = cobertura(texto, seg)
    if cob < UMBRAL_COBERTURA:
        return Motivo(codigo="COBERTURA_INSUFICIENTE",
                      texto=f"La segmentaci" + chr(0xf3) + f"n solo cubre el {cob:.0%} del "
                            "texto: es probable que se haya perdido un elemento entero.")
    if hay_solape(seg):
        return Motivo(codigo="SOLAPE_DE_TRAMOS",
                      texto="Dos tramos de la segmentaci" + chr(0xf3) + "n se solapan.")
    n_sustantivos = contar_sustantivos(texto)
    if n_sustantivos != len(seg.elementos):
        return Motivo(codigo="RECUENTO_DE_SUSTANTIVOS_INCONSISTENTE",
                      texto=f"El esc" + chr(0xe1) + f"ner independiente cuenta "
                            f"{n_sustantivos} sustantivos de tipo pero la segmentaci" +
                            chr(0xf3) + f"n trae {len(seg.elementos)} elementos.")
    return None


def _linea_fila_rota(id_: str, fila: FilaMTO, motivo: Motivo) -> LineaSalida:
    linea = LineaSalida.vacia(id=id_, fila_origen=fila.item, cantidad=fila.cantidad)
    linea.confianza = 0
    linea.motivos = [motivo]
    return linea


def _linea_fila_fallida(id_: str, fila: FilaMTO) -> LineaSalida:
    """Una fila cuyo procesamiento lanzo una excepcion (tipicamente un corte de red que
    agoto los reintentos del puerto -- ver motor/puerto_gemini.py) no puede llevarse por
    delante al resto del lote: se marca a revision con confianza 0 y se sigue con la
    siguiente fila (ver el `try`/`except` en `procesar_mto`). El texto es legible por un
    comprador -- sin trazas tecnicas ni nombres de excepcion -- porque es lo unico que ve
    quien tiene que decidir si relanzarla."""
    linea = LineaSalida.vacia(id=id_, fila_origen=fila.item, cantidad=fila.cantidad)
    linea.confianza = 0
    linea.motivos = [Motivo(
        codigo=CODIGO_FALLO_DE_PROCESO,
        texto="No se ha podido procesar esta fila: error de conexi" + chr(0xf3) + "n con el "
              "servicio o fallo inesperado del sistema. Vuelve a lanzarla.")]
    return linea


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------

def _construir_linea(id_: str, fila: FilaMTO, texto: str, elem, es_principal: bool,
                     datos: _DatosElemento, medida_resuelta,
                     interruptores_coherencia: dict[str, bool],
                     politicas: dict[str, bool]) -> LineaSalida:
    linea = LineaSalida.vacia(id=id_, fila_origen=fila.item, cantidad=fila.cantidad * multiplicador(texto[elem.span[0]:elem.span[1]]))

    linea.nombre = _valor_extraido(datos.nombre)
    if linea.nombre.procedencia is Procedencia.AUSENTE and datos.norma is not None:
        derivado = nombre_de_norma(datos.norma[0])
        if derivado is not None:
            valor, regla = derivado
            linea.nombre = Valor(valor=valor, procedencia=Procedencia.DERIVADO, regla=regla)

    linea.norma = _valor_extraido(datos.norma)
    linea.calidad = _valor_extraido(datos.calidad)

    origen_medida, medida_dato = medida_resuelta
    if origen_medida == "propia":
        linea.medida = _valor_extraido(medida_dato)
    elif medida_dato is not None:
        valor, literal, _span = medida_dato
        linea.medida = Valor(valor=valor, literal=literal, procedencia=Procedencia.DERIVADO,
                             regla=_REGLA_MEDIDA_EXTRAPOLADA)

    if datos.longitud is not None:
        valor, literal, span, proc, regla = datos.longitud
        if proc is Procedencia.DERIVADO:
            linea.longitud = Valor(valor=valor, literal=literal, span=span,
                                   procedencia=Procedencia.DERIVADO, regla=regla)
        else:
            linea.longitud = Valor(valor=valor, literal=literal, span=span, procedencia=proc)

    if datos.acabado is not None:
        valor, literal, span = datos.acabado
        proc = Procedencia.EXTRAIDO if es_principal else Procedencia.INFERIDO
        linea.acabado = Valor(valor=valor, literal=literal, span=span, procedencia=proc)

    # Cadena de respaldo del material, cada eslabon solo si el anterior no
    # resolvio nada: 1) derivado de la calidad propia (el caso normal);
    # 2) Arreglo 3 -- derivado de la norma sola, para las normas que fijan
    # material pase lo que pase con el grado (ASTM F436: arandelas de las
    # filas 1 y 5, que no traen calidad propia); 3) Arreglo 2 -- palabra de
    # material reconocible en la columna MATERIAL del xlsx, solo para el
    # elemento principal (fila 14: 'acero'). Los dos primeros son
    # entailments deterministas (DERIVADO) y comparten el interruptor
    # `derivar_material`; el tercero es un literal de otra columna
    # (EXTRAIDO) y comparte `columna_material_al_principal` con la calidad
    # tomada de esa misma columna.
    material_fuente_columna = False
    if politicas["derivar_material"] and linea.calidad.procedencia is Procedencia.EXTRAIDO:
        derivado = material_de_calidad(linea.calidad.valor)
        if derivado is not None:
            valor, regla = derivado
            linea.material = Valor(valor=valor, procedencia=Procedencia.DERIVADO, regla=regla)
    if (politicas["derivar_material"] and linea.material.procedencia is Procedencia.AUSENTE
            and linea.norma.valor is not None):
        derivado = material_de_norma(linea.norma.valor)
        if derivado is not None:
            valor, regla = derivado
            linea.material = Valor(valor=valor, procedencia=Procedencia.DERIVADO, regla=regla)
    if (politicas["columna_material_al_principal"] and es_principal
            and linea.material.procedencia is Procedencia.AUSENTE):
        hallazgo = _material_de_columna_material(fila.material_col)
        if hallazgo is not None:
            valor, literal, span = hallazgo
            linea.material = Valor(valor=valor, literal=literal, span=span,
                                   procedencia=Procedencia.EXTRAIDO)
            material_fuente_columna = True

    literales_ok: dict[str, bool] = {}
    for atributo in ATRIBUTOS:
        celda = getattr(linea, atributo)
        if celda.procedencia in (Procedencia.EXTRAIDO, Procedencia.INFERIDO):
            # La calidad (y, desde el Arreglo 2, el material) tomados de la
            # columna MATERIAL viven en otra coordenada de texto: su span
            # apunta a `fila.material_col`, no a la descripcion, asi que el
            # literal se verifica contra esa misma columna.
            de_columna = ((atributo == "calidad" and datos.calidad_fuente == "material_col")
                          or (atributo == "material" and material_fuente_columna))
            fuente = fila.material_col if de_columna else texto
            literales_ok[atributo] = verificar_literal(celda.literal, fuente, celda.span)

    motivos_coherencia = comprobar(linea, interruptores_coherencia)
    linea = aplicar_confianza(linea, elem.votos, motivos_coherencia, literales_ok)

    obligatoriedad = _verificar_obligatoriedad(linea)
    if obligatoriedad:
        linea.confianza = 0
        linea.motivos = linea.motivos + obligatoriedad

    motivo_longitud = _motivo_longitud_inferida(linea)
    if motivo_longitud is not None:
        linea.motivos = linea.motivos + [motivo_longitud]

    return linea


def _procesar_fila(fila: FilaMTO, puerto: PuertoLLM, politicas: dict[str, bool],
                   interruptores_coherencia: dict[str, bool],
                   siguiente_id) -> list[LineaSalida]:
    texto = fila.descripcion
    seg = segmentar_con_votacion(puerto, texto, pasadas=3)

    motivo_roto = _motivo_invariante_rota(texto, seg)
    if motivo_roto is not None:
        return [_linea_fila_rota(siguiente_id(), fila, motivo_roto)]

    datos = [_DatosElemento(texto, *elem.span, politicas) for elem in seg.elementos]
    indice_principal = _indice_principal(datos)
    _atribuir_ambito_a_principal(datos, texto, seg.ambito_fila, politicas, indice_principal)
    if politicas["columna_material_al_principal"] and datos[indice_principal].calidad is None:
        # Ultimo respaldo, solo para el elemento principal por TIPO (nunca
        # para el resto del set -- ver `_calidad_de_columna_material`): la
        # propia descripcion (ni su tramo ni el ambito de fila) trajo
        # calidad, asi que se mira la columna MATERIAL del xlsx.
        respaldo = _calidad_de_columna_material(fila.material_col)
        if respaldo is not None:
            datos[indice_principal].calidad = respaldo
            datos[indice_principal].calidad_fuente = "material_col"
    medidas_resueltas = _extrapolar_medida(datos, indice_principal)

    lineas = []
    for i, (elem, d, medida_resuelta) in enumerate(zip(seg.elementos, datos, medidas_resueltas)):
        linea = _construir_linea(siguiente_id(), fila, texto, elem, i == indice_principal, d,
                                 medida_resuelta, interruptores_coherencia, politicas)
        lineas.append(linea)
    return lineas


def procesar_mto(ruta: Path, puerto: PuertoLLM,
                 politicas: dict[str, bool] | None = None,
                 interruptores_coherencia: dict[str, bool] | None = None) -> list[LineaSalida]:
    politicas = politicas if politicas is not None else POLITICAS_POR_DEFECTO
    interruptores_coherencia = (interruptores_coherencia if interruptores_coherencia is not None
                                else TODAS_ACTIVAS)
    filas = leer_mto(ruta)

    contador = {"n": 0}

    def siguiente_id():
        contador["n"] += 1
        return f"L{contador['n']:03d}"

    lineas: list[LineaSalida] = []
    for fila in filas:
        try:
            lineas.extend(_procesar_fila(fila, puerto, politicas, interruptores_coherencia, siguiente_id))
        except Exception as exc:
            # Una excepcion no controlada al procesar una fila (tipicamente un corte de red
            # que agoto los reintentos del puerto) no puede tumbar el lote entero -- en un
            # MTO de veinte mil filas eso significa perder horas de trabajo por un parpadeo
            # de red en una sola fila. Se marca esta fila para revision y se sigue.
            _LOG.warning("Fila %d fallo durante el procesamiento y se marca para revision "
                        "manual: %s: %s", fila.item, type(exc).__name__, exc)
            lineas.append(_linea_fila_fallida(siguiente_id(), fila))
    return lineas


def contar_fallos_de_proceso(lineas: list[LineaSalida]) -> int:
    """Cuantas lineas de `lineas` vienen de una fila cuyo procesamiento fallo (marcadas con
    `CODIGO_FALLO_DE_PROCESO` -- ver `_linea_fila_fallida`). Que una tirada termine con filas
    fallidas tiene que ser visible para el arnes y el front, no algo que solo se note contando
    a mano; esta funcion es la forma publica de preguntarlo sin conocer el codigo de motivo."""
    return sum(1 for l in lineas if any(m.codigo == CODIGO_FALLO_DE_PROCESO for m in l.motivos))
