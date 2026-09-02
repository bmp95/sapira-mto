# De aquí a producción

Bernabé Muñoz · Caso técnico Senior FDE · Anexo para la sesión

Responde a las tres preguntas de Adolfo: **timeline con hitos, gestión de recursos y QA en producción.**

---

## 1. Timeline: cinco puertas, no cinco fases

Cada puerta tiene un criterio de salida medible. Si no se cumple, no se pasa — y eso es lo que separa un piloto que se eterniza de un despliegue.

### Puerta 0 · Lo que ya está — hecho

Sistema funcionando sobre una familia y siete atributos, con escape medido en 300 filas no vistas.

**Criterio de salida:** cumplido.

### Puerta 1 · Validar el patrón de medida con vosotros — 2 semanas

Mi gold set lo he anotado yo. Eso vale para construir, no para comprometerse.

**Qué pasa aquí:** un comprador vuestro anota 100 líneas a ciegas. Comparamos con las mías. **La tasa de desacuerdo entre dos personas de vuestro equipo es la cota superior real de cualquier número que os prometa.** Si dos compradores discrepan en el 8 % de las celdas, hablar de un 97 % de acierto es ruido.

**Criterio de salida:** desacuerdo entre anotadores medido y por debajo del 5 %. Si sale más alto, el problema no es el sistema: es que no hay un criterio común, y eso hay que resolverlo antes de automatizar nada.

**Riesgo si se salta:** os comprometo un número contra mi propio criterio. Es exactamente el error que este caso pone a prueba.

### Puerta 2 · Piloto en sombra sobre una obra real — 4 semanas

El sistema procesa los MTO de una obra en paralelo al proceso actual. **Nadie compra con su salida.** Los compradores siguen trabajando como siempre y la comparación es silenciosa.

**Qué se mide:** tasa de escape real contra lo que compró el comprador, cobertura por origen de ingeniería, tiempo real de cierre de una revisión —que valida o tumba el supuesto de los 90 segundos—, y cuántas consultas a ingeniería se repiten.

**Criterio de salida:** escape por debajo del 1,5 % sobre al menos 600 líneas, y el tiempo de revisión medido, no supuesto.

**Por qué en sombra y no en piloto normal:** porque con un cociente de 1:50.000 el primer escape en producción cuesta más que todo el piloto. En sombra, un escape es un dato; en producción, son tres semanas de obra.

### Puerta 3 · Producción con una familia — 4 semanas

Tornillería, con el comprador cerrando la cola de revisión de verdad. El histórico empieza a llenarse.

**Criterio de salida:** el comprador prefiere la herramienta al Excel. Se mide por uso, no por encuesta: qué porcentaje de MTO se procesan con ella sin que nadie lo imponga.

### Puerta 4 · El histórico y la reconciliación entre revisiones — 6 semanas

Aquí está el valor grande. Cada respuesta de ingeniería se guarda contra clave canónica y las revisiones siguientes la heredan.

**Criterio de salida:** porcentaje de consultas evitadas por herencia. Es la métrica que justifica la fase.

### Puerta 5 · Más familias — a partir de ahí

Tubería, válvulas, instrumentación. Cada familia son sus tablas y su gold set; el motor no cambia.

**Criterio de salida por familia:** el mismo de la puerta 2.

**Total hasta producción con una familia: unas 10 semanas.** Hasta el histórico funcionando, 16.

---

## 2. Recursos

### Del lado del cliente

**Un comprador senior, 4 h/semana durante las puertas 1 y 2.** Es el recurso crítico y el que suele fallar. No es para "validar": es la fuente de la verdad. Sin él no hay patrón de medida y todo lo demás es opinión.

**Un segundo comprador, 8 horas en total**, sólo para la anotación ciega de la puerta 1. Sin dos anotadores no hay cota de fiabilidad.

**Un interlocutor de ingeniería, 2 h/semana.** Adolfo ya lo apuntó: *"tendrías que buscar una reunión con ellos y aclarar el tema"*. Hacen falta para cerrar lo que las reglas no deciden —la unidad de la longitud en los espárragos ASTM, el alcance del acabado en un set— y **son el cuello de botella real del sistema**: el 100 % de las revisiones son datos que ellos no escriben.

**Acceso a la base de datos de compras pasadas**, en lectura. Es contra lo que hay que reconciliar, y sin verla no se puede diseñar la clave canónica definitiva.

**Entre 3 y 5 MTO reales de obras distintas**, con orígenes de ingeniería distintos. El sistema está probado contra 15 filas suyas y 300 mías; hace falta variedad real.

### Del lado nuestro

**Un FDE a tiempo completo** durante las puertas 1 a 3. El trabajo no es montar agentes: es medir, decidir y defender los números delante del cliente.

**Medio ingeniero de datos** a partir de la puerta 4, para el histórico y la integración con su base de compras.

**Coste de infraestructura: despreciable.** 80 $ de modelo por obra completa. Lo digo antes de que lo pregunte el CFO, y añado que **por eso el coste no es el criterio de diseño**: si lo fuera, habría metido modelo en todas partes.

### Lo que NO hace falta, y conviene decirlo

No hacen falta científicos de datos ni entrenar nada. **El 90 % del sistema son tablas**, y ampliarlas es trabajo de un comprador con un Excel, no de un ingeniero. Cuando aparezca un vocabulario nuevo —un estudio que escriba en portugués— se arregla añadiendo filas a una tabla, no reentrenando un modelo.

---

## 3. QA en producción

### Lo que ya está construido

**Ocho invariantes** que impiden inventar y omitir. Si alguna se rompe, la línea no sale resuelta.

**Once comprobaciones de coherencia** que detectan que dos atributos escritos se contradicen.

**Procedencia por celda**: cada valor dice si se leyó, se dedujo o se decidió, y cada revisión dice **qué factor concreto la tumbó**. El sistema nunca dice "no estoy seguro".

**Corpus de estrés de 300 filas** con normas inventadas y formatos reales de proveedor. Se ejecuta como prueba de regresión: si un cambio introduce una invención, salta.

### Lo que hay que montar en producción, y no existe todavía

**Muestreo de auditoría.** Un 2 % de las líneas resueltas se revisan a mano cada semana, a ciegas. **Es la única forma de medir el escape sin gold set**, y es la métrica que de verdad importa cuando ya no hay patrón contra el que comparar.

**Monitor de tasa de revisión por origen.** Si un estudio concreto empieza a generar más revisiones, hay vocabulario nuevo. Es la alarma temprana de la deriva, y avisa **antes** de que caiga la cobertura.

**Alarma de aprobación en bloque.** Ésta es la importante y la menos obvia: si un comprador cierra veinte revisiones seguidas en treinta segundos, ha dejado de mirarlas. **Es el indicador de que el sistema ha dejado de servir aunque todas sus métricas internas sigan verdes.** Por eso la interfaz no debe permitir aprobar de golpe motivos distintos.

**Correcciones tras cerrar.** Cuántas veces se cambia un valor ya dado por bueno. Es el proxy del escape en producción.

**Registro de decisiones y sus interruptores.** Cada criterio que no es regla escrita del cliente vive tras un interruptor con nombre. Cuando el cliente dice "eso no lo hacemos así", se apaga y se mide lo que cuesta — no se discute.

### El estándar de calidad que propongo

| Métrica | Umbral | Qué pasa si se cruza |
|---|---|---|
| Tasa de escape (por muestreo) | < 1,5 % | Se para el despliegue y se investiga cada caso |
| Ruido de revisión | < 5 % | Revisar calibración: el sistema duda de más |
| Aprobaciones en bloque | < 10 % de los cierres | Alarma de erosión: hablar con el comprador |
| Tasa de revisión por origen | sin subidas > 10 pp | Vocabulario nuevo: ampliar tablas |

### Y una lección de esta construcción que va aquí

Durante el desarrollo aparecieron **doce casos de pruebas que pasaban midiendo otra cosa**: un test que comparaba una construcción rota contra sí misma, un guardián que miraba bytes del fichero en vez del comportamiento, una métrica cuya definición contaba como ruido lo que era dato ausente.

**La conclusión es el estándar de QA:** una prueba sólo vale si puede fallar. Cada guardián nuevo se verifica rompiendo el código a propósito y comprobando que salta. Un test que no puede fallar es peor que ninguno, porque da seguridad falsa — y en un sistema donde el fallo cuesta cincuenta mil euros, la seguridad falsa es el riesgo principal.
