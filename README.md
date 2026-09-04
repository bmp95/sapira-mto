# Reconciliación de MTOs · Tornillería

Convierte cada fila de un listado de materiales, escrita en prosa libre, en **una línea por material comprable** con siete atributos normalizados — y marca cada línea como `RESUELTA` o `REVISION_MANUAL` según si puede darse por buena sin que la mire nadie.

Caso técnico Senior FDE · Bernabé Muñoz · Septiembre 2026

---

## El problema

Una **EPC** es una empresa de ingeniería, compras y construcción: no promueve obras, las construye. El cliente de este caso es una EPC asturiana de unos 400 M€ de facturación.

Su departamento de ingeniería produce planos, y de cada revisión de un plano sale un **MTO** (*Material Take-Off*): un Excel donde cada fila es algo que hay que comprar. En una obra grande ese Excel tiene **hasta veinte mil filas**, la tornillería es **entre el 15 % y el 25 %** de ellas, y puede haber **veinticinco revisiones** antes de que la obra termine.

El Excel aterriza en el departamento de compras y alguien tiene que comprarlo. Y ahí está el problema: parte de la ingeniería es interna y parte está subcontratada a estudios externos, **y cada uno escribe la misma tuerca de otra forma** — distintas columnas, distintas abreviaturas, distintas normas, distinto idioma. Una fila puede decir:

```
Conjunto esparrago M20 x 200 DIN 975 con 2 tuercas DIN 934 y 2 arandelas DIN 125, 8.8, zincado
```

Esa fila es real, del MTO del cliente. Y no es un material: son **tres** materiales distintos que se compran por separado, cada uno con su norma y su cantidad. Hay que separarlos y traducirlos a un vocabulario común antes de poder hacer nada — y fijarse en que la calidad y el acabado están escritos **al final, para todo el conjunto**, no junto a la pieza a la que pertenecen. Hasta que las filas no están normalizadas no se puede agrupar por familia, ni saber a qué proveedor pedir, ni lanzar una petición de oferta, ni darse cuenta de que la revisión 12 pide dos mil tornillos que ya se compraron en la revisión 9.

Hoy lo hacen **seis personas leyendo fila a fila**, a unos noventa segundos por fila.

## La decisión que gobierna todo lo demás

Este sistema podría escribirse de muchas formas. La que se ha elegido sale de una sola observación, y conviene entenderla antes de mirar el código porque explica cada decisión posterior:

**Los dos errores posibles no cuestan lo mismo, ni de lejos.**

| Error | Qué pasa | Coste |
|---|---|---|
| Mandar a revisión una fila que estaba bien | Un comprador la mira noventa segundos | **~1 €** |
| Dar por buena una fila mal extraída | Llega el material equivocado a la obra: de tres a ocho semanas de retraso en ese frente | **~50.000 €** |

El cociente ronda **1:50.000**. Adivinar sólo compensaría si el sistema se equivocase menos de una vez cada cincuenta mil, y ningún criterio plausible llega ahí.

De ahí la regla que atraviesa todo el proyecto: **el sistema no adivina nunca.** Cada valor o está escrito en el MTO, o se deduce por una regla que no admite alternativa, o lo contestó una persona antes. Todo lo demás va a revisión, con la pregunta ya formulada.

## Qué hace el sistema, paso a paso

Una fila del Excel recorre ocho pasos. **Sólo uno usa un modelo de lenguaje; los otros siete son código determinista**, y eso es deliberado:

| | Paso | Quién | Qué hace |
|---|---|---|---|
| 1 | **Saneado** | código | Normaliza sin interpretar: comillas tipográficas, `Ø` a `DIA`, y `DIN931` / `DIN-931` / `DIN 931` a una única forma |
| 2 | **Segmentación** | **modelo** | Parte la prosa en las piezas físicas que describe. No ve los catálogos y no devuelve posiciones: sólo texto copiado tal cual |
| 3 | **Verificación literal** | código | Busca cada trozo en el texto original. Si no aparece exactamente igual, se descarta |
| 4 | **Extracción por token** | código | Cuatro catálogos cerrados —26 normas, 23 calidades, 21 acabados, nombres— con frontera de palabra. Cero coincidencia difusa |
| 5 | **Derivaciones** | código | Lo que se deduce sin alternativa: una calidad `8.8` sólo existe en acero al carbono, así que el material se sabe aunque no esté escrito |
| 6 | **Ámbito de fila** | código | Lo que describe la fila entera —un acabado al final, por ejemplo— se atribuye a la pieza principal |
| 7 | **Invariantes y coherencias** | código | Ocho reglas que impiden inventar y omitir, más once que detectan que dos atributos escritos se contradicen |
| 8 | **Confianza** | código | Un número por celda, del que sale el estado de la línea |

**El modelo dice qué pone; el código decide qué significa.** Son dos trabajos distintos y por eso están en dos sitios distintos. Como el modelo nunca ve los catálogos, no tiene nada hacia lo que empujar lo que lee; y como se le pide texto literal en vez de posiciones, el código puede comprobar cada trozo contra el origen. Por eso inventar no es improbable aquí: es estructuralmente imposible.

**El umbral es 100, y no lo ha elegido nadie a ojo.** La confianza de una celda es el **mínimo** de cuatro hechos medidos —de dónde viene el valor, si el texto está verificado, si la segmentación fue estable y si no contradice a otro atributo—. `RESUELTA` es exactamente `confianza == 100`. Encima hay un veto independiente: si falta un campo obligatorio, la confianza se pone a cero valga lo que valga ese mínimo. O el valor viene por un camino que no puede estar mal, o lo mira una persona.

## La arquitectura de agentes: uno en producción, tres descartados con medición

Un solo paso de los ocho usa un modelo de lenguaje. Eso no es porque sólo se diseñara uno: **se diseñaron cuatro, se midieron los cuatro, y se retiraron tres con la medición delante**, no por criterio a ojo.

| Componente | Tipo | Qué le pasa al KPI si se quita |
|---|---|---|
| **Segmentador** — parte la prosa en las piezas que describe | Modelo · 1 llamada por fila | Se caen las 9 filas de set del MTO de ejemplo: 18 de 30 líneas |
| Extractor por elemento | Modelo — **descartado** | Con catálogos cerrados, buscar por token lo hace igual y sin llamadas |
| Árbitro de ambigüedad | Modelo — **descartado** | Subiría la cobertura, pero subiría el escape con ella. El cociente 1:50.000 lo mata |
| Autoconsistencia ×3 (tres pasadas, se compara) | Modelo — **descartada** | Medida con 90 llamadas reales: 0 desacuerdos, a temperatura 0 y a 0,7 |

La autoconsistencia estaba en el diseño como pilar de fiabilidad. Se construyó, se probó con 90 llamadas reales, y el factor de confianza que alimentaba valía siempre 100 — sugería una protección que no existía. Se quitó porque medirla, no porque estorbara.

**El 90 % de este sistema son cuatro tablas cerradas y once comprobaciones de coherencia — código, no modelo.** El modelo hace lo único que un humano no puede hacer más barato: leer prosa libre y decir qué piezas describe.

## Arrancarlo

Hace falta **Python 3.12 o superior**. No hace falta Node: la interfaz va compilada dentro del repositorio.

```bash
python -m venv .venv
```

Actívalo — en Windows `.venv\Scripts\activate`, en macOS o Linux `source .venv/bin/activate` — e instala:

```bash
pip install -e ".[dev]"
```

Hace falta una clave de Google Gemini, en un fichero `.env` en la raíz (hay plantilla en `.env.example`) o como variable de entorno `GEMINI_API_KEY`. Y se arranca con un comando:

```bash
python arrancar.py
```

Abre <http://127.0.0.1:8000> y sube `datos/MTO_tornilleria.xlsx`.

> Verificado sobre un clon limpio, entorno nuevo y sin caché: el MTO de 15 filas se procesa en **29 segundos** y cuesta **0,008 $** de modelo.

## Qué se ve

Las 15 filas del MTO de ejemplo dan **30 líneas de compra**: 13 resueltas, 17 a revisión, 0 fallos de proceso.

Y aquí está lo que de verdad hay que entender: **esas 17 no son dudas del sistema, son datos que el MTO no trae.** Trece van a revisión porque falta la calidad —las siete arandelas y seis tuercas—, cinco porque falta la norma y tres porque la longitud viene en pulgadas sin unidad. Ni una sola línea va a revisión pudiendo resolverse. La cobertura no la limita el sistema: la limita que la ingeniería del cliente no escribe la dureza de las arandelas.

La interfaz tiene dos pestañas. **Cola** ordena las líneas por procedencia y permite cerrar una revisión en un clic. **Traza** enseña, para la línea seleccionada, el texto original con el trozo marcado y los cuatro factores de confianza, con el que la tumbó en rojo. El sistema nunca dice «no estoy seguro»: dice qué falló.

### La demo de dos minutos

Enseña el ciclo completo, que es donde está el valor de negocio:

1. Sube el MTO. La arandela `L003` sale en revisión: `7/8" ASTM F436`, sin calidad.
2. Resuélvela a mano con `200HV`, identificándote.
3. **Vuelve a subir el mismo MTO.** `L003` vuelve `RESUELTA`, con procedencia `HEREDADO` y un motivo que dice quién contestó y cuándo.

Fíjate en que **hereda una arandela, no las siete**. Las otras seis son piezas distintas —`M12` sin norma, `M16 ISO 7089` cincada, `1" ASTM F436`…— y la clave de búsqueda es la coincidencia **exacta** de los otros seis atributos. `L014` también es `ASTM F436` de acero, pero mide `1"` en vez de `7/8"`, así que se vuelve a preguntar.

Con hasta 25 revisiones por obra, preguntar una vez en lugar de veinticinco no reduce el coste de la consulta a ingeniería: **lo divide**.

## Resultados

| | |
|---|---|
| Tasa de escape sobre 300 filas nunca vistas | **0 %** |
| Invenciones en 100 filas adversarias | **0** |
| Ruido de revisión | **0 %** — las 17 revisiones son dato ausente, ninguna es duda del sistema |
| Coste y latencia | 0,0008 $ y 0,83 s por fila · una obra completa, unos **80 $** |

**Lo que ese 0 % no cubre, dicho aquí y no escondido:** la anotación de referencia cubre el elemento principal de cada fila. De las 279 líneas que produce el bloque compuesto del blind set, 79 —las tuercas y arandelas de los sets— no tienen verdad anotada. Lo que sí se audita en las 389 es que ningún valor esté inventado: [`evaluacion/trazabilidad.py`](evaluacion/trazabilidad.py) comprueba que cada uno se rastrea hasta el texto de origen o hasta una regla con nombre. **0 celdas no rastreables.**

El compromiso que se defiende no es el 0 % medido, sino **escape por debajo del 1,5 %**: con cero fallos en 200 filas, el límite superior honesto al 95 % es 3/200.

## Estructura del repositorio

| | |
|---|---|
| `motor/` | El sistema. `pipeline.py` orquesta los ocho pasos; `catalogos.py` son las cuatro tablas cerradas; `derivaciones.py` lo que se deduce sin alternativa; `invariantes.py` y `coherencias.py` la red de seguridad; `confianza.py` el índice; `historico.py` la herencia entre revisiones |
| `motor/puerto_gemini.py` | La única llamada a modelo del sistema, detrás de un puerto: cambiar de proveedor es un parámetro |
| `api/` | Servidor FastAPI: procesar, resolver, exportar |
| `front/` | La interfaz, en React. `front/dist` va versionado a propósito para que arranque sin Node |
| `evaluacion/` | Arnés de métricas, evaluador del blind set, ablaciones y auditoría de trazabilidad |
| `datos/` | El MTO del enunciado, las anotaciones de referencia y el generador del blind set de 300 filas |
| `docs/` | Los documentos de entrega y el diseño |
| `tests/` | 220 pruebas |

## Cómo se verifica

```bash
python -m pytest        # 220 tests, sin red ni clave
ruff check .            # estilo, configurado en pyproject.toml
```

Las pruebas corren **sin red y sin clave**: el segmentador va de guion. Las que llaman de verdad a la API están marcadas `@pytest.mark.red` y se saltan salvo que se pase `--red`. La integración continua ejecuta las dos cosas sobre un clon limpio y comprueba además que el servidor levanta.

**Una prueba sólo vale si puede fallar.** Durante el desarrollo apareció una y otra vez el mismo fallo: pruebas que pasaban midiendo otra cosa. Una que comparaba una construcción rota contra sí misma. Un guardián que miraba bytes del fichero en vez del comportamiento. Un auditor de invenciones que comparaba contra el texto crudo en vez del saneado. Por eso cada guardián nuevo se verifica **rompiendo el código a propósito** y comprobando que salta: en un sistema donde el fallo cuesta cincuenta mil euros, la seguridad falsa es el riesgo principal.

### Las medidas

```bash
python -m evaluacion.ablaciones            # determinista y gratis
python -m evaluacion.ablaciones --estres   # + corpus de 55 filas y comparativa de modelos (con red)
```

Vuelca [`docs/metricas.md`](docs/metricas.md): qué le pasa a la cobertura si se quita cada política y cada comprobación, el corpus de estrés, y el mismo MTO procesado con dos modelos distintos.

## Los documentos

| Documento | Qué es |
|---|---|
| [1 · One-pager](docs/1%20-%20One-pager.pdf) · [fuente](docs/one-pager.md) | El problema, el KPI, la solución agente a agente, los resultados y qué se decidió no hacer |
| [2 · De aquí a producción](docs/2%20-%20De%20aqui%20a%20produccion.pdf) | Timeline con cinco puertas, recursos a ambos lados y QA en producción, en una página |
| [3 · De aquí a producción, detalle](docs/3%20-%20De%20aqui%20a%20produccion,%20detalle.pdf) · [fuente](docs/despliegue.md) | Lo mismo, desarrollado |
| [4 · Cómo funciona, en diagramas](docs/4%20-%20Como%20funciona,%20en%20diagramas.pdf) | Siete diagramas del funcionamiento interno |
| [5 · Diseño del sistema](docs/5%20-%20Diseno%20del%20sistema.pdf) · [fuente](docs/diseno/specs/) | Las decisiones tomadas antes de escribir código, con lo que se descartó y por qué |

Los cinco se regeneran desde el repositorio; ninguno depende de una herramienta externa:

```bash
python docs/activos/render.py one-pager-visual guia-visual
```

## La clave de API

`GEMINI_API_KEY` se lee del entorno o de `.env`, y **no se imprime nunca** — ni en registros, ni en mensajes de error, ni en informes. `.env`, `*.key` y `secrets/` están en `.gitignore`.
