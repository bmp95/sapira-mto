# Reconciliación de MTOs · Tornillería — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir cada fila de un MTO de tornillería en una línea por material comprable, con siete atributos normalizados, procedencia y confianza por celda, y estado `RESUELTA` / `REVISION_MANUAL`.

**Architecture:** Cinco etapas; sólo una usa modelo. Saneado (código) → segmentación (LLM ×3) → extracción por elemento (LLM, ve sólo su tramo) → normalización (100 % tablas) → validación y estado (código). La confianza la calcula el código como mínimo de cuatro factores medidos; `RESUELTA` es exactamente `confianza == 100`.

**Tech Stack:** Python 3.12, pydantic v2, openpyxl, openai, FastAPI, pytest · Front: Vite + React + TypeScript + Tailwind + shadcn/ui + TanStack Table.

**Spec:** `docs/superpowers/specs/2026-08-31-reconciliacion-mto-design.md`

## Global Constraints

- Python 3.12. Todo el código y los identificadores en castellano sin tildes (`confianza_linea`, no `confianza_línea`). Los comentarios y textos de usuario sí llevan tildes.
- **El modelo nunca ve los catálogos.** Ni en el prompt del segmentador ni en el del extractor.
- **El modelo nunca reporta confianza.** La calcula el código.
- **Cero coincidencia difusa.** Nada de Levenshtein, `difflib`, ni "el más parecido". Emparejamiento por token, más largo primero.
- **Sin valores por defecto.** Un campo ausente es `AUSENTE`, nunca `""` ni `None` silencioso.
- Toda celda lleva `procedencia`. Una celda sin procedencia lanza excepción, no advertencia.
- Ningún secreto en el repositorio. La clave se lee de `os.environ["OPENAI_API_KEY"]`.
- Commits en castellano, presente de indicativo: `añade`, `corrige`, `mide`.

---

## Estructura de ficheros

```
motor/
  modelos.py       Tipos pydantic: Procedencia, Valor, Elemento, Segmentacion, LineaSalida, Motivo
  saneado.py       Etapa 1: unicode, comillas, forma canonica de norma
  lectura_mto.py   xlsx -> [FilaMTO]
  catalogos.py     Las 4 tablas + emparejador por token
  derivaciones.py  calidad->material, norma->nombre
  puerto_llm.py    Protocol PuertoLLM + PuertoFalso + PuertoOpenAI
  segmentador.py   A1: parte la fila, vota 3 pasadas
  extractor.py     A2: literales por elemento, ve solo su tramo
  invariantes.py   Las 8 comprobaciones estructurales
  coherencias.py   Las 6 comprobaciones cruzadas de dominio
  cantidades.py    Multiplicadores del set
  confianza.py     Los 4 factores y su minimo
  validador.py     Obligatoriedad, estado, motivos
  pipeline.py      Orquesta las 5 etapas
api/
  servidor.py      FastAPI: POST /api/procesar, estaticos del front
evaluacion/
  arnes.py         Metricas contra el gold set
  ablaciones.py    Ejecuta el arnes con componentes desactivados
  informe.py       Vuelca tablas en markdown
front/             Vite + React + shadcn + TanStack Table
datos/
  gold_set.csv     Anotacion manual (30 lineas)
  corpus_estres.csv
tests/
```

Cada fichero del motor tiene una responsabilidad y se prueba solo. `pipeline.py` es el único que conoce a todos.

---

## Tarea 1: Andamiaje y modelos de datos

**Files:**
- Create: `pyproject.toml`, `motor/__init__.py`, `motor/modelos.py`, `tests/__init__.py`, `tests/test_modelos.py`

**Interfaces:**
- Produces: `Procedencia` (enum), `Valor`, `Elemento`, `Segmentacion`, `Motivo`, `LineaSalida`, `Estado` (enum)

- [ ] **Paso 1: Crear `pyproject.toml`**

```toml
[project]
name = "sapira-mto"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pydantic>=2.7", "openpyxl>=3.1", "openai>=1.40", "fastapi>=0.111", "uvicorn>=0.30"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Instalar: `pip install -e ".[dev]"`

- [ ] **Paso 2: Escribir el test que falla** — `tests/test_modelos.py`

```python
import pytest
from motor.modelos import Procedencia, Valor, LineaSalida, Estado


def test_valor_extraido_exige_span_y_literal():
    v = Valor(valor="TORNILLO", literal="BOLT", span=(0, 4), procedencia=Procedencia.EXTRAIDO)
    assert v.confianza_procedencia == 100


def test_valor_inferido_puntua_70():
    v = Valor(valor="130 mm", literal="130", span=(20, 23), procedencia=Procedencia.INFERIDO)
    assert v.confianza_procedencia == 70


def test_valor_ausente_no_exige_span():
    v = Valor(valor=None, literal=None, span=None, procedencia=Procedencia.AUSENTE)
    assert v.confianza_procedencia is None


def test_extraido_sin_span_revienta():
    with pytest.raises(ValueError, match="span"):
        Valor(valor="TORNILLO", literal="BOLT", span=None, procedencia=Procedencia.EXTRAIDO)


def test_estado_se_deriva_de_la_confianza():
    linea = LineaSalida.vacia(id="L001", fila_origen=1, cantidad=40)
    linea.confianza = 100
    assert linea.estado == Estado.RESUELTA
    linea.confianza = 99
    assert linea.estado == Estado.REVISION_MANUAL
```

- [ ] **Paso 3: Ejecutar y ver que falla**

Run: `pytest tests/test_modelos.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'motor.modelos'`

- [ ] **Paso 4: Implementar `motor/modelos.py`**

```python
"""Tipos del dominio. El estado nunca se escribe: se deriva de la confianza."""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, model_validator

ATRIBUTOS = ("nombre", "material", "calidad", "medida", "longitud", "norma", "acabado")


class Procedencia(str, Enum):
    EXTRAIDO = "EXTRAIDO"
    DERIVADO = "DERIVADO"
    INFERIDO = "INFERIDO"
    AUSENTE = "AUSENTE"


class Estado(str, Enum):
    RESUELTA = "RESUELTA"
    REVISION_MANUAL = "REVISION_MANUAL"


PUNTOS_PROCEDENCIA = {
    Procedencia.EXTRAIDO: 100,
    Procedencia.DERIVADO: 100,
    Procedencia.INFERIDO: 70,
}


class Valor(BaseModel):
    valor: Optional[str] = None
    literal: Optional[str] = None
    span: Optional[tuple[int, int]] = None
    procedencia: Procedencia
    regla: Optional[str] = None
    confianza: Optional[int] = None
    factores: dict[str, int] = {}

    @model_validator(mode="after")
    def _exige_evidencia(self):
        if self.procedencia is Procedencia.EXTRAIDO and self.span is None:
            raise ValueError("un valor EXTRAIDO necesita span")
        if self.procedencia is Procedencia.DERIVADO and not self.regla:
            raise ValueError("un valor DERIVADO necesita regla")
        return self

    @property
    def confianza_procedencia(self) -> Optional[int]:
        return PUNTOS_PROCEDENCIA.get(self.procedencia)


class Elemento(BaseModel):
    tipo_indicado: str
    span: tuple[int, int]
    votos: int = 3


class Segmentacion(BaseModel):
    elementos: list[Elemento]
    ambito_fila: list[tuple[int, int]] = []
    conectores: list[tuple[int, int]] = []


class Motivo(BaseModel):
    codigo: str
    texto: str
    atributo: Optional[str] = None
    valor_propuesto: Optional[str] = None
    factor_limitante: Optional[str] = None


class LineaSalida(BaseModel):
    id: str
    fila_origen: int
    cantidad: int
    nombre: Valor
    material: Valor
    calidad: Valor
    medida: Valor
    longitud: Valor
    norma: Valor
    acabado: Valor
    confianza: int = 0
    motivos: list[Motivo] = []

    @classmethod
    def vacia(cls, id: str, fila_origen: int, cantidad: int) -> "LineaSalida":
        hueco = Valor(procedencia=Procedencia.AUSENTE)
        return cls(id=id, fila_origen=fila_origen, cantidad=cantidad,
                   **{a: hueco.model_copy() for a in ATRIBUTOS})

    @property
    def estado(self) -> Estado:
        return Estado.RESUELTA if self.confianza == 100 else Estado.REVISION_MANUAL

    def celdas(self) -> dict[str, Valor]:
        return {a: getattr(self, a) for a in ATRIBUTOS}
```

- [ ] **Paso 5: Ejecutar y ver que pasa**

Run: `pytest tests/test_modelos.py -v`
Expected: 5 passed

- [ ] **Paso 6: Commit**

```bash
git add pyproject.toml motor/ tests/
git commit -m "añade modelos de dominio con estado derivado de la confianza"
```

---

## Tarea 2: Lectura del MTO y saneado

**Files:**
- Create: `motor/saneado.py`, `motor/lectura_mto.py`, `tests/test_saneado.py`, `tests/test_lectura.py`

**Interfaces:**
- Produces: `sanear(texto: str) -> str`, `FilaMTO` (item, descripcion, material_col, medida_col, cantidad, unidad), `leer_mto(ruta: Path) -> list[FilaMTO]`

- [ ] **Paso 1: Test de saneado**

```python
from motor.saneado import sanear


def test_comillas_tipograficas_y_prima_a_recta():
    assert sanear('7/8″ X 130') == '7/8" X 130'
    assert sanear('“7/8”') == '"7/8"'


def test_colapsa_espacios():
    assert sanear("BOLT   DIN  933") == "BOLT DIN 933"


def test_forma_canonica_de_norma():
    assert sanear("BOLT DIN931 M20") == "BOLT DIN 931 M20"
    assert sanear("BOLT DIN-931 M20") == "BOLT DIN 931 M20"
    assert sanear("BOLT DIN 931 M20") == "BOLT DIN 931 M20"


def test_no_toca_el_resto():
    t = 'STUD BOLT 7/8" X 130 LG, ASTM A193, GR B7'
    assert sanear(t) == t
```

- [ ] **Paso 2: Ver que falla** — `pytest tests/test_saneado.py -v` → `ModuleNotFoundError`

- [ ] **Paso 3: Implementar `motor/saneado.py`**

```python
"""Etapa 1. Un MTO de un estudio externo no viene en ASCII limpio."""
import re
import unicodedata

_COMILLAS = {"“": '"', "”": '"', "″": '"', "′": "'",
             "‘": "'", "’": "'", "´": "'"}
_NORMA = re.compile(r"\b(DIN|ISO|ASME|ASTM|EN|MSS)[\s\-]*((?:SP[\s\-]*)?\d[\w\-]*)", re.I)


def sanear(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto)
    for malo, bueno in _COMILLAS.items():
        t = t.replace(malo, bueno)
    t = t.replace("Ø", "DIA ")
    t = _NORMA.sub(lambda m: f"{m.group(1).upper()} {m.group(2).upper()}", t)
    return re.sub(r"\s+", " ", t).strip()
```

- [ ] **Paso 4: Ver que pasa** — `pytest tests/test_saneado.py -v` → 4 passed

- [ ] **Paso 5: Test de lectura**

```python
from pathlib import Path
from motor.lectura_mto import leer_mto


def test_lee_las_quince_filas():
    filas = leer_mto(Path("datos/MTO_tornilleria.xlsx"))
    assert len(filas) == 15
    assert filas[0].item == 1
    assert filas[0].cantidad == 40
    assert "STUD BOLT" in filas[0].descripcion


def test_la_descripcion_llega_saneada():
    filas = leer_mto(Path("datos/MTO_tornilleria.xlsx"))
    assert "DIN 931" in filas[1].descripcion  # el fichero trae "DIN931"
```

- [ ] **Paso 6: Implementar `motor/lectura_mto.py`**

```python
"""xlsx -> filas. La cabecera esta en la fila 4; los datos empiezan en la 5."""
from pathlib import Path
from pydantic import BaseModel
import openpyxl
from motor.saneado import sanear


class FilaMTO(BaseModel):
    item: int
    descripcion: str
    material_col: str
    medida_col: str
    cantidad: int
    unidad: str


def leer_mto(ruta: Path) -> list[FilaMTO]:
    hoja = openpyxl.load_workbook(ruta, data_only=True).worksheets[0]
    filas: list[FilaMTO] = []
    for f in hoja.iter_rows(min_row=5, values_only=True):
        if f[0] is None:
            continue
        filas.append(FilaMTO(
            item=int(f[0]),
            descripcion=sanear(str(f[1] or "")),
            material_col=sanear(str(f[2] or "")),
            medida_col=sanear(str(f[3] or "")),
            cantidad=int(f[4] or 0),
            unidad=str(f[5] or ""),
        ))
    return filas
```

- [ ] **Paso 7: Ver que pasa y commit**

```bash
pytest tests/test_saneado.py tests/test_lectura.py -v
git add motor/saneado.py motor/lectura_mto.py tests/
git commit -m "añade lectura del MTO y saneado de entrada"
```

---

## Tarea 3: Catálogos y emparejador por token

Aquí viven las trampas. Es la tarea con más riesgo de fallo silencioso.

**Files:**
- Create: `motor/catalogos.py`, `tests/test_catalogos.py`

**Interfaces:**
- Produces: `NORMAS_DIN_ISO: dict[str,str]`, `GRUPOS_CALIDAD: dict[str,str]`, `CALIDADES: tuple[str,...]`, `ACABADOS: dict[str,str]`, `NOMBRES: dict[str,str]`, `emparejar(texto, tabla) -> list[tuple[str, str, tuple[int,int]]]`

- [ ] **Paso 1: Escribir los tests de trampa primero**

```python
from motor.catalogos import emparejar, ACABADOS, CALIDADES_ALIAS, NORMAS_DIN_ISO, normalizar_norma


def test_BL_no_casa_dentro_de_AUTOBLOCANTE():
    """DIN 985 es tuerca autoblocante. 'BL' es alias de PAVONADO."""
    t = "TUERCA AUTOBLOCANTE DIN 985 M12, 8.8, ZINCADA"
    hallados = {v for v, _, _ in emparejar(t, ACABADOS)}
    assert hallados == {"CINCADO"}


def test_ZP_no_se_come_YZP():
    assert {v for v, _, _ in emparejar("TORNILLO M10 YZP", ACABADOS)} == {"BICROMATADO"}
    assert {v for v, _, _ in emparejar("TORNILLO M10 ZP", ACABADOS)} == {"CINCADO"}


def test_calidad_10_no_sale_de_M10():
    t = "ARANDELA PLANA DIN 125 M10, ACERO, ZINCADA"
    assert emparejar(t, CALIDADES_ALIAS) == []


def test_calidad_8_no_sale_de_8_8():
    hallados = [v for v, _, _ in emparejar("TORNILLO DIN 933 M10 X 40, 8.8", CALIDADES_ALIAS)]
    assert hallados == ["8.8"]


def test_A4_70_gana_a_A4():
    t = "BOLT DIN 931 M12X60 A4-70 WITH NUT DIN 934 M12 A4-80"
    assert [v for v, _, _ in emparejar(t, CALIDADES_ALIAS)] == ["A4-70", "A4-80"]


def test_normalizacion_de_norma():
    assert normalizar_norma("DIN 933") == "ISO 4017"
    assert normalizar_norma("DIN 125 A") == "ISO 7089"
    assert normalizar_norma("DIN 975") == "DIN 975"   # sin equivalente: se conserva
    assert normalizar_norma("ASTM A193") == "ASTM A193"


def test_no_hay_coincidencia_difusa():
    assert normalizar_norma("DIN 9331") == "DIN 9331"  # NO es DIN 933
```

- [ ] **Paso 2: Ver que falla** — `pytest tests/test_catalogos.py -v`

- [ ] **Paso 3: Implementar `motor/catalogos.py`**

```python
"""Las cuatro tablas cerradas. Cero modelo, cero coincidencia difusa."""
import re

NORMAS_DIN_ISO = {
    "DIN 84": "ISO 1207", "DIN 440": "ISO 7094", "DIN 603": "ISO 8677",
    "DIN 912": "ISO 4762", "DIN 913": "ISO 4026", "DIN 916": "ISO 4029",
    "DIN 931": "ISO 4014", "DIN 933": "ISO 4017", "DIN 934": "ISO 4032",
    "DIN 935": "ISO 7035", "DIN 936": "ISO 4035", "DIN 960": "ISO 8765",
    "DIN 961": "ISO 1665", "DIN 963": "ISO 2009", "DIN 965": "ISO 7046",
    "DIN 980": "ISO 7042", "DIN 982": "ISO 7040", "DIN 985": "ISO 10511",
    "DIN 6923": "EN 1661", "DIN 7981 C-H": "ISO 7049", "DIN 7982 C-H": "ISO 7050",
    "DIN 7985": "ISO 7045", "DIN 7991": "ISO 10642", "DIN 9021": "ISO 7093",
    "DIN 125": "ISO 7089", "DIN 125 A": "ISO 7089",
}

GRUPOS_CALIDAD = {
    "A2": "G1", "A2-70": "G1", "18-8": "G1", "304": "G1",
    "A2-80": "G2",
    "A4": "G3", "A4-70": "G3", "316": "G3",
    "A4-80": "G4",
    "8.8": "G5", "GRADE 5": "G5", "GRADO 5": "G5",
    "10.9": "G6", "GRADE 8": "G6", "GRADO 8": "G6",
    "12.9": "G7", "8": "G8", "10": "G9",
    "100HV": "G10", "140HV": "G11", "160HV": "G12", "200HV": "G13", "300HV": "G14",
}
CALIDADES_ALIAS = {c: c for c in GRUPOS_CALIDAD}

ACABADOS = {
    "GEOMET": "GEOMET", "DACROMET": "DACROMET",
    "GALVANIZADO EN CALIENTE": "GALVANIZADO EN CALIENTE", "HOT DIP GALVANIZED": "GALVANIZADO EN CALIENTE",
    "HDG": "GALVANIZADO EN CALIENTE", "GALVA": "GALVANIZADO EN CALIENTE",
    "CINCADO": "CINCADO", "CINCADA": "CINCADO", "ZINCADO": "CINCADO", "ZINCADA": "CINCADO",
    "ZINC PLATED": "CINCADO", "ZN": "CINCADO", "ZP": "CINCADO",
    "PAVONADO": "PAVONADO", "BL": "PAVONADO", "NEGRO": "PAVONADO",
    "FOSFATADO": "FOSFATADO", "PHOSPHATED": "FOSFATADO",
    "BICROMATADO": "BICROMATADO", "YZP": "BICROMATADO", "YELLOW ZINC PLATED": "BICROMATADO",
}

NOMBRES = {
    "THREADED ROD": "VARILLA ROSCADA", "VARILLA ROSCADA": "VARILLA ROSCADA",
    "STUD BOLT": "ESPARRAGO", "STUD": "ESPARRAGO", "ESPARRAGO": "ESPARRAGO",
    "SCREW": "TORNILLO", "BOLT": "TORNILLO", "TORNILLO": "TORNILLO",
    "NUT": "TUERCA", "TUERCA": "TUERCA", "TUERCAS": "TUERCA",
    "WASHER": "ARANDELA", "ARANDELA": "ARANDELA", "ARANDELAS": "ARANDELA",
}

# Un token no puede estar pegado a letra, digito, punto o guion.
# Esto es lo que impide que 'BL' case dentro de AUTOBLOCANTE y que '10' salga de M10.
_ANTES = r"(?<![A-Za-z0-9.\-])"
_DESPUES = r"(?![A-Za-z0-9.\-])"


def emparejar(texto: str, tabla: dict[str, str]) -> list[tuple[str, str, tuple[int, int]]]:
    """Devuelve (valor_normalizado, literal, span). Mas largo primero; sin solapes."""
    t = texto.upper()
    hallazgos: list[tuple[str, str, tuple[int, int]]] = []
    ocupado: list[tuple[int, int]] = []
    for clave in sorted(tabla, key=len, reverse=True):
        patron = _ANTES + re.escape(clave) + _DESPUES
        for m in re.finditer(patron, t):
            ini, fin = m.span()
            if any(ini < f and i < fin for i, f in ocupado):
                continue
            ocupado.append((ini, fin))
            hallazgos.append((tabla[clave], texto[ini:fin], (ini, fin)))
    return sorted(hallazgos, key=lambda h: h[2][0])


def normalizar_norma(literal: str) -> str:
    """Exacta o se conserva. DIN 9331 NO es DIN 933."""
    return NORMAS_DIN_ISO.get(literal.upper().strip(), literal.upper().strip())
```

- [ ] **Paso 4: Ver que pasan los 7 tests**

Run: `pytest tests/test_catalogos.py -v`
Expected: 7 passed. Si `test_calidad_10_no_sale_de_M10` falla, el problema está en `_ANTES`: `M10` tiene una letra antes del `10`.

- [ ] **Paso 5: Commit**

```bash
git add motor/catalogos.py tests/test_catalogos.py
git commit -m "añade catalogos cerrados y emparejador por token sin coincidencia difusa"
```

---

## Tarea 4: Derivaciones

**Files:**
- Create: `motor/derivaciones.py`, `tests/test_derivaciones.py`

**Interfaces:**
- Produces: `material_de_calidad(calidad: str) -> Optional[tuple[str, str]]` (valor, regla), `nombre_de_norma(norma: str) -> Optional[tuple[str, str]]`

- [ ] **Paso 1: Test**

```python
import pytest
from motor.catalogos import GRUPOS_CALIDAD
from motor.derivaciones import material_de_calidad, nombre_de_norma


@pytest.mark.parametrize("calidad,esperado", [
    ("8.8", "AC"), ("10.9", "AC"), ("12.9", "AC"), ("GRADE 5", "AC"),
    ("8", "AC"), ("10", "AC"), ("200HV", "AC"), ("100HV", "AC"),
    ("A2", "INOX"), ("A4-70", "INOX"), ("A4-80", "INOX"), ("304", "INOX"), ("316", "INOX"),
    ("GR B7", "AC"), ("GR 2H", "AC"), ("ASTM F436", "AC"),
])
def test_material_se_deriva_de_la_calidad(calidad, esperado):
    valor, regla = material_de_calidad(calidad)
    assert valor == esperado
    assert regla.startswith("MAT-")


def test_las_21_calidades_del_catalogo_mapean():
    """Ninguna queda fuera: si una nueva entra al catalogo, este test lo caza."""
    sin_mapa = [c for c in GRUPOS_CALIDAD if material_de_calidad(c) is None]
    assert sin_mapa == []


def test_calidad_desconocida_no_deriva_nada():
    assert material_de_calidad("XYZ-99") is None


@pytest.mark.parametrize("norma,esperado", [
    ("ISO 4017", "TORNILLO"), ("ISO 4762", "TORNILLO"), ("ISO 4032", "TUERCA"),
    ("ISO 10511", "TUERCA"), ("ISO 7089", "ARANDELA"), ("ISO 7094", "ARANDELA"),
    ("ASTM A193", "ESPARRAGO"), ("ASTM A194", "TUERCA"), ("ASTM F436", "ARANDELA"),
    ("DIN 975", "VARILLA ROSCADA"),
])
def test_nombre_se_deriva_de_la_norma(norma, esperado):
    valor, regla = nombre_de_norma(norma)
    assert valor == esperado
```

- [ ] **Paso 2: Ver que falla**

- [ ] **Paso 3: Implementar `motor/derivaciones.py`**

```python
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
```

- [ ] **Paso 4: Ver que pasan y commit**

```bash
pytest tests/test_derivaciones.py -v
git add motor/derivaciones.py tests/test_derivaciones.py
git commit -m "añade derivacion de material desde calidad y de nombre desde norma"
```

---

## Tarea 5: Puerto LLM y segmentador con votación

**Files:**
- Create: `motor/puerto_llm.py`, `motor/segmentador.py`, `tests/test_segmentador.py`

**Interfaces:**
- Produces: `PuertoLLM` (Protocol con `segmentar(texto) -> Segmentacion` y `extraer(tramo) -> list[dict]`), `PuertoFalso`, `segmentar_con_votacion(puerto, texto, pasadas=3) -> Segmentacion`

- [ ] **Paso 1: Test de votación (con puerto falso, sin red)**

```python
from motor.modelos import Elemento, Segmentacion
from motor.segmentador import segmentar_con_votacion


class PuertoGuion:
    """Devuelve una segmentacion distinta en cada pasada, segun guion."""
    def __init__(self, guion): self.guion, self.i = guion, 0
    def segmentar(self, texto):
        s = self.guion[self.i % len(self.guion)]; self.i += 1; return s
    def extraer(self, tramo): return []


def _seg(*tipos):
    return Segmentacion(elementos=[Elemento(tipo_indicado=t, span=(i, i + 1))
                                   for i, t in enumerate(tipos)])


def test_unanimidad_da_tres_votos():
    p = PuertoGuion([_seg("BOLT", "NUT")] * 3)
    r = segmentar_con_votacion(p, "x", pasadas=3)
    assert [e.votos for e in r.elementos] == [3, 3]


def test_dos_de_tres_baja_los_votos():
    p = PuertoGuion([_seg("BOLT", "NUT"), _seg("BOLT", "NUT"), _seg("BOLT")])
    r = segmentar_con_votacion(p, "x", pasadas=3)
    assert max(e.votos for e in r.elementos) == 2


def test_gana_la_segmentacion_mayoritaria():
    p = PuertoGuion([_seg("BOLT"), _seg("BOLT", "NUT"), _seg("BOLT", "NUT")])
    r = segmentar_con_votacion(p, "x", pasadas=3)
    assert [e.tipo_indicado for e in r.elementos] == ["BOLT", "NUT"]
```

- [ ] **Paso 2: Ver que falla**

- [ ] **Paso 3: Implementar `motor/puerto_llm.py`**

```python
"""El proveedor vive detras de un puerto. Cambiar de modelo es un parametro."""
from typing import Protocol
from motor.modelos import Segmentacion


class PuertoLLM(Protocol):
    def segmentar(self, texto: str) -> Segmentacion: ...
    def extraer(self, tramo: str) -> list[dict]: ...


class PuertoFalso:
    """Segmentador de guion para tests y para el pipeline sin red."""
    def __init__(self, respuestas: dict[str, Segmentacion]):
        self.respuestas = respuestas

    def segmentar(self, texto: str) -> Segmentacion:
        if texto not in self.respuestas:
            raise KeyError(f"PuertoFalso sin guion para: {texto[:60]}")
        return self.respuestas[texto]

    def extraer(self, tramo: str) -> list[dict]:
        return []
```

- [ ] **Paso 4: Implementar `motor/segmentador.py`**

```python
"""A1. Vota 3 pasadas: la firma es (numero, tipos). Los votos alimentan la confianza."""
from collections import Counter
from motor.modelos import Segmentacion
from motor.puerto_llm import PuertoLLM


def _firma(s: Segmentacion) -> tuple:
    return tuple(e.tipo_indicado.upper() for e in s.elementos)


def segmentar_con_votacion(puerto: PuertoLLM, texto: str, pasadas: int = 3) -> Segmentacion:
    resultados = [puerto.segmentar(texto) for _ in range(pasadas)]
    conteo = Counter(_firma(s) for s in resultados)
    firma_ganadora, votos = conteo.most_common(1)[0]
    ganadora = next(s for s in resultados if _firma(s) == firma_ganadora)
    for e in ganadora.elementos:
        e.votos = votos
    return ganadora
```

- [ ] **Paso 5: Ver que pasan y commit**

```bash
pytest tests/test_segmentador.py -v
git add motor/puerto_llm.py motor/segmentador.py tests/test_segmentador.py
git commit -m "añade puerto LLM y segmentador con votacion de tres pasadas"
```

---

## Tarea 6: Invariantes estructurales

**Files:**
- Create: `motor/invariantes.py`, `tests/test_invariantes.py`

**Interfaces:**
- Produces: `verificar_literal(literal, texto, span) -> bool`, `cobertura(texto, seg) -> float`, `hay_solape(seg) -> bool`, `contar_sustantivos(texto) -> int`

- [ ] **Paso 1: Test**

```python
from motor.modelos import Elemento, Segmentacion
from motor.invariantes import verificar_literal, cobertura, hay_solape, contar_sustantivos


def test_literal_verificado():
    t = 'STUD BOLT 7/8" X 130'
    assert verificar_literal("BOLT", t, (5, 9)) is True
    assert verificar_literal("BOLT", t, (0, 4)) is False   # ahi pone STUD
    assert verificar_literal("A193", t, (0, 4)) is False   # no aparece


def test_cobertura_detecta_elemento_perdido():
    t = "BOLT M16 with NUT and WASHER"
    completa = Segmentacion(elementos=[
        Elemento(tipo_indicado="BOLT", span=(0, 8)),
        Elemento(tipo_indicado="NUT", span=(14, 17)),
        Elemento(tipo_indicado="WASHER", span=(22, 28))])
    assert cobertura(t, completa) > 0.75
    coja = Segmentacion(elementos=completa.elementos[:2])
    assert cobertura(t, coja) < 0.75


def test_solape():
    s = Segmentacion(elementos=[Elemento(tipo_indicado="A", span=(0, 10)),
                                Elemento(tipo_indicado="B", span=(5, 15))])
    assert hay_solape(s) is True


def test_recuento_independiente_de_sustantivos():
    assert contar_sustantivos("BOLT DIN 933 M16 with NUT and WASHER") == 3
    assert contar_sustantivos("Tornillo hexagonal DIN 933 con tuerca y arandela") == 3
    assert contar_sustantivos("STUD BOLT 7/8, 2 HEX. NUT, 2 WASHER") == 3
    assert contar_sustantivos("Tuerca hexagonal DIN 934 M16") == 1
```

- [ ] **Paso 2: Ver que falla**

- [ ] **Paso 3: Implementar `motor/invariantes.py`**

```python
"""Las comprobaciones que impiden inventar y, sobre todo, la que impide OMITIR.

La verificacion de literales impide que el modelo se invente un valor. No impide que
se deje un elemento fuera: si el segmentador se salta '2 WASHER 7/8", ASTM F436',
ninguna comprobacion por elemento lo detecta porque ese elemento no existe.
Solo la cobertura del texto lo caza.
"""
import re
from motor.modelos import Segmentacion

UMBRAL_COBERTURA = 0.75

_SUSTANTIVOS = {
    "TORNILLO": r"TORNILLOS?|BOLTS?|SCREWS?",
    "TUERCA": r"TUERCAS?|NUTS?",
    "ARANDELA": r"ARANDELAS?|WASHERS?",
    "ESPARRAGO": r"ESPARRAGOS?|STUDS?",
    "VARILLA": r"VARILLAS?\s+ROSCADAS?|THREADED\s+RODS?",
}
# STUD BOLT es un solo elemento, no un esparrago mas un tornillo.
_COMPUESTOS = [(r"STUD\s+BOLTS?", "ESPARRAGO")]


def verificar_literal(literal: str, texto: str, span: tuple[int, int]) -> bool:
    if literal is None or span is None:
        return False
    ini, fin = span
    if not (0 <= ini < fin <= len(texto)):
        return False
    return texto[ini:fin].upper() == literal.upper()


def cobertura(texto: str, seg: Segmentacion) -> float:
    """Proporcion de caracteres no-conector cubiertos por algun tramo."""
    marcas = bytearray(len(texto))
    for e in seg.elementos:
        for i in range(max(0, e.span[0]), min(len(texto), e.span[1])):
            marcas[i] = 1
    for ini, fin in seg.ambito_fila:
        for i in range(max(0, ini), min(len(texto), fin)):
            marcas[i] = 1
    significativos = [i for i, c in enumerate(texto) if c.isalnum()]
    if not significativos:
        return 1.0
    return sum(marcas[i] for i in significativos) / len(significativos)


def hay_solape(seg: Segmentacion) -> bool:
    tramos = sorted(e.span for e in seg.elementos)
    return any(tramos[i][1] > tramos[i + 1][0] for i in range(len(tramos) - 1))


def contar_sustantivos(texto: str) -> int:
    """Escaner determinista, independiente del modelo. Solo cuenta; no parsea."""
    t = texto.upper()
    total, consumido = 0, t
    for patron, _ in _COMPUESTOS:
        hallados = re.findall(patron, consumido)
        total += len(hallados)
        consumido = re.sub(patron, " ", consumido)
    for patron in _SUSTANTIVOS.values():
        total += len(re.findall(patron, consumido))
    return total
```

- [ ] **Paso 4: Ver que pasan y commit**

```bash
pytest tests/test_invariantes.py -v
git add motor/invariantes.py tests/test_invariantes.py
git commit -m "añade invariantes estructurales incluida la cobertura del texto"
```

---

## Tarea 7: Coherencias cruzadas

**Files:**
- Create: `motor/coherencias.py`, `tests/test_coherencias.py`

**Interfaces:**
- Produces: `comprobar(linea: LineaSalida, interruptores: dict[str,bool]) -> list[Motivo]`

- [ ] **Paso 1: Test**

```python
from motor.modelos import LineaSalida, Valor, Procedencia
from motor.coherencias import comprobar, TODAS_ACTIVAS


def _linea(**kw):
    l = LineaSalida.vacia(id="L1", fila_origen=1, cantidad=1)
    for k, v in kw.items():
        setattr(l, k, Valor(valor=v, literal=v, span=(0, 1), procedencia=Procedencia.EXTRAIDO))
    return l


def test_calidad_10_en_tornillo_es_incoherente():
    codigos = [m.codigo for m in comprobar(_linea(nombre="TORNILLO", calidad="10"), TODAS_ACTIVAS)]
    assert "CALIDAD_SOLO_TUERCA" in codigos


def test_HV_en_tornillo_es_incoherente():
    codigos = [m.codigo for m in comprobar(_linea(nombre="TORNILLO", calidad="200HV"), TODAS_ACTIVAS)]
    assert "CALIDAD_SOLO_ARANDELA" in codigos


def test_inox_cincado_es_incoherente():
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="TUERCA", calidad="A4-80", acabado="CINCADO"), TODAS_ACTIVAS)]
    assert "INOX_CON_ACABADO_ZINC" in codigos


def test_astm_con_metrica_es_incoherente():
    codigos = [m.codigo for m in comprobar(
        _linea(nombre="ESPARRAGO", norma="ASTM A193", medida="M20"), TODAS_ACTIVAS)]
    assert "SISTEMA_MEDIDA_INCOHERENTE" in codigos


def test_tuerca_con_8_8_no_es_incoherencia():
    """Atestiguado en la fila 13 del MTO: es vocabulario del cliente."""
    codigos = [m.codigo for m in comprobar(_linea(nombre="TUERCA", calidad="8.8"), TODAS_ACTIVAS)]
    assert codigos == []


def test_interruptor_apaga_la_comprobacion():
    apagado = {**TODAS_ACTIVAS, "inox_acabado": False}
    assert comprobar(_linea(nombre="TUERCA", calidad="A4-80", acabado="CINCADO"), apagado) == []
```

- [ ] **Paso 2: Ver que falla**

- [ ] **Paso 3: Implementar `motor/coherencias.py`**

```python
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
                              texto=f"La calidad {calidad} solo aplica a tuercas (§5) y esto es {nombre}."))

    if interruptores.get("calidad_solo_arandela") and calidad.endswith("HV") and nombre and nombre != "ARANDELA":
        motivos.append(Motivo(codigo="CALIDAD_SOLO_ARANDELA", atributo="calidad",
                              texto=f"Las clases HV son durezas de arandela y esto es {nombre}."))

    if interruptores.get("inox_acabado") and calidad in _INOX and acabado in _ZINC:
        motivos.append(Motivo(codigo="INOX_CON_ACABADO_ZINC", atributo="acabado",
                              texto=f"{calidad} es inox austenitico y no se {acabado.lower()}."))

    if interruptores.get("sistema_medida") and norma and medida:
        imperial_norma = norma.startswith(("ASTM", "ASME", "MSS"))
        metrica_medida = medida.upper().startswith("M")
        if imperial_norma and metrica_medida:
            motivos.append(Motivo(codigo="SISTEMA_MEDIDA_INCOHERENTE", atributo="medida",
                                  texto=f"{norma} es norma imperial y la medida {medida} es metrica."))
        if norma.startswith(("DIN", "ISO", "EN")) and '"' in medida:
            motivos.append(Motivo(codigo="SISTEMA_MEDIDA_INCOHERENTE", atributo="medida",
                                  texto=f"{norma} es norma metrica y la medida {medida} es imperial."))

    if interruptores.get("grado_astm_nombre") and nombre:
        if calidad in {"GR 2H", "2H"} and nombre != "TUERCA":
            motivos.append(Motivo(codigo="GRADO_ASTM_INCOHERENTE", atributo="calidad",
                                  texto="GR 2H es ASTM A194, norma de tuercas."))
        if calidad in {"GR B7", "B7"} and nombre not in {"TORNILLO", "ESPARRAGO"}:
            motivos.append(Motivo(codigo="GRADO_ASTM_INCOHERENTE", atributo="calidad",
                                  texto="GR B7 es ASTM A193, norma de tornilleria."))
    return motivos
```

- [ ] **Paso 4: Ver que pasan y commit**

```bash
pytest tests/test_coherencias.py -v
git add motor/coherencias.py tests/test_coherencias.py
git commit -m "añade seis comprobaciones cruzadas de dominio con interruptor"
```

---

## Tarea 8: Confianza y validador

**Files:**
- Create: `motor/confianza.py`, `motor/validador.py`, `tests/test_confianza.py`

**Interfaces:**
- Produces: `confianza_celda(valor, literal_ok, votos, coherente) -> tuple[int, str]`, `aplicar_confianza(linea, votos, motivos) -> LineaSalida`

- [ ] **Paso 1: Test**

```python
from motor.modelos import Valor, Procedencia, LineaSalida, Motivo, Estado
from motor.confianza import confianza_celda, aplicar_confianza


def _v(p, **kw):
    base = dict(valor="X", literal="X", span=(0, 1))
    if p is Procedencia.DERIVADO:
        base = dict(valor="X", regla="MAT-8.8")
    if p is Procedencia.AUSENTE:
        base = dict()
    return Valor(procedencia=p, **{**base, **kw})


def test_extraido_verificado_unanime_y_coherente_da_100():
    c, factor = confianza_celda(_v(Procedencia.EXTRAIDO), True, 3, True)
    assert c == 100 and factor == "ninguno"


def test_derivado_tambien_llega_a_100():
    assert confianza_celda(_v(Procedencia.DERIVADO), True, 3, True)[0] == 100


def test_inferido_topa_en_70():
    c, factor = confianza_celda(_v(Procedencia.INFERIDO), True, 3, True)
    assert c == 70 and factor == "procedencia"


def test_literal_no_verificado_deja_la_celda_en_cero():
    c, factor = confianza_celda(_v(Procedencia.EXTRAIDO), False, 3, True)
    assert c == 0 and factor == "literal"


def test_dos_de_tres_votos_baja_a_67():
    c, factor = confianza_celda(_v(Procedencia.EXTRAIDO), True, 2, True)
    assert c == 67 and factor == "segmentacion"


def test_incoherencia_deja_la_celda_en_cero():
    assert confianza_celda(_v(Procedencia.EXTRAIDO), True, 3, False) == (0, "coherencia")


def test_la_linea_toma_el_minimo_y_deriva_su_estado():
    linea = LineaSalida.vacia(id="L1", fila_origen=1, cantidad=1)
    linea.nombre = _v(Procedencia.EXTRAIDO)
    linea.calidad = _v(Procedencia.INFERIDO)
    r = aplicar_confianza(linea, votos=3, motivos=[])
    assert r.confianza == 70
    assert r.estado is Estado.REVISION_MANUAL
    assert any(m.factor_limitante == "procedencia" for m in r.motivos)
```

- [ ] **Paso 2: Ver que falla**

- [ ] **Paso 3: Implementar `motor/confianza.py`**

```python
"""La confianza NO la reporta el modelo: la calcula el codigo con cuatro hechos medidos.

Un '95 %' generado por un LLM es un numero inventado con aspecto de evidencia.
Aqui cada factor es una observacion, y por ser un minimo siempre hay un motivo
concreto: '67 porque la segmentacion fue 2 de 3'.
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


def aplicar_confianza(linea: LineaSalida, votos: int, motivos: list[Motivo]) -> LineaSalida:
    atributos_incoherentes = {m.atributo for m in motivos if m.atributo}
    peor, peor_atributo, peor_factor = 100, None, "ninguno"
    for nombre, celda in linea.celdas().items():
        if celda.procedencia is Procedencia.AUSENTE:
            continue
        literal_ok = celda.span is not None or celda.procedencia is Procedencia.DERIVADO
        c, factor = confianza_celda(celda, literal_ok, votos, nombre not in atributos_incoherentes)
        if c < peor:
            peor, peor_atributo, peor_factor = c, nombre, factor
    linea.confianza = peor
    linea.motivos = list(motivos)
    if peor < 100 and not any(m.atributo == peor_atributo for m in motivos):
        linea.motivos.append(Motivo(
            codigo="CONFIANZA_INSUFICIENTE", atributo=peor_atributo,
            texto=f"La celda '{peor_atributo}' se queda en {peor} por el factor {peor_factor}.",
            factor_limitante=peor_factor))
    return linea
```

- [ ] **Paso 4: Ver que pasan y commit**

```bash
pytest tests/test_confianza.py -v
git add motor/confianza.py tests/test_confianza.py
git commit -m "añade indice de confianza como minimo de cuatro factores medidos"
```

---

## Tarea 9: Cantidades

**Files:**
- Create: `motor/cantidades.py`, `tests/test_cantidades.py`

**Interfaces:**
- Produces: `multiplicador(tramo: str) -> int`

- [ ] **Paso 1: Test** — el ejemplo trabajado de §2 fija la respuesta: 40 / 80 / 80

```python
from motor.cantidades import multiplicador


def test_multiplicador_explicito():
    assert multiplicador("W/2 HEX. NUT 7/8\", ASTM A194, GR 2H") == 2
    assert multiplicador("2 WASHER 7/8\", ASTM F436") == 2
    assert multiplicador("con 2 tuercas DIN 934") == 2


def test_sin_multiplicador_es_uno():
    assert multiplicador("with NUT DIN 934 M20") == 1
    assert multiplicador("con tuerca y arandela") == 1


def test_el_uno_explicito_tambien_vale():
    assert multiplicador("1 WASHER ASTM F436") == 1
```

- [ ] **Paso 2: Ver que falla**

- [ ] **Paso 3: Implementar `motor/cantidades.py`**

```python
"""Las reglas no las cierran, pero el ejemplo trabajado de §2 si: 40 / 80 / 80.
CANT. es la cantidad del elemento principal; el multiplicador va encima.
"""
import re

_MULT = re.compile(r"(?:W/|C/W|WITH|CON|Y|AND)?\s*(\d+)\s*(?=[A-Za-zÁÉÍÓÚÑ])", re.I)


def multiplicador(tramo: str) -> int:
    m = _MULT.search(tramo.strip())
    return int(m.group(1)) if m else 1
```

- [ ] **Paso 4: Ver que pasan y commit**

```bash
pytest tests/test_cantidades.py -v
git add motor/cantidades.py tests/test_cantidades.py
git commit -m "añade multiplicadores de cantidad del set"
```

---

## Tarea 10: Pipeline punta a punta

Con `PuertoFalso` guionizado para las 15 filas. Sin red. Es el hito que convierte piezas en sistema.

**Files:**
- Create: `motor/pipeline.py`, `datos/guion_falso.py`, `tests/test_pipeline.py`

**Interfaces:**
- Produces: `procesar_mto(ruta, puerto, interruptores) -> list[LineaSalida]`

- [ ] **Paso 1: Test de contrato global**

```python
from pathlib import Path
from motor.pipeline import procesar_mto
from datos.guion_falso import puerto_de_guion
from motor.modelos import Estado


def test_quince_filas_dan_treinta_lineas():
    lineas = procesar_mto(Path("datos/MTO_tornilleria.xlsx"), puerto_de_guion())
    assert len(lineas) == 30


def test_reparto_por_tipo():
    lineas = procesar_mto(Path("datos/MTO_tornilleria.xlsx"), puerto_de_guion())
    tipos = [l.nombre.valor for l in lineas]
    assert tipos.count("TUERCA") == 11
    assert tipos.count("ARANDELA") == 7


def test_las_siete_arandelas_van_a_revision_por_falta_de_calidad():
    lineas = procesar_mto(Path("datos/MTO_tornilleria.xlsx"), puerto_de_guion())
    arandelas = [l for l in lineas if l.nombre.valor == "ARANDELA"]
    assert all(l.estado is Estado.REVISION_MANUAL for l in arandelas)


def test_cantidades_de_la_fila_uno():
    lineas = [l for l in procesar_mto(Path("datos/MTO_tornilleria.xlsx"), puerto_de_guion())
              if l.fila_origen == 1]
    assert sorted(l.cantidad for l in lineas) == [40, 80, 80]


def test_ninguna_celda_sin_procedencia():
    for l in procesar_mto(Path("datos/MTO_tornilleria.xlsx"), puerto_de_guion()):
        for nombre, celda in l.celdas().items():
            assert celda.procedencia is not None, f"{l.id}.{nombre} sin procedencia"
```

- [ ] **Paso 2: Ver que falla**

- [ ] **Paso 3: Escribir `datos/guion_falso.py`**

Contiene, a mano, la segmentación esperada de las 15 filas: por cada fila, los tramos `(ini, fin)` de cada elemento y el tramo de ámbito de fila. Se obtiene abriendo `datos/MTO_tornilleria.xlsx`, saneando cada descripción y localizando los índices. **Este fichero es andamio de pruebas, no gold set** — no decide qué es correcto, sólo permite ejercitar el pipeline sin red.

- [ ] **Paso 4: Implementar `motor/pipeline.py`**

Orquesta: `leer_mto` → por fila `segmentar_con_votacion` → invariantes 2/3/4 (si fallan, la fila entera va a revisión con motivo) → por elemento `extraer` + `verificar_literal` → `emparejar` contra catálogos → `normalizar_norma` → derivaciones → extrapolación de medida (§2, sólo medida) → `multiplicador` × cantidad de fila → `comprobar` coherencias → `aplicar_confianza`.

- [ ] **Paso 5: Ver que pasan los 5 tests y commit**

```bash
pytest tests/ -v
git add motor/pipeline.py datos/guion_falso.py tests/test_pipeline.py
git commit -m "añade pipeline punta a punta: 15 filas dan 30 lineas"
```

---

## Tarea 11: Gold set

**Files:**
- Create: `evaluacion/plantilla_gold.py`, `datos/gold_set.csv`

- [ ] **Paso 1: Generar la plantilla**

```python
"""Vuelca las 30 lineas con las celdas vacias para anotar a mano.
NO rellena valores: solo la estructura, para que anotar cueste 45 min y no 2 h.
"""
# columnas: id, fila_origen, nombre, material, calidad, medida, longitud, norma,
#           acabado, cantidad, estado_esperado, confianza_nombre..confianza_acabado
# donde cada confianza_* es: cierta | interpretada | indecidible
```

- [ ] **Paso 2: Anotar a mano** (Bernabé, no el agente). Las celdas donde las reglas no deciden se marcan `indecidible`.

- [ ] **Paso 3: Segunda anotación ciega**, en otro momento del día, en `datos/gold_set_2.csv`.

- [ ] **Paso 4: Medir el desacuerdo propio**

```bash
python -m evaluacion.plantilla_gold --comparar datos/gold_set.csv datos/gold_set_2.csv
```

Ese porcentaje es la cota superior de fiabilidad del gold set. Va al one-pager.

- [ ] **Paso 5: Commit**

```bash
git add evaluacion/plantilla_gold.py datos/gold_set*.csv
git commit -m "añade gold set anotado a mano con doble anotacion"
```

---

## Tarea 12: Arnés de evaluación

**Files:**
- Create: `evaluacion/arnes.py`, `tests/test_arnes.py`

**Interfaces:**
- Produces: `evaluar(lineas, gold) -> Metricas` con `tasa_escape`, `cobertura`, `exactitud_segmentacion`, `por_atributo`, `coste_eur`, `latencia_s`

- [ ] **Paso 1: Test con gold sintético**

```python
from evaluacion.arnes import evaluar


def test_escape_solo_cuenta_lineas_resueltas_y_mal():
    m = evaluar(lineas=[_resuelta_mal(), _resuelta_bien(), _en_revision()], gold=_gold())
    assert m.tasa_escape == 1 / 3
    assert m.cobertura == 2 / 3


def test_las_celdas_indecidibles_no_cuentan_como_escape():
    m = evaluar(lineas=[_resuelta_con_celda_indecidible()], gold=_gold_con_indecidible())
    assert m.tasa_escape == 0.0
    assert m.celdas_indecidibles == 1
```

- [ ] **Paso 2: Implementar** con las definiciones exactas del spec §8.

- [ ] **Paso 3: Commit**

```bash
git add evaluacion/arnes.py tests/test_arnes.py
git commit -m "añade arnes de evaluacion con las metricas del spec"
```

---

## Tarea 13: Puerto OpenAI y prueba de humo

**Files:**
- Create: `motor/puerto_openai.py`, `tests/test_puerto_openai.py` (marcado `@pytest.mark.red`)

- [ ] **Paso 1: Implementar `PuertoOpenAI`** con salida estructurada, `temperature=0`, caché en disco por hash del texto (`.cache_llm/`), y contabilidad de `usage` para el coste. **Sin catálogos en el prompt.**

- [ ] **Paso 2: Prueba de humo sobre 3 filas** (la 1, la 8 y la 13: set completo ASTM, set sin norma, elemento suelto con trampa `AUTOBLOCANTE`).

```bash
python -m motor.pipeline --mto datos/MTO_tornilleria.xlsx --filas 1,8,13 --proveedor openai --modelo <luna>
```

Coste esperado: céntimos. Si la segmentación de la fila 1 no da 3 elementos, el prompt necesita trabajo — **es el momento de descubrirlo, no el martes por la noche.**

- [ ] **Paso 3: Commit**

```bash
git add motor/puerto_openai.py tests/test_puerto_openai.py
git commit -m "añade puerto OpenAI con cache en disco y contabilidad de coste"
```

---

## Tarea 14: API

**Files:**
- Create: `api/servidor.py`, `arrancar.py`

- [ ] `POST /api/procesar` (multipart xlsx) → `list[LineaSalida]` en JSON
- [ ] `POST /api/resolver` (id, atributo, valor) → recalcula confianza y estado de esa línea
- [ ] `GET /api/exportar` → xlsx agrupado por material canónico
- [ ] `GET /` y estáticos desde `front/dist`
- [ ] `arrancar.py`: un comando levanta todo
- [ ] Commit: `añade API y arranque de un solo comando`

---

## Tarea 15: Front

**Files:**
- Create: `front/` (Vite + React + TS + Tailwind + shadcn/ui + TanStack Table)

- [ ] Subir xlsx, tabla virtualizada con estado y confianza por línea
- [ ] Color por procedencia en cada celda (extraído / derivado / inferido / ausente)
- [ ] Filtro por estado y por motivo
- [ ] Panel lateral de traza: texto original, tramos, regla por celda, factores de confianza
- [ ] Resolver con **el valor propuesto y un clic**
- [ ] Exportar
- [ ] `npm run build` y `dist/` versionado
- [ ] Commit: `añade front de cola de compras con panel de traza`

---

## Tarea 16: Corpus de estrés, ablaciones e informe

**Files:**
- Create: `datos/corpus_estres.csv`, `evaluacion/ablaciones.py`, `evaluacion/informe.py`

- [ ] ~50 filas sintéticas que ejerciten lo que el MTO nunca toca: las 16 calidades sin usar (las 5 HV, GRADE/GRADO 5 y 8, 10.9, 304, 316...), 20 normas sin usar, los 5 acabados ausentes, `VARILLA ROSCADA`, `ASME` y `MSS SP`, `1-1/4"`, longitudes con unidad explícita, comillas tipográficas
- [ ] Ablaciones: sin votación, sin coherencias, sin derivación de material, sin invariante de cobertura
- [ ] Comparativa Luna vs Terra: (escape, coste/obra) de cada uno
- [ ] `informe.py` vuelca las tablas en markdown, listas para el one-pager
- [ ] Commit: `añade corpus de estres, ablaciones e informe de metricas`

---

## Tarea 17: Arranque en frío

- [ ] `README.md` con los tres comandos exactos
- [ ] **Probar en frío:** clonar en carpeta limpia, `pip install -e .`, `python arrancar.py`, subir el MTO. Sin `npm install`.
- [ ] Commit: `añade README y verifica arranque en frio`

---

## Autorrevisión del plan

**Cobertura del spec:** §2 procedencia → tareas 1, 8. §3 derivaciones y coherencias → 4, 7. §4 las seis decisiones → 4 (material), 7 (coherencias), 9 (cantidades), 10 (norma faltante y longitud, dentro del validador del pipeline). §5 arquitectura → 5, 6, 10, 13. §6 contratos → 1. §7 anti-alucinación → 6, 8. §8 medición → 11, 12, 16. §9 front → 14, 15. §11 riesgos → sin tarea, es material del one-pager.

**Hueco detectado y anotado:** la decisión §4.3 (longitud imperial sin unidad → `INFERIDO`) y §4.2 (norma faltante → revisión) viven dentro del validador del pipeline (tarea 10) pero no tienen test propio. **Añadir a la tarea 10 dos tests:** `test_longitud_imperial_sin_unidad_es_inferida` y `test_linea_sin_norma_va_a_revision`.

**Consistencia de tipos:** `Valor.factores` es `dict[str,int]` en la tarea 1 y se rellena en la 8. `Elemento.votos` se fija en la 5 y se consume en la 8. `Motivo.factor_limitante` se define en la 1 y se usa en la 8.

**Ruta crítica para el miércoles:** tareas 1-13. Las 14-15 son el front. La 16 es lo que llena las casillas del one-pager. Si el martes por la noche va justo, lo que se cae es la 16 antes que la 15, y la 15 antes que la 13.
