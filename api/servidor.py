"""Tarea 14: la API. Es lo que el front consume (spec.md seccion 9): una persona de
compras sube el MTO, resuelve la cola de revision con un clic y exporta lo que va a pedir.

Cuatro endpoints:
  POST /api/procesar  -- sube un .xlsx, devuelve las lineas y un resumen de la pasada.
  POST /api/resolver  -- escribe una celda con procedencia EXTRAIDO y recalcula la
                         confianza y el estado de esa linea. El estado nunca se
                         escribe a mano: siempre se deriva (motor/modelos.py).
  GET  /api/exportar  -- .xlsx agrupado por material canonico (los siete atributos
                         iguales), cantidades sumadas.
  GET  /              -- el front compilado (front/dist) si existe; si no, un
                         mensaje claro de que hace falta compilarlo, nunca un 404 seco.

El estado del proceso vive en memoria (`app.state.sesiones`), indexado por un
identificador de sesion que devuelve /api/procesar -- alcance declarado del caso
(spec.md seccion 10): un proceso, un fichero, sin persistencia ni multiusuario.
"""
from __future__ import annotations

import tempfile
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

import openpyxl
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from motor.coherencias import TODAS_ACTIVAS, comprobar
from motor.confianza import PUNTOS_VOTOS, aplicar_confianza
from motor.modelos import ATRIBUTOS, Estado, LineaSalida, Procedencia, Valor
from motor.pipeline import (POLITICAS_POR_DEFECTO, _motivo_longitud_inferida,
                            _verificar_obligatoriedad, contar_fallos_de_proceso,
                            procesar_mto)
from motor.puerto_gemini import PuertoGemini
from motor.puerto_llm import PuertoLLM

_A, _E, _I, _O, _U = (chr(0xe1), chr(0xe9), chr(0xed), chr(0xf3), chr(0xfa))

_MEDIA_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _raiz_repo() -> Path:
    return Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# Peticiones
# --------------------------------------------------------------------------

class PeticionResolver(BaseModel):
    sesion_id: str
    linea_id: str
    atributo: str
    valor: str


# --------------------------------------------------------------------------
# Mensajes para el comprador. Todo no-ASCII via chr(0x....), nunca tecleado.
# --------------------------------------------------------------------------

def _mensaje_no_xlsx(nombre: str) -> str:
    return (f"El fichero '{nombre}' no es un .xlsx v" + _A + "lido. Sube el MTO en "
            "formato Excel (.xlsx).")


def _mensaje_sesion_no_encontrada(sesion_id: str) -> str:
    return (f"No hay ninguna sesi" + _O + f"n '{sesion_id}' en curso. Sube el MTO de "
            "nuevo con /api/procesar.")


def _mensaje_linea_no_encontrada(linea_id: str) -> str:
    return f"No hay ninguna l" + _I + f"nea '{linea_id}' en esta sesi" + _O + "n."


def _mensaje_atributo_invalido(atributo: str) -> str:
    return (f"'{atributo}' no es un atributo v" + _A + "lido. Los siete atributos son: "
            + ", ".join(ATRIBUTOS) + ".")


def _mensaje_front_no_compilado() -> str:
    return (
        "El front todav" + _I + "a no est" + _A + " compilado.\n\n"
        "Ejecuta, dentro de front/:\n"
        "  npm install\n"
        "  npm run build\n\n"
        "y vuelve a arrancar el servidor (python arrancar.py)."
    )


# --------------------------------------------------------------------------
# Serializacion de una linea. `estado` es una @property de LineaSalida, no un
# campo del modelo -- model_dump() no la incluye por si sola, hay que anadirla.
# --------------------------------------------------------------------------

def _linea_a_dict(linea: LineaSalida) -> dict:
    datos = linea.model_dump(mode="json")
    datos["estado"] = linea.estado.value
    return datos


def _construir_resumen(lineas: list[LineaSalida], segundos: float, puerto: PuertoLLM) -> dict:
    resueltas = sum(1 for l in lineas if l.estado is Estado.RESUELTA)
    coste = puerto.coste_estimado() if hasattr(puerto, "coste_estimado") else 0.0
    return {
        "total_lineas": len(lineas),
        "resueltas": resueltas,
        "en_revision": len(lineas) - resueltas,
        "fallos_de_proceso": contar_fallos_de_proceso(lineas),
        "segundos": segundos,
        "coste": coste,
    }


# --------------------------------------------------------------------------
# Resolver una celda: reproduce EXACTAMENTE la cola de calculo que
# motor.pipeline._construir_linea aplica al final (coherencias -> confianza ->
# obligatoriedad -> longitud inferida), pero solo sobre la linea ya
# construida -- no vuelve a tocar el texto de origen ni repite derivaciones.
# --------------------------------------------------------------------------

def _votos_de_la_linea(linea: LineaSalida) -> int:
    """El voto de segmentacion es una propiedad de la FILA (`Elemento.votos`),
    no de la celda, y `LineaSalida` no lo guarda aparte. Pero cada `Valor` ya
    evaluado en el proceso original dejo su marca en
    `factores['segmentacion']` (motor/confianza.py): se relee de la primera
    celda que la tenga. Si ninguna celda fue evaluada nunca (una linea que
    llego vacia, p.ej. una fila entera rota por invariante), se asume
    acuerdo total -- no hay ninguna otra pista, y no es un dato que el
    pipeline hubiera podido medir de por si en ese caso."""
    for celda in linea.celdas().values():
        puntos = celda.factores.get("segmentacion")
        if puntos is None:
            continue
        for votos, p in PUNTOS_VOTOS.items():
            if p == puntos:
                return votos
    return 3


def _literales_ok_de_la_linea(linea: LineaSalida, atributo_resuelto: str) -> dict[str, bool]:
    """Para la celda recien resuelta el literal se da por bueno: lo escribio
    el comprador, no hay texto de origen que verificar. Para el resto de
    celdas EXTRAIDO/INFERIDO, se relee lo que ya se midio la primera vez --
    queda guardado en `factores['literal']` de cada `Valor` (100 o 0) -- sin
    volver a tocar el texto original. Las DERIVADO no hacen falta aqui:
    `aplicar_confianza` las da por buenas sin consultar este diccionario."""
    literales_ok: dict[str, bool] = {}
    for nombre, celda in linea.celdas().items():
        if celda.procedencia not in (Procedencia.EXTRAIDO, Procedencia.INFERIDO):
            continue
        if nombre == atributo_resuelto:
            literales_ok[nombre] = True
        else:
            literales_ok[nombre] = celda.factores.get("literal") == 100
    return literales_ok


def _recalcular(linea: LineaSalida, atributo_resuelto: str) -> LineaSalida:
    votos = _votos_de_la_linea(linea)
    literales_ok = _literales_ok_de_la_linea(linea, atributo_resuelto)

    motivos_coherencia = comprobar(linea, TODAS_ACTIVAS)
    linea = aplicar_confianza(linea, votos, motivos_coherencia, literales_ok)

    obligatoriedad = _verificar_obligatoriedad(linea)
    if obligatoriedad:
        linea.confianza = 0
        linea.motivos = linea.motivos + obligatoriedad

    motivo_longitud = _motivo_longitud_inferida(linea)
    if motivo_longitud is not None:
        linea.motivos = linea.motivos + [motivo_longitud]

    return linea


def _resolver_celda(linea: LineaSalida, atributo: str, valor: str) -> LineaSalida:
    nueva = Valor(valor=valor, literal=valor, span=(0, len(valor)), procedencia=Procedencia.EXTRAIDO)
    setattr(linea, atributo, nueva)
    return _recalcular(linea, atributo)


# --------------------------------------------------------------------------
# Exportar: agrupado por material canonico -- los siete atributos iguales se
# agregan en una sola linea con la suma de cantidades. La columna estado y
# la de motivo dejan ver, sin abrir nada mas, cuales de las agrupadas siguen
# en revision.
# --------------------------------------------------------------------------

def _agrupar_por_material_canonico(lineas: list[LineaSalida]) -> list[dict]:
    grupos: dict[tuple, dict] = {}
    orden: list[tuple] = []
    for linea in lineas:
        clave = tuple(getattr(linea, atributo).valor for atributo in ATRIBUTOS)
        if clave not in grupos:
            grupos[clave] = {"cantidad": 0, "en_revision": False, "motivos": []}
            orden.append(clave)
        grupo = grupos[clave]
        grupo["cantidad"] += linea.cantidad
        if linea.estado is Estado.REVISION_MANUAL:
            grupo["en_revision"] = True
            for motivo in linea.motivos:
                if motivo.texto not in grupo["motivos"]:
                    grupo["motivos"].append(motivo.texto)

    filas: list[dict] = []
    for clave in orden:
        grupo = grupos[clave]
        filas.append({
            "valores": dict(zip(ATRIBUTOS, clave)),
            "cantidad": grupo["cantidad"],
            "estado": (Estado.REVISION_MANUAL.value if grupo["en_revision"]
                      else Estado.RESUELTA.value),
            "motivo": "; ".join(grupo["motivos"]),
        })
    return filas


def _construir_xlsx_exportacion(filas: list[dict]) -> bytes:
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Cola de compras"
    cabecera = list(ATRIBUTOS) + ["cantidad", "estado", "motivo"]
    hoja.append(cabecera)
    for fila in filas:
        hoja.append([fila["valores"][a] for a in ATRIBUTOS]
                    + [fila["cantidad"], fila["estado"], fila["motivo"]])
    buffer = BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


# --------------------------------------------------------------------------
# La app
# --------------------------------------------------------------------------

def crear_app(puerto: Optional[PuertoLLM] = None, *,
             directorio_front: Optional[Path] = None) -> FastAPI:
    """`puerto`, si se pasa, sustituye al puerto real (Gemini) -- es el punto de
    inyeccion que usan los tests con `PuertoFalso`, sin red. `directorio_front`
    sustituye a `front/dist` (solo para tests); si no se pasa, se mira la ruta
    real del repo."""
    app = FastAPI(title="Reconciliaci" + _O + "n MTO " + chr(0x2014) + " Torniller" + _I + "a")
    app.state.puerto = puerto if puerto is not None else PuertoGemini()
    app.state.sesiones: dict[str, list[LineaSalida]] = {}

    @app.post("/api/procesar")
    async def procesar(archivo: UploadFile = File(...)):
        nombre = archivo.filename or ""
        if not nombre.lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail=_mensaje_no_xlsx(nombre))

        contenido = await archivo.read()
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(contenido)
            ruta_tmp = Path(tmp.name)

        try:
            try:
                openpyxl.load_workbook(ruta_tmp, data_only=True)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=_mensaje_no_xlsx(nombre)) from exc

            inicio = time.monotonic()
            lineas = procesar_mto(ruta_tmp, app.state.puerto, POLITICAS_POR_DEFECTO)
            segundos = time.monotonic() - inicio
        finally:
            ruta_tmp.unlink(missing_ok=True)

        sesion_id = uuid.uuid4().hex
        app.state.sesiones[sesion_id] = lineas

        return {
            "sesion_id": sesion_id,
            "resumen": _construir_resumen(lineas, segundos, app.state.puerto),
            "lineas": [_linea_a_dict(l) for l in lineas],
        }

    @app.post("/api/resolver")
    def resolver(peticion: PeticionResolver):
        lineas = app.state.sesiones.get(peticion.sesion_id)
        if lineas is None:
            raise HTTPException(status_code=404,
                                detail=_mensaje_sesion_no_encontrada(peticion.sesion_id))
        if peticion.atributo not in ATRIBUTOS:
            raise HTTPException(status_code=400,
                                detail=_mensaje_atributo_invalido(peticion.atributo))
        linea = next((l for l in lineas if l.id == peticion.linea_id), None)
        if linea is None:
            raise HTTPException(status_code=404,
                                detail=_mensaje_linea_no_encontrada(peticion.linea_id))

        linea_actualizada = _resolver_celda(linea, peticion.atributo, peticion.valor)
        return _linea_a_dict(linea_actualizada)

    @app.get("/api/exportar")
    def exportar(sesion_id: str):
        lineas = app.state.sesiones.get(sesion_id)
        if lineas is None:
            raise HTTPException(status_code=404, detail=_mensaje_sesion_no_encontrada(sesion_id))

        filas = _agrupar_por_material_canonico(lineas)
        contenido = _construir_xlsx_exportacion(filas)
        return Response(
            content=contenido,
            media_type=_MEDIA_XLSX,
            headers={"Content-Disposition": 'attachment; filename="cola_de_compras.xlsx"'},
        )

    dist = directorio_front if directorio_front is not None else (_raiz_repo() / "front" / "dist")
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="front")
    else:
        @app.get("/", response_class=PlainTextResponse)
        def raiz():
            return _mensaje_front_no_compilado()

    return app
