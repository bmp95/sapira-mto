# Reconciliación de MTOs · Tornillería — Diseño

Caso técnico Senior FDE · Sapira Partners
Autor: Bernabé Muñoz · 2026-08-31 · Entrega: miércoles 2026-09-02

---

## 1. Objetivo

Convertir cada fila de un MTO de tornillería en **una línea por material comprable**, con
siete atributos normalizados, y clasificarla como `RESUELTA` o `REVISION_MANUAL` con motivo.

El MTO de muestra tiene 15 filas y produce **30 líneas** (12 principales, 11 tuercas,
7 arandelas). El día de la presentación se ejecutará un MTO de 12 filas no vistas.

**El cuello de botella no es la accuracy del modelo: es la asimetría de coste.** Dar por
buena una línea mal extraída cuesta 3-8 semanas de retraso de obra (~50.000 €). Mandar a
revisión una línea buena cuesta ~90 s de comprador (~1 €). Cociente ≈ 1:50.000. Toda la
arquitectura sale de ahí.

---

## 2. La decisión central: procedencia

Cuatro niveles. La frontera entre DERIVADO e INFERIDO es exacta: **¿existe la alternativa?**

| Nivel | Definición | Política |
|---|---|---|
| `EXTRAIDO` | Escrito literalmente en el MTO | Se toma |
| `DERIVADO` | Entailment determinista; la alternativa no existe | **Se toma** |
| `INFERIDO` | Confianza alta, pero es un juicio | **A revisión** |
| `AUSENTE` | No hay dato | Según regla del atributo |

`8.8` no puede ser inox: si lo fuera se llamaría `A4-70` bajo ISO 3506. La alternativa no
existe → DERIVADO. `7/8" X 130` en pulgadas serían 3,3 m: la alternativa existe, sólo que es
absurda → INFERIDO → revisión.

§1 de las reglas prohíbe rellenar con *"el valor más probable"*: prohíbe INFERIDO, no
DERIVADO. §10.1 no dice "prohibido derivarlo", dice "no hay regla" — y §10 pide decidir.

**Cada celda de salida lleva su nivel de procedencia.** Una celda sin procedencia es un error
que aborta el proceso, no una advertencia.

---

## 3. Derivaciones y comprobaciones

### Derivaciones (se aplican)

| De | A | Cobertura |
|---|---|---|
| Calidad | Material | 21/21 valores del catálogo |
| Norma | Nombre | 25/25 entradas de la tabla DIN→ISO |

Material: ISO 898-1/2 (8.8, 10.9, 12.9, GRADE/GRADO 5 y 8, 8, 10) → `AC` · ISO 3506
(A2, A2-70, A2-80, 18-8, 304, A4, A4-70, A4-80, 316) → `INOX` · ISO 7089/7090 (100HV-300HV)
→ `AC` · ASTM A193 GR B7, A194 GR 2H, F436 → `AC`.

*Nota de honestidad: las cinco clases HV descansan en una convención del sistema de
designación (las arandelas de acero se designan por dureza, las de inox por A2/A4). Confianza
muy alta, no idéntica al caso 8.8.*

### Comprobaciones cruzadas (no rellenan; detectan)

| Comprobación | Origen |
|---|---|
| Nombre → ¿longitud obligatoria? (salvo tuerca y arandela) | §7, escrito |
| Nombre ↔ calidad: `8` y `10` sólo tuercas | §5, escrito |
| Nombre ↔ calidad: `HV` sólo arandelas | dominio |
| Calidad → nombre: `GR 2H` (A194) → TUERCA; `GR B7` (A193) → TORNILLO/ESPARRAGO | dominio |
| Norma ↔ sistema de medida: ASTM→pulgadas, DIN/ISO→métrica | dominio · 15/15 en el MTO |
| Calidad ↔ acabado: el inox no se cinca ni se galvaniza | dominio · 15/15 en el MTO |

Son conocimiento de dominio que las reglas NO contienen. Se declaran como aporte propio y
**cada una tiene interruptor**.

---

## 4. Las seis cuestiones abiertas (§10), decididas

| # | Cuestión | Decisión |
|---|---|---|
| 1 | Material | Se **deriva** de la calidad y se marca `DERIVADO`. Sin calidad no hay material, pero esa línea ya está en revisión por calidad. |
| 2 | Norma faltante | **Revisión**, motivo `SIN_NORMA`. Sin norma no se puede pedir a un proveedor. |
| 3 | Longitud sin unidad | Métrica (DIN/ISO + `M20x90`) → mm por definición de la norma: `DERIVADO`. Imperial (ASTM + `7/8" X 130`) → `INFERIDO` → **revisión con el valor propuesto**. Cuesta 3 líneas (filas 1, 5, 12). |
| 4 | Acabado en set | `EXTRAIDO` para el elemento principal; `INFERIDO` para el resto → revisión. Coste real 0 líneas: esos elementos ya están en revisión por calidad. |
| 5 | Cantidades | Multiplicador explícito (`W/2`) × cantidad de fila; sin multiplicador, 1:1. El ejemplo trabajado de §2 lo fija: 40 / 80 / 80. |
| 6 | Coherencias | Calidad no vinculada **nunca** se atribuye (1:50.000). Incoherencia detectada → revisión con motivo. Excepción: tuerca con `8.8` se extrae tal cual, atestiguado en la fila 13, con nota. |

---

## 5. Arquitectura

### Pipeline, cinco etapas — sólo una usa modelo

1. **Saneado** (código) — NFKC, comillas tipográficas y `″` → `"`, `Ø`, espacios colapsados,
   forma canónica de norma (`DIN931` / `DIN-931` / `DIN 931` → una).
2. **Segmentación** (LLM, ×3) — parte la fila en tramos.
3. **Extracción por elemento** (LLM) — literales de atributo con posición, **viendo sólo el
   tramo de su elemento**.
4. **Normalización** (código, 100 % tablas) — 26 norma, 21 calidad, 7 acabado, 5 nombre.
5. **Validación y estado** (código) — obligatoriedad, comprobaciones cruzadas, procedencia,
   `RESUELTA` / `REVISION_MANUAL` + motivos.

### Agentes

| Agente | Tipo | Existe porque | Ablación |
|---|---|---|---|
| **A1 Segmentador** | LLM ×3 | Partir prosa multilingüe con abreviaturas arbitrarias no es reducible a regex | Sin él se caen las 9 filas de set: ~18 de 30 líneas |
| **A2 Extractor** | LLM por elemento | Localizar literales dentro de un tramo | Sin él no hay atributos |
| **A3 Árbitro** | LLM | *Condicional (§12.7).* Si hay tiempo: se construye, se mide y **se descarta con el número delante**. Resolvería la calidad no vinculada | Sube cobertura, sube el escape. El número justifica quitarlo. |

Las dos propiedades que impiden estructuralmente la alucinación —contención de A2 y catálogos
fuera del prompt— se detallan en §7.1.

No son agentes: normalizador, extrapolador de medida, derivador de material, validador,
motor de procedencia. Todo tabla.

### Stack

Motor en **Python 3.12** (openpyxl, pydantic, openai). Front en **Vite + React +
shadcn/ui + TanStack Table**, compilado a estático y servido por **FastAPI**.

Un comando, un proceso, sin Node en la demo. `dist/` versionado a propósito: "arranca en
frío" es criterio de evaluación.

---

## 6. Contratos de datos

```
Segmentacion:
  elementos:    [{ tipo_indicado, span: [ini, fin], votos: k }]   # k de 3 pasadas
  ambito_fila:  [span]          # el ", 8.8, zincado" del final
  conectores:   [span]

Valor:
  valor          # normalizado, o None
  literal        # tal como aparece en el texto
  span           # posición en el texto saneado
  procedencia    # EXTRAIDO | DERIVADO | INFERIDO | AUSENTE
  regla          # id de la regla aplicada, si DERIVADO
  confianza      # entero 0-100. Lo calcula el código. NUNCA lo reporta el modelo.
  factores       # {procedencia, literal, segmentacion, coherencia} -> confianza = min()

LineaSalida:
  id, fila_origen, cantidad
  nombre, material, calidad, medida, longitud, norma, acabado   # cada uno un Valor
  confianza      # min(confianza de sus celdas evaluables)
  estado         # RESUELTA si confianza == 100, si no REVISION_MANUAL
  motivos        # [{codigo, texto, atributo, valor_propuesto, factor_limitante}]
```

**`estado` no es un campo independiente: es una consecuencia de `confianza`.** No hay dos
sitios donde decidir lo mismo, así que no pueden discrepar.

`valor_propuesto` es lo que hace barata la revisión: la cola no pide teclear, propone y pide
un clic. `factor_limitante` dice cuál de los cuatro factores tumbó la celda, para que el
motivo sea concreto y no un "el sistema no está seguro".

---

## 7. Anti-alucinación

El sistema no debe meter jamás un dato que crea bueno y no lo sea. Tres capas.

### 7.1 Dos propiedades estructurales

No son instrucciones del prompt — son cosas que el modelo **no puede** hacer.

**Contención.** A2 recibe un solo tramo de elemento, nunca la fila completa. No puede coger la
calidad de la tuerca y ponérsela a la arandela porque nunca ve el texto de la tuerca.

**El modelo no ve los catálogos.** Nunca. Si ve los 21 valores de calidad, "ayudará" mapeando
al más parecido — que es normalizar, y normalizar es del código. La frontera es:
**el modelo dice qué pone; el código decide qué significa.** La mitad semántica del sistema es
incapaz de alucinar por construcción, no por buen comportamiento.

### 7.2 Ocho invariantes

Si alguna se rompe, la línea no sale `RESUELTA`.

| # | Invariante | Qué impide |
|---|---|---|
| 1 | Todo literal existe en el origen, en su posición | Inventar un valor |
| 2 | Cobertura del texto por los tramos devueltos | **Perder un elemento entero** |
| 3 | Sin solapamiento entre tramos | Duplicar un valor |
| 4 | Recuento independiente por escáner determinista de sustantivos de tipo | Partir de menos o de más |
| 5 | Autoconsistencia: 3 pasadas coinciden en número y tipo | Inestabilidad ante texto nuevo |
| 6 | Cero coincidencia difusa. `DIN 9331` no es `DIN 933` | El error tipográfico que se vuelve dato |
| 7 | Sin valores por defecto. `presente` / `ausente` / `no aplica` | Que un hueco parezca dato |
| 8 | Procedencia obligatoria en toda celda | Un valor sin origen conocido |

La invariante 2 es la que cubre el agujero que las demás no ven: la verificación de literales
impide inventar, pero no impide **omitir**. Si el segmentador se salta entero
`2 WASHER 7/8", ASTM F436`, ninguna comprobación por elemento lo detecta, porque ese elemento
no existe. Sólo la cobertura del texto lo caza.

**Coincidencia por token y por el más largo primero, nunca substring.** Desactiva `BL` dentro
de `AUTOBLOCANTE`, `10` dentro de `M10`, `A2` dentro de `A2-70`, `ZP` dentro de `YZP`.

**Un valor que no case con ninguna entrada del catálogo nunca se descarta en silencio:** o se
extrae tal cual (§5, grados ASTM), o va a revisión.

### 7.3 El índice de confianza

**La confianza no la reporta el modelo.** La autoconfianza de un LLM está mal calibrada y no
es auditable: un "95 %" generado por el modelo es un número inventado con aspecto de evidencia,
y ponerlo en una celda contradice todo lo anterior.

Aquí la confianza la calcula el código como **el mínimo de cuatro factores medidos**:

| Factor | Cómo se obtiene | Valores |
|---|---|---|
| Procedencia | Categoría asignada por el código | EXTRAIDO 100 · DERIVADO 100 · INFERIDO 70 |
| Verificación de literal | ¿aparece en el texto, en su posición? | 100 / 0 |
| Acuerdo de segmentación | Votos de las 3 pasadas | 3/3 → 100 · 2/3 → 67 · 1/3 → 33 |
| Coherencia cruzada | ¿saltó alguna comprobación de §3? | 100 / 0 |

Ninguno es una opinión; los cuatro son observaciones. Y por ser un mínimo, **siempre hay un
motivo concreto**: "67 porque la segmentación fue 2 de 3", nunca "el sistema no está seguro".

```
confianza_celda  = min(procedencia, literal, segmentacion, coherencia)
confianza_linea  = min(confianza de sus celdas evaluables)
RESUELTA         <=>  confianza_linea == 100
```

**Nada por debajo de 100 sale como resuelto.** Sólo `EXTRAIDO` y `DERIVADO` alcanzan 100, y
sólo si además el literal se verificó, la segmentación fue unánime y ninguna comprobación
cruzada saltó.

Esto responde a *"dónde pones el umbral entre resuelta y revisión, y por qué ahí"* sin elegir
un número a ojo: **no hay umbral elegido. El umbral es 100.** O el valor viene por un camino
que no puede estar mal, o lo mira una persona. Es la traducción directa del cociente 1:50.000.

### 7.4 Riesgo residual, declarado

Esto no deja el riesgo en cero y no se va a presentar como si lo dejara.

Lo que sigue vivo: que el modelo vincule un valor **al elemento equivocado** cuando el texto es
genuinamente ambiguo y los dos elementos son plausibles. Eso no es alucinacion, es ambigüedad,
y lo cubre la regla de calidad no vinculada — que nunca se atribuye.

---

## 8. Medición

**Gold set.** Las 30 líneas anotadas a mano, con marca por celda: `cierta` / `interpretada` /
`indecidible`. Las indecidibles no puntúan como acierto o fallo, sino como consistencia con la
política declarada.

**Doble anotación.** Anotado dos veces, separado en el tiempo. El desacuerdo propio es la cota
superior de fiabilidad del gold set — la respuesta a *"¿cuánto te fías de él?"*.

**Corpus de estrés.** ~50 filas sintéticas que ejercitan lo que el MTO nunca toca: las 16
calidades sin usar (las 5 HV, GRADE/GRADO 5 y 8, 10.9, 304, 316...), 20 normas sin usar, los 5
acabados ausentes, `VARILLA ROSCADA`, formatos ASME y MSS SP, fracciones compuestas (`1-1/4"`),
longitudes con unidad explícita y suciedad unicode. **Sustituye a optimizar contra las 15 filas.**

### Métricas, con definición exacta

| Métrica | Definición |
|---|---|
| **Tasa de escape** | líneas `RESUELTA` con ≥1 atributo distinto del gold, **contando sólo celdas marcadas `cierta` o `interpretada`** (las `indecidible` se excluyen del numerador y se reportan aparte), / total de líneas. **Es el número que se compromete.** |
| Cobertura | líneas `RESUELTA` / total |
| Ruido de revisión | líneas en revisión que un humano cierra sin volver a ingeniería / líneas en revisión |
| Exactitud de segmentación | filas cuyo nº y tipo de líneas coincide con el gold / filas |
| Desglose por atributo | por cada uno de los 7: aciertos / celdas evaluables |
| Coste | € por fila procesada, medido de `usage` real |
| Latencia | segundos para 1.000 filas, extrapolado de tandas medidas |

**Ablaciones:** el arnés se ejecuta con cada componente desactivado y se rellena la tabla de
la sección 5. Ninguna casilla puede quedar con un adjetivo.

**Modelos:** el proveedor vive detrás de un puerto (`PuertoLLM`), con implementación OpenAI.
Se mide con **GPT-5.6 Luna** ($0,20/$1,20 por MTok) y **GPT-5.6 Terra** ($2/$12) y se reporta el
par (escape, coste/obra) de cada uno, con recomendación razonada. Luna cuesta ~10× menos: si
aguanta el escape, ése es el argumento; si no, se enseña cuánto se degrada. Cambiar de
proveedor o de modelo es un parámetro, no un refactor.

---

## 9. Front

Una sola vista, **Cola de compras**, con panel lateral de traza.

- Subir `.xlsx` → tabla de líneas con estado, procedencia visible por celda y filtros
- Filtrar las de revisión → panel con el motivo escrito y **el valor ya propuesto** → un clic
- Exportar agrupado por familia, listo para pedir
- El panel lateral muestra la traza completa: texto original, cómo se partió, qué tramo
  alimentó cada celda, qué regla se aplicó, qué procedencia

TanStack Table con virtualización: la tabla sigue fluida con 20.000 filas. Es el argumento de
escala sin decir una palabra.

---

## 10. Alcance

**Dentro:** familia tornillería, 7 atributos, 2 estados, un MTO por ejecución.

**Fuera, y consciente:**
- Reconciliación entre revisiones del MTO (rev. 12 contra rev. 9). El enunciado la nombra como
  el premio, pero requiere el maestro de materiales del cliente, que es una de las preguntas.
- Otras familias (tubería, válvulas, instrumentación).
- Persistencia y multiusuario. Un proceso, un fichero, memoria.
- Autenticación.

---

## 11. Riesgos en producción

1. **Deriva del vocabulario.** Un estudio externo nuevo escribe distinto y la cobertura cae sin
   avisar. Necesita monitor de tasa de revisión por origen.
2. **El maestro de materiales del cliente está sucio.** Normalizas impecablemente contra un
   catálogo que aguas abajo no cuadra: el sistema es correcto y el resultado inútil.
3. **Erosión de la cola.** Si la revisión crece, el comprador aprueba en bloque y el escape
   entra igual. Es riesgo de proceso, no de modelo: la UI no debe permitir aprobación en bloque
   de motivos distintos, y hace falta muestreo de auditoría.

---

## 12. Orden de construcción

Lo de arriba se entrega aunque falte lo de abajo.

1. Gold set de las 30 líneas
2. Motor de punta a punta con `SegmentadorFake`
3. **Prueba de humo del segmentador real** (~0,50 €, 20 min) — de-riesga lo único incierto
4. Front: Cola con panel de traza
5. Medición y ablaciones → nace el número comprometido
6. One-pager
7. *Si hay tiempo:* A3 construido y descartado; pulido

**Bloqueante:** `ANTHROPIC_API_KEY` con saldo (~25 € cubren todo el caso).
