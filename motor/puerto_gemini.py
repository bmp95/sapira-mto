"""Tarea 13. El puerto real: donde el segmentador deja de leer un guion (`datos/guion_falso.py`)
y empieza a leer texto de verdad, via la API de Gemini (paquete `google-genai`).

Decision de diseno (obligatoria, no discrecional): al modelo se le pide TEXTO LITERAL, nunca
una posicion. El puerto localiza cada trozo devuelto dentro del texto de entrada con
`str.find` y calcula el `span` el mismo. Si un trozo no aparece literalmente en el texto de
origen, se descarta ese elemento y se registra el motivo (log + `self.descartes`) -- nunca se
inventa una posicion. Es a proposito: si le pidieramos el span al modelo, podria devolver una
posicion que no corresponde y la invariante de verificacion de literales (`verificar_literal`
en motor/invariantes.py) quedaria hueca. Pidiendo el texto y buscandolo nosotros, o esta o no
esta.

El prompt de sistema (`INSTRUCCION_SISTEMA`) y el esquema de salida (`ESQUEMA_SEGMENTACION`)
son los que ya se probaron y funcionaron -- se reproducen aqui tal cual, sin retocar una
palabra. El prompt no menciona catalogos, calidades, acabados ni normas: el modelo dice QUE
pone, el codigo (motor/pipeline.py) decide QUE SIGNIFICA.

La clave nunca se imprime ni se registra: los mensajes de error solo describen el fallo del
lado del cliente (falta de clave, ausencia de cache), nunca el valor de la clave ni la
respuesta cruda de un fallo de autenticacion.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path

import httpx
from google import genai
from google.genai import types

from motor.invariantes import hay_solape
from motor.modelos import Elemento, Segmentacion

_LOG = logging.getLogger(__name__)

MODELO_POR_DEFECTO = "gemini-3.7-flash"

# Codigos HTTP que se reintentan: 429 (limite de peticiones, nivel gratuito) y los 5xx que
# senalan un fallo transitorio del lado del servidor. NO incluye 4xx que no se van a
# arreglar solos (401 clave invalida, 400 peticion mal formada, etc.): esos deben salir a
# la primera con su mensaje, no esconderse detras de reintentos que nunca van a funcionar.
_CODIGOS_HTTP_REINTENTABLES = {429, 500, 502, 503, 504}


def _es_error_transitorio(exc: Exception) -> bool:
    """Errores que vale la pena reintentar: 429/5xx del lado de la API, o un corte de
    transporte (desconexion del servidor, timeout, fallo de conexion -- `httpx.TransportError`
    cubre las tres). Todo lo demas (clave invalida, peticion mal formada, cualquier otro 4xx)
    no es transitorio: reintentarlo no lo arregla, asi que sale a la primera."""
    codigo = getattr(exc, "code", None)
    if codigo in _CODIGOS_HTTP_REINTENTABLES:
        return True
    return isinstance(exc, httpx.TransportError)

# Precios publicados por Google (precio de introduccion), en la unidad que se configure --
# el metodo `coste_estimado` no hace conversion de divisa alguna, multiplica tal cual. Solo
# se incluye el modelo para el que el pliego dio precio; anadir aqui el de
# `gemini-3.5-flash-lite` (o cualquier otro) antes de pedir coste sobre el, para no inventar
# un numero que nadie ha dado.
TABLA_PRECIOS_POR_DEFECTO: dict[str, dict[str, float]] = {
    "gemini-3.7-flash": {"entrada": 0.75, "salida": 3.75},  # por millon de tokens
}

# Instruccion de sistema que funciono en la prueba de humo. Reproducida literal: ni una
# palabra distinta, ni una tilde anadida (no las lleva en el original). No menciona
# catalogos, calidades, acabados ni normas -- y no puede hacerlo.
INSTRUCCION_SISTEMA = (
    "Partes una linea de un despiece de tornilleria en los elementos fisicos que describe.\n"
    "Cada elemento es una pieza que se compra por separado.\n"
    "Devuelve, para cada elemento, el sustantivo tal como aparece y el TROZO LITERAL de texto "
    "que le pertenece.\n"
    "En ambito_fila pon los trozos que describen la fila entera y no estan pegados a ningun "
    "elemento.\n"
    "En conectores pon las palabras de union.\n"
    "Copia los trozos LITERALMENTE del texto de entrada. No normalices, no traduzcas, no "
    "interpretes, no anadas nada."
)

# Esquema de salida estructurada que funciono en la prueba de humo. Reproducido literal.
ESQUEMA_SEGMENTACION: dict = {
    "type": "OBJECT",
    "properties": {
        "elementos": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "tipo_indicado": {"type": "STRING"},
                    "texto": {"type": "STRING"},
                },
                "required": ["tipo_indicado", "texto"],
            },
        },
        "ambito_fila": {"type": "ARRAY", "items": {"type": "STRING"}},
        "conectores": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["elementos", "ambito_fila", "conectores"],
}


class ErrorSinRed(RuntimeError):
    """No hay forma de responder: falta la clave, la llamada fallo, y no hay cache.

    Nunca se lanza con el valor de la clave dentro del mensaje.
    """


def _raiz_repo() -> Path:
    return Path(__file__).resolve().parents[1]


class PuertoGemini:
    """Implementa `motor.puerto_llm.PuertoLLM` contra la API real de Gemini.

    `cliente`, si se pasa, sustituye por completo al `genai.Client` real -- es el punto de
    inyeccion que usan los tests para ejercitar toda la logica (cache, spans, descartes,
    contabilidad de tokens, reintentos) sin red. Debe exponer `.models.generate_content(model=,
    contents=, config=)` devolviendo un objeto con `.text` (JSON) y `.usage_metadata` (con
    `.prompt_token_count` y `.candidates_token_count`), igual que el `genai.Client` real.
    """

    def __init__(
        self,
        modelo: str = MODELO_POR_DEFECTO,
        *,
        cliente=None,
        directorio_cache: Path | None = None,
        limite_concurrencia: int = 5,
        max_reintentos: int = 5,
        espera_base_s: float = 2.0,
        tabla_precios: dict[str, dict[str, float]] | None = None,
    ):
        self.modelo = modelo
        self.directorio_cache = directorio_cache or (_raiz_repo() / ".cache_llm")
        self.limite_concurrencia = limite_concurrencia
        self.max_reintentos = max_reintentos
        self.espera_base_s = espera_base_s
        self.tabla_precios = tabla_precios if tabla_precios is not None else dict(TABLA_PRECIOS_POR_DEFECTO)

        self._api_key = self._resolver_clave_api()
        self._semaforo = threading.Semaphore(limite_concurrencia)
        self._config = types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=ESQUEMA_SEGMENTACION,
            system_instruction=INSTRUCCION_SISTEMA,
        )

        if cliente is not None:
            self._cliente = cliente
        elif self._api_key is not None:
            self._cliente = genai.Client(api_key=self._api_key)
        else:
            self._cliente = None

        # Contabilidad acumulada (todas las llamadas hechas por esta instancia).
        self.tokens_prompt_acumulados = 0
        self.tokens_candidatos_acumulados = 0
        self.latencias_s: list[float] = []
        # Trozos que el modelo devolvio y que se descartaron (no literales o solapados),
        # con el motivo -- para poder inspeccionar el porque sin tener que leer logs.
        self.descartes: list[dict] = []

    # ------------------------------------------------------------------
    # Resolucion de la clave. Nunca se imprime ni se registra.
    # ------------------------------------------------------------------

    def _resolver_clave_api(self) -> str | None:
        clave = os.environ.get("GEMINI_API_KEY")
        if clave:
            return clave.strip() or None
        ruta_env = _raiz_repo() / ".env"
        if not ruta_env.exists():
            return None
        for linea in ruta_env.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            nombre, _, valor = linea.partition("=")
            if nombre.strip() != "GEMINI_API_KEY":
                continue
            valor = valor.strip().strip('"').strip("'")
            return valor or None
        return None

    # ------------------------------------------------------------------
    # Cache en disco. Clave: hash(modelo, texto). Antes de llamar, se mira la cache.
    # ------------------------------------------------------------------

    def _clave_cache(self, texto: str) -> str:
        material = f"{self.modelo}\x1f{texto}".encode()
        return hashlib.sha256(material).hexdigest()

    def _ruta_cache(self, clave: str) -> Path:
        return self.directorio_cache / f"{clave}.json"

    def _leer_cache(self, clave: str) -> dict | None:
        ruta = self._ruta_cache(clave)
        if not ruta.exists():
            return None
        with ruta.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _guardar_cache(self, clave: str, texto: str, respuesta: dict, uso: dict, latencia_s: float) -> None:
        self.directorio_cache.mkdir(parents=True, exist_ok=True)
        contenido = {
            "modelo": self.modelo,
            "texto": texto,
            "respuesta": respuesta,
            "uso": uso,
            "latencia_s": latencia_s,
        }
        with self._ruta_cache(clave).open("w", encoding="utf-8") as f:
            json.dump(contenido, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Llamada al modelo: concurrencia limitada + reintento con espera creciente ante
    # errores transitorios (429, 5xx, cortes de transporte -- ver `_es_error_transitorio`).
    # ------------------------------------------------------------------

    def _llamar_modelo(self, texto: str) -> tuple[dict, dict, float]:
        with self._semaforo:
            intento = 0
            while True:
                inicio = time.monotonic()
                try:
                    respuesta = self._cliente.models.generate_content(
                        model=self.modelo, contents=texto, config=self._config)
                except Exception as exc:
                    if _es_error_transitorio(exc) and intento < self.max_reintentos:
                        espera = self.espera_base_s * (2 ** intento)
                        _LOG.warning(
                            "Gemini fallo con un error transitorio (%s); reintento %d tras %.1fs",
                            type(exc).__name__, intento + 1, espera)
                        time.sleep(espera)
                        intento += 1
                        continue
                    raise
                latencia_s = time.monotonic() - inicio
                datos = json.loads(respuesta.text)
                uso_meta = respuesta.usage_metadata
                uso = {
                    "prompt_token_count": uso_meta.prompt_token_count or 0,
                    "candidates_token_count": uso_meta.candidates_token_count or 0,
                }
                return datos, uso, latencia_s

    # ------------------------------------------------------------------
    # Construccion de la Segmentacion a partir del JSON: texto literal -> span por str.find.
    # ------------------------------------------------------------------

    def _localizar(self, texto: str, trozo: str, ultima_posicion: dict[str, int]) -> tuple[int, int] | None:
        """Busca `trozo` en `texto`. Si el mismo trozo ya aparecio antes, avanza la busqueda
        desde el final de su span anterior -- asi dos apariciones identicas ("TUERCA M10" dos
        veces en la misma fila) no colapsan sobre el mismo tramo."""
        inicio = ultima_posicion.get(trozo, 0)
        idx = texto.find(trozo, inicio)
        if idx == -1:
            return None
        fin = idx + len(trozo)
        ultima_posicion[trozo] = fin
        return (idx, fin)

    def _registrar_descarte(self, trozo: str, motivo: str, tipo_indicado: str | None) -> None:
        self.descartes.append({"trozo": trozo, "motivo": motivo, "tipo_indicado": tipo_indicado})
        _LOG.warning("PuertoGemini descarta un trozo (%s): %r", motivo, trozo)

    def _construir_segmentacion(self, texto: str, datos: dict) -> Segmentacion:
        ultima_posicion: dict[str, int] = {}

        elementos: list[Elemento] = []
        for item in datos["elementos"]:
            trozo = item["texto"]
            span = self._localizar(texto, trozo, ultima_posicion)
            if span is None:
                self._registrar_descarte(trozo, "NO_LITERAL", item["tipo_indicado"])
                continue
            candidata = Elemento(tipo_indicado=item["tipo_indicado"], span=span)
            # Comprobacion explicita con hay_solape antes de aceptar: si este tramo se solapa
            # con uno ya aceptado, se descarta -- nunca se devuelve una Segmentacion con
            # elementos solapados.
            if hay_solape(Segmentacion(elementos=[*elementos, candidata])):
                self._registrar_descarte(trozo, "SOLAPE", item["tipo_indicado"])
                continue
            elementos.append(candidata)

        ambito_fila: list[tuple[int, int]] = []
        for trozo in datos["ambito_fila"]:
            span = self._localizar(texto, trozo, ultima_posicion)
            if span is None:
                self._registrar_descarte(trozo, "NO_LITERAL", None)
                continue
            ambito_fila.append(span)

        conectores: list[tuple[int, int]] = []
        for trozo in datos["conectores"]:
            span = self._localizar(texto, trozo, ultima_posicion)
            if span is None:
                self._registrar_descarte(trozo, "NO_LITERAL", None)
                continue
            conectores.append(span)

        return Segmentacion(elementos=elementos, ambito_fila=ambito_fila, conectores=conectores)

    # ------------------------------------------------------------------
    # PuertoLLM
    # ------------------------------------------------------------------

    def segmentar(self, texto: str) -> Segmentacion:
        clave = self._clave_cache(texto)
        entrada = self._leer_cache(clave)
        if entrada is not None:
            return self._construir_segmentacion(texto, entrada["respuesta"])

        if self._cliente is None:
            raise ErrorSinRed(
                f"No hay GEMINI_API_KEY (ni en el entorno ni en .env) y no hay cache en disco "
                f"para este texto (clave {clave}). No se puede segmentar sin red.")

        try:
            datos, uso, latencia_s = self._llamar_modelo(texto)
        except Exception as exc:
            raise ErrorSinRed(
                f"La llamada a Gemini fallo y no hay cache en disco para este texto "
                f"(clave {clave}): {type(exc).__name__}: {exc}") from exc

        self._guardar_cache(clave, texto, datos, uso, latencia_s)
        self.tokens_prompt_acumulados += uso["prompt_token_count"]
        self.tokens_candidatos_acumulados += uso["candidates_token_count"]
        self.latencias_s.append(latencia_s)
        return self._construir_segmentacion(texto, datos)

    def extraer(self, tramo: str) -> list[dict]:
        # Fuera de alcance de la Tarea 13: la extraccion por elemento es codigo determinista
        # (motor/pipeline.py: regex + motor/catalogos.emparejar contra las tablas cerradas),
        # no una llamada al modelo -- ver la cabecera de motor/pipeline.py. No se implementa
        # con un valor por defecto silencioso (lista vacia) porque eso ocultaria que nadie ha
        # construido esta ruta todavia.
        raise NotImplementedError(
            "PuertoGemini.extraer no esta implementado: la extraccion por elemento es "
            "codigo determinista (motor/pipeline.py), no una llamada al modelo (Tarea 13 "
            "solo cubre segmentar).")

    # ------------------------------------------------------------------
    # Coste
    # ------------------------------------------------------------------

    def coste_estimado(self) -> float:
        """Coste acumulado segun `self.tabla_precios` (unidad por millon de tokens). El
        metodo no convierte divisas: multiplica los tokens acumulados por los precios tal
        como esten configurados para `self.modelo`."""
        precios = self.tabla_precios.get(self.modelo)
        if precios is None:
            raise ValueError(
                f"No hay precio configurado para el modelo '{self.modelo}' en tabla_precios; "
                f"anadelo antes de pedir coste (cero valores por defecto silenciosos).")
        return ((self.tokens_prompt_acumulados / 1_000_000) * precios["entrada"]
                + (self.tokens_candidatos_acumulados / 1_000_000) * precios["salida"])
