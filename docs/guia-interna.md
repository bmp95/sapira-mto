# Guía interna · Todo lo que hay que saber para defender esto

Uso propio. No se entrega. Escrito para que puedas contestar cualquier pregunta sin mirar el código.

---

## 1. Qué hace el sistema, en una frase

Coge un Excel donde cada fila describe tornillería en prosa, y devuelve **una línea por material comprable**, con siete atributos normalizados, diciendo de cada uno **de dónde salió** y **cuánto se fía**. Lo que no puede resolver con certeza, lo manda a una persona con la pregunta ya formulada.

## 2. El flujo, paso a paso

Sigue una fila real de principio a fin. Es la fila 1 de su MTO:

```
STUD BOLT 7/8" X 130 LG, ASTM A193, GR B7 W/2 HEX. NUT 7/8", ASTM A194, GR 2H, 2 WASHER 7/8", ASTM F436
```

**Paso 1 · Lectura y saneado** — `motor/lectura_mto.py`, `motor/saneado.py`
Se lee el Excel y se limpia el texto: comillas tipográficas a rectas, el símbolo de diámetro a `DIA`, espacios colapsados, y las normas a forma única (`DIN931`, `DIN-931` y `DIN 931` acaban iguales). **Todo código, cero modelo.**

**Paso 2 · Segmentación** — `motor/segmentador.py` + `motor/puerto_gemini.py`
Aquí y sólo aquí actúa el modelo. Se le da la fila y devuelve tres cosas: los **elementos** con el trozo de texto de cada uno, el **ámbito de fila** (lo que describe la fila entera sin estar pegado a nadie) y los **conectores**.

Para esta fila devuelve tres elementos: `STUD BOLT 7/8" X 130 LG, ASTM A193, GR B7`, `2 HEX. NUT 7/8", ASTM A194, GR 2H` y `2 WASHER 7/8", ASTM F436`.

Detalle importante: **se le pide el texto literal, no las posiciones.** El código busca ese texto en el original y calcula la posición él. Si le pidiéramos la posición, el modelo podría darnos una que no corresponde y no tendríamos forma de saberlo. Pidiendo texto, o está o no está. Cuando no está, se descarta el elemento con motivo `NO_LITERAL` — y pasa de verdad, se ve en los registros.

**Paso 3 · Invariantes estructurales** — `motor/invariantes.py`
Antes de mirar ningún atributo, tres comprobaciones sobre cómo se partió:
- **Cobertura**: ¿está todo el texto asignado a algo? Caza el elemento omitido, que ninguna comprobación por elemento puede ver.
- **Sin solapamiento**: dos elementos no pueden reclamar el mismo trozo.
- **Recuento independiente**: un escáner de código cuenta los sustantivos de tipo y se compara con lo que dijo el modelo.
- **Sin dimensiones en el ámbito de fila**: si aparece un diámetro o una longitud suelta ahí, hay una pieza sin nombrar.

**Paso 4 · Extracción y normalización** — `motor/catalogos.py`
Dentro del tramo de cada elemento se buscan los valores contra las cuatro tablas cerradas. **Por token y el más largo primero, nunca por subcadena.**

**Paso 5 · Derivaciones** — `motor/derivaciones.py`
Calidad→material, norma→nombre, y norma→material donde la norma lo fija sola.

**Paso 6 · Coherencias** — `motor/coherencias.py`
Once comprobaciones que no rellenan nada, sólo detectan que dos atributos escritos se contradicen.

**Paso 7 · Confianza y estado** — `motor/confianza.py`
Cada celda recibe el mínimo de cuatro factores. La línea toma el mínimo de sus celdas. `RESUELTA` si es exactamente 100.

**Paso 8 · Cantidades** — `motor/cantidades.py`
`W/2` sobre 40 espárragos son 80 tuercas. Sin multiplicador, 1:1.

Resultado: **tres líneas** — 40 espárragos resueltos salvo la longitud, 80 tuercas resueltas, 80 arandelas a revisión porque `ASTM F436` es una norma, no un grado, y nadie escribió la dureza.

## 3. La idea central: la procedencia

Es lo único que hay que entender de verdad. Cada valor lleva una etiqueta de **de dónde salió**:

| Etiqueta | Significa | Vale |
|---|---|---|
| `EXTRAIDO` | Está escrito en el MTO | 100 |
| `DERIVADO` | Se deduce de otro atributo, y la alternativa **no existe** | 100 |
| `INFERIDO` | Confianza alta, pero es un juicio | 70 → revisión |
| `AUSENTE` | No hay dato | — |

**La frontera entre derivado e inferido es la pregunta: ¿existe la alternativa?**

`8.8` no puede ser inox. Si lo fuera se llamaría `A4-70`, porque 8.8 pertenece a ISO 898-1 —la norma del acero al carbono— y A4-70 a ISO 3506 —la del inox—. **Los dos sistemas de designación son disjuntos.** No es que sea probable: es que la alternativa no existe. Eso es derivado.

`7/8" X 130` en pulgadas serían 3,3 metros, que no es un espárrago de brida. Pero **existir, existe**: ASTM admite las dos unidades. Eso es inferido, y va a revisión.

Esa distinción es lo que el enunciado premia. Si derivas el material **y** rellenas la longitud **y** atribuyes el acabado, y a todo lo llamas deducción, pareces alguien racionalizando lo que le convenía. Si derivas el material y **te niegas** a llamar deducción a lo de la longitud, usando el mismo criterio en tu contra, el criterio es real.

## 4. Los cuatro factores de confianza

**La confianza no la reporta el modelo.** Un "95 %" generado por un LLM es un número inventado con aspecto de evidencia. Aquí la calcula el código como el **mínimo** de cuatro hechos observados:

| Factor | Qué mide |
|---|---|
| Procedencia | Extraído y derivado valen 100, inferido 70 |
| Literal | ¿El texto está de verdad en esa posición del origen? 100 o 0 |
| Segmentación | Acuerdo entre pasadas |
| Coherencia | ¿Saltó alguna de las once comprobaciones? 100 o 0 |

Por ser un mínimo, **siempre hay un culpable concreto**. El sistema nunca dice "no estoy seguro": dice *"la celda longitud se queda en 70 por el factor procedencia"*.

## 5. Estructura del agente

**Sólo hay un agente en producción: el segmentador.** Todo lo demás es código determinista.

Dos propiedades hacen que la alucinación sea estructuralmente imposible en la mitad semántica:

**El modelo nunca ve los catálogos.** Si le enseñas los 21 valores de calidad, "ayuda": ve algo raro y lo aproxima al más parecido. Eso es normalizar, y normalizar es del código. **El modelo dice qué pone; el código decide qué significa.**

**El extractor ve sólo su tramo.** Cuando el extractor trabaja sobre el trozo de la tuerca, no puede coger la calidad de la arandela porque nunca ve ese texto. No es una instrucción del prompt: es que no está ahí.

### Los tres que no existen, y por qué

**El extractor como segundo agente.** Estaba diseñado. Al implementarlo resultó que, con catálogos cerrados, buscar por token dentro del tramo lo hace igual de bien y sin ninguna llamada. No lo construí.

**El árbitro de ambigüedad.** Resolvería la calidad de las tuercas sin calidad propia. Sube cobertura y sube el escape a un ritmo del orden del 5 %. Con el cociente 1:50.000 haría falta bajar del 0,002 % para que compensara. Está 2.500 veces por encima. No hay frecuencia plausible que lo justifique.

**La autoconsistencia por triplicado.** Ésta es la buena: **estaba en mi diseño como pilar.** Tres pasadas votando entre sí para detectar inestabilidad. La construí, y luego la medí: 90 llamadas reales, 15 filas, a temperatura 0 y a 0,7. **Cero desacuerdos.** No detecta nada y triplica el coste. Peor aún: el factor `segmentación` valía siempre 100, o sea que **sugería una protección que no existía**.

Que te pregunten por esto es lo mejor que te puede pasar. Un componente que construyes, mides y borras con el número delante vale más que tres defendidos con adjetivos.

## 6. Los descubrimientos que hay que contar

### El patrón que apareció doce veces

**La evidencia decía verde y medía otra cosa.** Doce veces en esta construcción, y varias fueron culpa mía:

1. El diccionario de comillas se corrompió al guardar el fichero, y **el test que debía cazarlo se corrompió igual** y siguió pasando.
2. Un test guardián que miraba si ciertos bytes estaban en el fichero, en vez de mirar el diccionario. Pasaba con el diccionario roto.
3. Un test de catálogo que pasaba con el catálogo vacío.
4. La cobertura penalizaba los conectores, y en vez de arreglar el código se estiró un valor del test para que cuadrara.
5. Un test que comprobaba "¿hay algún carácter acentuado?" en vez de "¿pone *austenítico*?". Pasaba con la palabra mal escrita.
6. Un test que comparaba **una construcción rota contra sí misma**: el mismo error en el código y en la prueba, así que la prueba confirmaba el error.
7. Mi propia verificación buscaba la grafía *anterior* del error, así que dijo "ninguno" con el error delante.
8. La definición de ruido de revisión que escribí daba 82 % contando como ruido líneas donde el dato genuinamente no existía. El número real era 0 %.
9. El evaluador del blind set comparaba `N/A` contra vacío como si fueran distintos, e inflaba el escape del 0,5 % al 44 %.
10. El mismo evaluador buscaba el valor **normalizado** dentro del texto crudo, marcando como invención toda normalización correcta: `ZINCADO`→`CINCADO` salía como alucinación.
11. La autoconsistencia era vacua porque la caché hacía que las tres pasadas leyeran la misma entrada.
12. El front decía "o arrastra el MTO aquí" y **no había implementación de arrastre**. La prueba inyectaba el fichero directamente, así que confirmaba el flujo posterior pero no que el arrastre existiera.

**La lección:** la única prueba que vale es la que puede fallar. Un guardián que no guarda es peor que ninguno, porque da seguridad falsa.

### El blind set encontró lo que ningún test encontró

300 filas inventadas destaparon tres bugs que las 15 del cliente jamás habrían mostrado:

**Un corte de red tiraba el lote entero.** 199 filas perdidas por un parpadeo. Arreglado con reintento e aislamiento por fila.

**Sólo se leía el primer tramo del ámbito de fila.** Cuando el modelo devuelve el cierre partido en dos —`['8.8', 'CINCADO']`— el acabado se perdía. **Causaba 27 de los 28 escapes.** Invisible con el segmentador de guion, porque allí el cierre venía en un tramo único.

**Un modo de fallo que el diseño no contemplaba.** Los formatos reales de proveedor como `3/4" IN DIA X 200MM LONG, FULLY THREADED, C/W 1 HEAVY HEXAGON NUTS` **no nombran la pieza principal**. El modelo mete su descripción en el ámbito de fila. **Ni la cobertura ni el recuento de sustantivos pueden cazarlo**: no falta texto ni sobra elemento, hay una clasificación equivocada. Se cerró con una invariante nueva —el ámbito de fila puede llevar calidad y acabado, nunca dimensiones— y **sin inventar la pieza que falta**.

### Los fantasmas numéricos

Tres veces apareció el mismo tipo de fallo: un número que en su catálogo es una calidad válida, escondido dentro de otra cosa.

- `M10` producía la calidad `10`
- `5/8"` producía la calidad `8`, porque el guardián de tokens excluía letras y guiones **pero no la barra**
- `x 304` producía la calidad `304`, que es **inox** — un tornillo de acero clasificado como inoxidable

Los dos últimos los encontró el corpus de estrés y **el tercero lo encontró un revisor discrepando de una instrucción mía equivocada**. Se cerró con una regla general, no con una lista: *si la clave del catálogo es sólo dígitos, exige posición de calidad*. Es lo que dice su propia sección 5: *"si no se sabe si un valor está marcado como calidad, no se extrae"*.

### La trampa del `AUTOBLOCANTE`

`BL` es alias de PAVONADO en su tabla de acabados. `AUTOBLOCANTE` contiene `BL`. Es el único alias de dos letras de la tabla y la única palabra del MTO que lo contiene, y están en la misma fila. **No es casualidad: está plantado.** Un normalizador por subcadena clasifica esa tuerca como pavonada y cincada a la vez, que por su sección 9 son dos materiales distintos.

## 7. Las cifras, y qué significa cada una

| Cifra | Valor | Qué dice |
|---|---|---|
| Cobertura en su MTO | 43,3 % | Lo que el sistema resuelve solo |
| **Tasa de escape** | **0 %** medido, **< 1,5 %** comprometido | Lo que cuesta dinero |
| **Ruido de revisión** | **0 %** | El sistema no duda de más ni una vez |
| Revisiones por dato ausente | 100 % | Las 17 son datos que su MTO no trae |
| Blind set, escape | 0 % sobre 200 no vistas | Generaliza |
| Blind set, invenciones | 0 sobre 100 adversarias | No se inventa nada |
| Coste | 0,0008 $/fila | ~80 $ por obra completa |
| Latencia | 0,83 s/fila | 1.000 filas en ~14 minutos |

**Por qué me comprometo a 1,5 % y no a 0 %:** cero sucesos en 200 pruebas no significa cero. Con esa muestra, el límite superior honesto al 95 % de confianza es aproximadamente `3/200`, o sea 1,5 %. Comprometerse al cero medido sería vender humo.

**El par de números que más dice:** ruido de revisión 0 % y revisiones por dato ausente 100 %. Significa que **la cobertura no la limita el sistema, la limita su ingeniería**. Es la respuesta con datos a "cómo asumes problemas que no son técnicamente tuyos".

## 8. Las ablaciones

| Política apagada | Resueltas | Δ |
|---|---|---|
| *base* | 13/30 | |
| Derivar material de la calidad | 13/30 | **0** |
| Leer la columna MATERIAL | 11/30 | −2 |
| Extender el acabado al set | 13/30 | **0** |
| Longitud imperial a revisión | 16/30 | **+3** |

**Tres de las cuatro decisiones que más discutimos no mueven el número.** Derivar el material —la más debatida— no cambia ni una línea, porque un material ausente no bloquea. Sigue teniendo sentido, pero no por el motivo que le habríamos atribuido.

Ser conservador con la longitud ASTM **cuesta 3 líneas, diez puntos de cobertura**. Ése es el precio exacto de no suponer una unidad.

## 9. Preguntas que te van a hacer, y la respuesta

**"¿Cómo sé que no se equivoca?"**
No lo sabes porque el sistema lo diga. Lo sabes porque cada valor se verifica contra el texto de origen, porque cada revisión declara qué factor concreto la tumbó, y porque durante la construcción aparecieron doce pruebas que mentían y se corrigieron.

**"Un 43 % de cobertura es poco."**
La cobertura no la limita el sistema. De las 17 líneas que van a revisión, **las 17 son datos que su MTO no trae**: ninguna arandela de sus quince filas lleva dureza. El ruido de revisión es cero. Si su ingeniería escribe la dureza, la cobertura sube sola.

**"¿Y si el MTO viene escrito de otra forma?"**
Le pasé 300 filas que no había visto, con formatos reales de proveedor de tubería. Escape cero. Y le pasé 100 adversarias con normas inventadas y nombres de pieza que me inventé: cero invenciones.

**"¿Por qué sólo un agente?"**
Porque medí los otros tres. El extractor no mejora nada frente a una tabla. El árbitro sube el escape más de lo que sube la cobertura. Y la autoconsistencia, que estaba en mi diseño como pilar, la medí con 90 llamadas: cero desacuerdos. Construir, medir y borrar.

**"Un A4-70 es inox, eso lo sabe cualquiera. ¿Por qué no lo rellenas?"**
Lo relleno. Tengo la tabla y cubre los 21 valores de su catálogo. Lo que no hago es rellenar lo que sólo es probable.

**"¿Cuánto cuesta?"**
Ochenta dólares de modelo por obra completa. Frente a las 2.500 horas de comprador que hoy cuesta leer esas mismas filas.

## 10. Lo que falta, y hay que decirlo

- **El histórico de respuestas**: diseñado y especificado, no construido. Es el mayor valor pendiente.
- **La segunda anotación del gold set**: falta tu pasada a ciegas para medir tu desacuerdo contigo mismo, que pone cota a todo lo demás.
- **El gold set es pre-anotado y revisado, no independiente.** Yo lo rellené y tú lo validaste. Hay que decirlo.
- **Sin cortacircuitos**: si la clave caduca a mitad de un MTO de veinte mil filas, el sistema reintenta fila a fila hasta el final en vez de parar y avisar.
- **Idiomas**: portugués, italiano y alemán no están en el catálogo de nombres. Se arregla añadiendo filas a una tabla.
