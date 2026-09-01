"""Tests de PuertoGemini. Todos menos el marcado @pytest.mark.red corren con un cliente
falso inyectado, sin red -- ejercitan el calculo de spans, los descartes, la cache y la
contabilidad de tokens, que es la logica propia de este puerto (lo que NO viene ya probado
por el SDK de google-genai)."""
import json
from pathlib import Path

import pytest

from motor.invariantes import hay_solape
from motor.lectura_mto import leer_mto
from motor.puerto_gemini import ErrorSinRed, PuertoGemini

RUTA_MTO = Path("datos/MTO_tornilleria.xlsx")


class _UsoFalso:
    def __init__(self, prompt: int, candidatos: int):
        self.prompt_token_count = prompt
        self.candidates_token_count = candidatos


class _RespuestaFalsa:
    def __init__(self, datos: dict, prompt: int = 10, candidatos: int = 5):
        self.text = json.dumps(datos)
        self.usage_metadata = _UsoFalso(prompt, candidatos)


class _ModelosFalsos:
    """Sustituye a `cliente.models`. Cada llamada consume la siguiente respuesta preparada,
    para poder verificar cuantas llamadas reales se hicieron (contador `llamadas`)."""
    def __init__(self, respuestas: list[_RespuestaFalsa]):
        self._respuestas = list(respuestas)
        self.llamadas = 0

    def generate_content(self, model, contents, config):
        self.llamadas += 1
        if not self._respuestas:
            raise AssertionError("PuertoGemini llamo al modelo mas veces de las esperadas")
        return self._respuestas.pop(0)


class _ClienteFalso:
    def __init__(self, respuestas: list[_RespuestaFalsa]):
        self.models = _ModelosFalsos(respuestas)


def _puerto(tmp_path: Path, respuestas: list[_RespuestaFalsa], **kwargs) -> tuple[PuertoGemini, _ClienteFalso]:
    cliente = _ClienteFalso(respuestas)
    puerto = PuertoGemini(cliente=cliente, directorio_cache=tmp_path / "cache_llm", **kwargs)
    return puerto, cliente


# --------------------------------------------------------------------------
# Verificacion de literales: un trozo que el modelo se inventa se descarta.
# --------------------------------------------------------------------------

def test_trozo_no_literal_se_descarta(tmp_path):
    texto = "BOLT M16 with NUT and WASHER"
    datos = {
        "elementos": [
            {"tipo_indicado": "BOLT", "texto": "BOLT M16"},
            {"tipo_indicado": "NUT", "texto": "NUT DE ACERO INOXIDABLE"},  # no aparece literal
        ],
        "ambito_fila": [],
        "conectores": ["with", "and"],
    }
    puerto, _ = _puerto(tmp_path, [_RespuestaFalsa(datos)])

    seg = puerto.segmentar(texto)

    assert [e.tipo_indicado for e in seg.elementos] == ["BOLT"]
    assert len(puerto.descartes) == 1
    assert puerto.descartes[0]["trozo"] == "NUT DE ACERO INOXIDABLE"
    assert puerto.descartes[0]["motivo"] == "NO_LITERAL"


# --------------------------------------------------------------------------
# Los spans calculados apuntan al texto correcto.
# --------------------------------------------------------------------------

def test_spans_calculados_apuntan_al_texto_correcto(tmp_path):
    texto = "BOLT M16 with NUT and WASHER"
    datos = {
        "elementos": [
            {"tipo_indicado": "BOLT", "texto": "BOLT M16"},
            {"tipo_indicado": "NUT", "texto": "NUT"},
            {"tipo_indicado": "WASHER", "texto": "WASHER"},
        ],
        "ambito_fila": [],
        "conectores": ["with", "and"],
    }
    puerto, _ = _puerto(tmp_path, [_RespuestaFalsa(datos)])

    seg = puerto.segmentar(texto)

    assert len(seg.elementos) == 3
    literales_esperados = ["BOLT M16", "NUT", "WASHER"]
    for elemento, literal in zip(seg.elementos, literales_esperados):
        ini, fin = elemento.span
        assert texto[ini:fin] == literal


# --------------------------------------------------------------------------
# Dos trozos identicos no colapsan en el mismo tramo.
# --------------------------------------------------------------------------

def test_dos_trozos_iguales_no_solapan(tmp_path):
    texto = "TUERCA M10 y TUERCA M10"
    datos = {
        "elementos": [
            {"tipo_indicado": "TUERCA", "texto": "TUERCA M10"},
            {"tipo_indicado": "TUERCA", "texto": "TUERCA M10"},
        ],
        "ambito_fila": [],
        "conectores": ["y"],
    }
    puerto, _ = _puerto(tmp_path, [_RespuestaFalsa(datos)])

    seg = puerto.segmentar(texto)

    assert len(seg.elementos) == 2
    assert hay_solape(seg) is False
    span_a, span_b = (e.span for e in seg.elementos)
    assert span_a != span_b
    assert span_a[1] <= span_b[0]
    assert texto[span_a[0]:span_a[1]] == "TUERCA M10"
    assert texto[span_b[0]:span_b[1]] == "TUERCA M10"


# --------------------------------------------------------------------------
# La cache evita la segunda llamada.
# --------------------------------------------------------------------------

def test_cache_evita_la_segunda_llamada(tmp_path):
    texto = "TORNILLO M10"
    datos = {
        "elementos": [{"tipo_indicado": "TORNILLO", "texto": "TORNILLO M10"}],
        "ambito_fila": [],
        "conectores": [],
    }
    puerto, cliente = _puerto(tmp_path, [_RespuestaFalsa(datos)])

    primera = puerto.segmentar(texto)
    segunda = puerto.segmentar(texto)

    assert cliente.models.llamadas == 1
    assert [e.tipo_indicado for e in primera.elementos] == [e.tipo_indicado for e in segunda.elementos]
    assert [e.span for e in primera.elementos] == [e.span for e in segunda.elementos]


def test_cache_persiste_para_una_instancia_nueva(tmp_path):
    """La cache es en disco, no en memoria: una segunda instancia sobre el mismo directorio
    tampoco debe llamar al modelo."""
    texto = "TORNILLO M10"
    datos = {
        "elementos": [{"tipo_indicado": "TORNILLO", "texto": "TORNILLO M10"}],
        "ambito_fila": [],
        "conectores": [],
    }
    directorio = tmp_path / "cache_llm"
    puerto1, cliente1 = _puerto(tmp_path, [_RespuestaFalsa(datos)])
    puerto1.segmentar(texto)

    cliente2 = _ClienteFalso([])  # sin respuestas preparadas: si llama, revienta
    puerto2 = PuertoGemini(cliente=cliente2, directorio_cache=directorio)
    seg2 = puerto2.segmentar(texto)

    assert cliente2.models.llamadas == 0
    assert [e.tipo_indicado for e in seg2.elementos] == ["TORNILLO"]


# --------------------------------------------------------------------------
# El contador de tokens suma a traves de llamadas distintas.
# --------------------------------------------------------------------------

def test_contador_de_tokens_suma(tmp_path):
    datos1 = {
        "elementos": [{"tipo_indicado": "TORNILLO", "texto": "TORNILLO M10"}],
        "ambito_fila": [], "conectores": [],
    }
    datos2 = {
        "elementos": [{"tipo_indicado": "TUERCA", "texto": "TUERCA M10"}],
        "ambito_fila": [], "conectores": [],
    }
    puerto, cliente = _puerto(tmp_path, [
        _RespuestaFalsa(datos1, prompt=100, candidatos=20),
        _RespuestaFalsa(datos2, prompt=50, candidatos=10),
    ])

    puerto.segmentar("TORNILLO M10")
    puerto.segmentar("TUERCA M10")  # texto distinto: no hay hit de cache

    assert cliente.models.llamadas == 2
    assert puerto.tokens_prompt_acumulados == 150
    assert puerto.tokens_candidatos_acumulados == 30
    assert len(puerto.latencias_s) == 2
    assert all(l >= 0 for l in puerto.latencias_s)


def test_coste_estimado_con_precios_por_defecto(tmp_path):
    datos = {
        "elementos": [{"tipo_indicado": "TORNILLO", "texto": "TORNILLO M10"}],
        "ambito_fila": [], "conectores": [],
    }
    puerto, _ = _puerto(tmp_path, [_RespuestaFalsa(datos, prompt=1_000_000, candidatos=1_000_000)])

    puerto.segmentar("TORNILLO M10")

    # gemini-3.7-flash: 0.75 por millon de entrada + 3.75 por millon de salida.
    assert puerto.coste_estimado() == pytest.approx(0.75 + 3.75)


def test_coste_sin_precio_configurado_para_el_modelo_lanza_error_claro(tmp_path):
    datos = {
        "elementos": [{"tipo_indicado": "TORNILLO", "texto": "TORNILLO M10"}],
        "ambito_fila": [], "conectores": [],
    }
    puerto, _ = _puerto(tmp_path, [_RespuestaFalsa(datos)], modelo="gemini-3.5-flash-lite")

    puerto.segmentar("TORNILLO M10")

    with pytest.raises(ValueError):
        puerto.coste_estimado()


# --------------------------------------------------------------------------
# Reintento con espera creciente ante el 429.
# --------------------------------------------------------------------------

class _ErrorDeCuota(Exception):
    def __init__(self, code: int):
        super().__init__(f"{code} RESOURCE_EXHAUSTED")
        self.code = code


class _ModelosConFallosDeCuota:
    def __init__(self, fallos_429: int, respuesta_final: _RespuestaFalsa):
        self.fallos_429 = fallos_429
        self.respuesta_final = respuesta_final
        self.llamadas = 0

    def generate_content(self, model, contents, config):
        self.llamadas += 1
        if self.llamadas <= self.fallos_429:
            raise _ErrorDeCuota(429)
        return self.respuesta_final


def test_reintenta_ante_429_y_acaba_devolviendo_la_segmentacion(tmp_path, monkeypatch):
    esperas = []
    monkeypatch.setattr("motor.puerto_gemini.time.sleep", lambda s: esperas.append(s))

    datos = {
        "elementos": [{"tipo_indicado": "TORNILLO", "texto": "TORNILLO M10"}],
        "ambito_fila": [], "conectores": [],
    }
    modelos = _ModelosConFallosDeCuota(fallos_429=2, respuesta_final=_RespuestaFalsa(datos))
    cliente = _ClienteFalso([])
    cliente.models = modelos
    puerto = PuertoGemini(cliente=cliente, directorio_cache=tmp_path / "cache_llm",
                          espera_base_s=1.0, max_reintentos=5)

    seg = puerto.segmentar("TORNILLO M10")

    assert modelos.llamadas == 3
    assert [e.tipo_indicado for e in seg.elementos] == ["TORNILLO"]
    assert esperas == [1.0, 2.0]  # espera creciente: base * 2**intento


def test_agota_reintentos_y_sin_cache_lanza_error_sin_red(tmp_path, monkeypatch):
    monkeypatch.setattr("motor.puerto_gemini.time.sleep", lambda s: None)
    modelos = _ModelosConFallosDeCuota(fallos_429=99, respuesta_final=_RespuestaFalsa({
        "elementos": [], "ambito_fila": [], "conectores": [],
    }))
    cliente = _ClienteFalso([])
    cliente.models = modelos
    puerto = PuertoGemini(cliente=cliente, directorio_cache=tmp_path / "cache_llm",
                          espera_base_s=0.01, max_reintentos=2)

    with pytest.raises(ErrorSinRed):
        puerto.segmentar("TORNILLO M10")

    assert modelos.llamadas == 3  # intento inicial + 2 reintentos


# --------------------------------------------------------------------------
# Modo sin red: ni clave ni cache -> error claro, nunca una segmentacion inventada.
# --------------------------------------------------------------------------

def test_sin_clave_y_sin_cache_lanza_error_claro(tmp_path, monkeypatch):
    monkeypatch.setattr(PuertoGemini, "_resolver_clave_api", lambda self: None)

    puerto = PuertoGemini(directorio_cache=tmp_path / "cache_llm")

    with pytest.raises(ErrorSinRed):
        puerto.segmentar("UN TEXTO CUALQUIERA NUNCA VISTO")


def test_sin_clave_pero_con_cache_no_lanza(tmp_path, monkeypatch):
    """Requisito 5: si no hay clave pero SI hay entrada en cache, se usa la cache."""
    monkeypatch.setattr(PuertoGemini, "_resolver_clave_api", lambda self: None)
    directorio = tmp_path / "cache_llm"

    # Primero se llena la cache con un cliente falso (simulando una corrida anterior con clave).
    datos = {
        "elementos": [{"tipo_indicado": "TORNILLO", "texto": "TORNILLO M10"}],
        "ambito_fila": [], "conectores": [],
    }
    cliente = _ClienteFalso([_RespuestaFalsa(datos)])
    puerto_con_clave = PuertoGemini(cliente=cliente, directorio_cache=directorio)
    puerto_con_clave.segmentar("TORNILLO M10")

    # Ahora, sin clave y sin cliente inyectado, la misma cache debe bastar.
    puerto_sin_clave = PuertoGemini(directorio_cache=directorio)
    seg = puerto_sin_clave.segmentar("TORNILLO M10")

    assert [e.tipo_indicado for e in seg.elementos] == ["TORNILLO"]


# --------------------------------------------------------------------------
# Prueba de humo real. NO corre por defecto (ver tests/conftest.py): solo con --red.
# --------------------------------------------------------------------------

@pytest.mark.red
def test_fila_uno_da_tres_elementos_de_verdad():
    filas = leer_mto(RUTA_MTO)
    fila_uno = next(f for f in filas if f.item == 1)

    puerto = PuertoGemini()
    seg = puerto.segmentar(fila_uno.descripcion)

    assert len(seg.elementos) == 3
