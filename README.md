# Reconciliación de MTOs · Tornillería

Convierte cada fila de un MTO en **una línea por material comprable**, con siete atributos normalizados, y la deja en `RESUELTA` o `REVISION_MANUAL`.

Caso técnico Senior FDE · Bernabé Muñoz

---

## Arrancar

Necesitas **Python 3.12+**. No hace falta Node: el front va compilado en el repositorio.

```bash
python -m venv .venv
```

Actívalo — en Windows `.venv\Scripts\activate`, en macOS o Linux `source .venv/bin/activate` — e instala:

```bash
pip install -e ".[dev]"
```

Pon la clave de Gemini en un fichero `.env` en la raíz (hay plantilla en `.env.example`), o como variable de entorno `GEMINI_API_KEY`. Y arranca:

```bash
python arrancar.py
```

Abre <http://127.0.0.1:8000> y sube `datos/MTO_tornilleria.xlsx`.

> Verificado en frío el 3 de septiembre de 2026: clon limpio, entorno nuevo, sin caché. El MTO de 15 filas se procesa en **29 segundos** y cuesta **0,008 $**.

## Qué vas a ver

Las 15 filas del MTO dan **30 líneas**: 13 resueltas, 17 a revisión, 0 fallos de proceso.

Las 17 de revisión no son dudas del sistema: **son datos que el MTO no trae**. Trece por falta de calidad —las siete arandelas y seis tuercas—, cinco por falta de norma, tres por longitud imperial sin unidad. Ninguna línea va a revisión pudiendo resolverse.

La interfaz tiene dos pestañas. **Cola** ordena por procedencia y resuelve en un clic. **Traza** enseña, para la línea seleccionada, el texto de origen con el tramo marcado y los cuatro factores de confianza con el limitante en rojo.

## La demo de dos minutos

Enseña el ciclo completo, que es donde está el valor:

1. Sube el MTO. La arandela `L003` sale en revisión: `7/8" ASTM F436`, sin calidad.
2. Resuélvela a mano con `200HV`, identificándote.
3. **Vuelve a subir el mismo MTO.** `L003` vuelve `RESUELTA`, con procedencia `HEREDADO` y un motivo que dice quién contestó y cuándo.

Fíjate en que **hereda una arandela, no las siete**. Las otras seis son piezas distintas —`M12` sin norma, `M16 ISO 7089` cincada, `1" ASTM F436`…— y la clave es la coincidencia exacta de los otros seis atributos. `L014` también es `ASTM F436` de acero, pero mide `1"` en vez de `7/8"`, así que se vuelve a preguntar.

Con hasta 25 revisiones por obra, preguntar una vez en lugar de veinticinco no reduce el coste de la consulta: lo divide.

## Calidad

```bash
python -m pytest        # 220 tests, sin red ni clave
ruff check .            # estilo, configurado en pyproject.toml
```

Los tests corren **sin red y sin clave**: el segmentador va de guion. Los que llaman de verdad a Gemini están marcados `@pytest.mark.red` y se saltan salvo que pases `--red`. La CI de GitHub ejecuta las dos cosas sobre un clon limpio y comprueba además que el servidor levanta.

**Una prueba sólo vale si puede fallar.** Durante el desarrollo aparecieron catorce casos de tests que pasaban midiendo otra cosa —un test que comparaba una construcción rota contra sí misma, un guardián que miraba bytes del fichero en vez del comportamiento, un auditor de invenciones que comparaba contra el texto crudo en vez del saneado—. Por eso cada guardián nuevo se verifica rompiendo el código a propósito y comprobando que salta.

## Las medidas

```bash
python -m evaluacion.ablaciones            # determinista y gratis
python -m evaluacion.ablaciones --estres   # + corpus de 55 filas y comparativa de modelos (con red)
```

Vuelca [`docs/metricas.md`](docs/metricas.md): qué le pasa a la cobertura si quito cada política y cada coherencia, el corpus de estrés, y la misma obra procesada con dos modelos.

**Lo que el 0 % de escape no cubre, dicho aquí y no escondido:** el gold anota el elemento principal de cada fila. De las 279 líneas que produce el bloque compuesto del blind set, 79 —las tuercas y arandelas de los sets— no tienen verdad anotada. Lo que sí se audita en las 389 es que ningún valor esté inventado: `evaluacion/trazabilidad.py` comprueba que cada uno se rastrea hasta el texto de origen o hasta una regla con nombre. **0 celdas no rastreables.**

## El mapa

| | |
|---|---|
| `motor/` | El sistema. `pipeline.py` orquesta; `catalogos.py` son las cuatro tablas cerradas; `derivaciones.py` lo que se deduce sin alternativa; `invariantes.py` y `coherencias.py` la red de seguridad; `confianza.py` el índice; `historico.py` la herencia entre revisiones |
| `motor/puerto_gemini.py` | La única llamada a modelo del sistema, detrás de un puerto |
| `api/` · `front/` | Servidor FastAPI e interfaz compilada |
| `evaluacion/` | Arnés de métricas, evaluador del blind set, ablaciones y auditoría de trazabilidad |
| `datos/` | El MTO del enunciado, el gold set, y el generador del blind set de 300 filas |
| `docs/` | El one-pager, la guía interna y los diagramas |

## Cómo está construido

**Un solo agente en producción.** Segmenta la prosa en las piezas que se compran por separado, y nada más. Los otros tres que había diseñado —extractor, árbitro de ambigüedad y autoconsistencia ×3— se descartaron **midiendo**, no opinando.

**El modelo no ve los catálogos y no devuelve posiciones.** Dice qué pone; el código decide qué significa, localiza cada trozo en el texto de origen y lo verifica carácter a carácter. Lo que no aparece tal cual se descarta. Por eso la invención no es improbable: es estructuralmente imposible.

**El umbral es 100.** La confianza de una celda es el mínimo de cuatro hechos medidos, y `RESUELTA` es exactamente `confianza == 100`. Encima hay un veto independiente: si falta un campo obligatorio, la confianza se pone a cero valga lo que valga ese mínimo. O el valor viene por un camino que no puede estar mal, o lo mira una persona.

Todo esto sale de la asimetría de coste: un escape cuesta unos 50.000 € y una revisión de más, 1 €. **El sistema no adivina nunca.**

## Los documentos

- [`docs/De aqui a produccion - One-pager.pdf`](docs/) — timeline con puertas, recursos y QA
- [`docs/Guia interna - Como funciona.pdf`](docs/) — siete diagramas del funcionamiento interno
- [`docs/one-pager.md`](docs/one-pager.md) — el entregable del enunciado, seis secciones
- [`docs/superpowers/specs/`](docs/superpowers/specs/) — el diseño y las decisiones, con lo que se descartó y por qué

## La clave

`GEMINI_API_KEY` se lee del entorno o de `.env`, y **no se imprime nunca** — ni en logs, ni en errores, ni en informes. `.env`, `*.key` y `secrets/` están en `.gitignore`.
