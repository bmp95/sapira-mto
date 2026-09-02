# Reconciliación de MTOs · Tornillería

Bernabé Muñoz · Caso técnico Senior FDE · Septiembre 2026

---

## 1. El problema y el KPI

El cuello de botella no es la precisión de un modelo: es la **asimetría de coste**. Dar por buena una fila mal extraída cuesta de tres a ocho semanas de obra; mandar a revisión una buena cuesta noventa segundos de comprador. El cociente ronda **1:50.000**, y de ahí sale toda la arquitectura: adivinar sólo compensaría si nos equivocáramos menos de una vez cada cincuenta mil, y ningún criterio plausible llega ahí. **El sistema no adivina nunca.** Cada valor está escrito en el MTO o se deduce por una regla que no admite alternativa. Lo demás va a revisión.

**Me comprometo a una tasa de escape por debajo del 1,5 %.** Sobre 200 filas no vistas el escape medido fue **0**; con esa muestra el límite superior honesto al 95 % es 1,5 %, y ése es el número que defiendo, no el cero.

**La cobertura la fija vuestro dato, no mi sistema:** 43 % en vuestro MTO, 74 % en filas con datos completos. La diferencia es que ninguna arandela de vuestras quince filas trae dureza.

**El umbral no lo he elegido yo: es 100.** Cada celda lleva una confianza que calcula el código como el mínimo de cuatro hechos medidos —procedencia, verificación del literal contra el texto, acuerdo de segmentación y coherencia cruzada—. `RESUELTA` es exactamente `confianza == 100`. O el valor viene por un camino que no puede estar mal, o lo mira una persona.

## 2. La solución, componente a componente

| Componente | Tipo | Qué le pasa al KPI si lo quito |
|---|---|---|
| **Segmentador** — parte la prosa en piezas | LLM ×1 | Se caen las 9 filas de set: 18 de 30 líneas |
| **Normalizador** — 26 normas, 21 calidades, 7 acabados, 5 nombres | Tabla | Nada si lo cambio por otra tabla; todo si lo cambio por un modelo |
| **Derivaciones** — calidad→material 21/21, norma→nombre 25/25 | Tabla | Material cae de 20/20 a 17/20 |
| **11 coherencias + 8 invariantes** | Código | Sube el escape: es la red de seguridad entera |
| **Extractor por elemento** | **descartado** | Con catálogos cerrados, buscar por token lo hace igual y sin llamadas |
| **Árbitro de ambigüedad** | **descartado** | Subiría cobertura y subiría el escape. 1:50.000 lo mata |
| **Autoconsistencia ×3** | **descartada** | Medido: 0 desacuerdos en 15 filas a temperatura 0 y 0,7 |

**Un solo agente en producción.** Los otros tres los descarté midiendo, no opinando. La autoconsistencia estaba en mi diseño como pilar: la construí, la medí con 90 llamadas reales y la quité, porque el factor de confianza que alimentaba valía siempre 100 — sugería una protección que no existía.

Dos propiedades hacen la alucinación estructuralmente imposible, no improbable: **el modelo nunca ve los catálogos** —dice qué pone, el código decide qué significa— y **se le pide texto literal, no posiciones**, que el código localiza y verifica contra el origen. Si un trozo no aparece tal cual, se descarta.

## 3. Resultados

**Vuestro MTO, 15 filas → 30 líneas.** Cobertura 43,3 % · **escape 0 %** · segmentación 100 % · los siete atributos al 100 %.

**Ruido de revisión: 0 %.** De las 17 líneas en revisión, **las 17 son dato que el MTO no trae**. Ninguna es duda del sistema. La cobertura no la limita el sistema: la limita que vuestra ingeniería no escribe la dureza de las arandelas.

**Blind set propio de 300 filas no vistas**, con formatos reales de proveedor de tubería: 200 compuestas con verdad conocida dan **escape 0,0 %**; 100 adversarias —normas inventadas, calidades inexistentes, nombres de pieza inventados, cuatro filas que ni son tornillería— dan **0 invenciones**.

**Dónde falla:** de los fallos por atributo, prácticamente todos son *"no extrajo nada"* y casi ninguno *"extrajo mal"*. **El modo de fallo es la omisión, no la invención.** Las que se caen son los formatos que **no nombran la pieza principal** —`3/4" IN DIA X 200MM LONG, FULLY THREADED, C/W 2 HEAVY HEXAGON NUTS`—: un comprador deduce que es un espárrago, el sistema se niega a ponerle nombre. Y las descripciones en portugués o alemán, que se arreglan añadiendo filas a una tabla, no reentrenando nada.

**Coste y latencia:** 0,0008 $ y 0,83 s por fila. Una obra completa —100.000 filas en 25 revisiones— sale por **unos 80 $ de modelo**, frente a las ~2.500 horas de comprador que hoy cuesta leerlas.

## 4. La solución objetivo

**El histórico de respuestas.** Vuestra respuesta —que la calidad que falta se consulta con ingeniería— cambia dónde está el valor. La misma arandela sin dureza aparece en la revisión 9, en la 12 y en la 15, y hoy se pregunta tres veces. Con clave canónica exacta se pregunta **una** y las otras veinticuatro la heredan: con 25 revisiones por obra, eso no reduce el coste de la consulta, lo divide. Diseñado y especificado; no construido.

**Aprendizaje del vocabulario por origen**, midiendo la tasa de revisión de cada estudio y ampliando catálogos donde duele. **Y procesado por lotes**, que baja el coste a la mitad y quita el techo de latencia.

## 5. Qué he decidido no hacer

**No derivar lo que no es deducción.** El `130` sin unidad de un espárrago ASTM parece milímetros, y probablemente lo es — pero ASTM admite las dos unidades, así que es una suposición. Va a revisión y me cuesta tres líneas de treinta: **diez puntos de cobertura pagados a conciencia**.

**No completar sets por convención**, no usar coincidencia difusa en ninguna parte —`DIN 9331` no se convierte en `DIN 933`—, y no integrarme con vuestra base de compras, que necesita una conversación pendiente.

**Y no construir tres de los cuatro agentes que había diseñado.** Los medí primero.

## 6. Qué rompe esto en producción

**La deriva del vocabulario.** Un estudio nuevo escribe distinto y la cobertura cae sin avisar. Necesita monitor de tasa de revisión por origen.

**Que vuestra base de compras esté sucia.** Normalizaría impecablemente contra un vocabulario que aguas abajo no cuadra: el sistema correcto y el resultado inútil.

**La erosión de la cola.** Si la revisión crece, el comprador aprueba en bloque y el escape entra igual. Es riesgo de proceso: la interfaz no debe permitir aprobar en bloque motivos distintos, y hace falta muestreo de auditoría. Hoy el ruido es 0 % y ése es el número a vigilar.

---

*45 commits · 181 tests · Arranca en frío con un comando.*
