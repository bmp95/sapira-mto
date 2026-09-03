## Ablaciones sobre el MTO del cliente (30 lineas)

| Configuracion | Que compra | Resueltas | Delta |
|---|---|---|---|
| base (todas activas) |  | 13/30 | 0 |
| sin derivar_material | deduce el material de la calidad y de la norma | 13/30 | 0 |
| sin columna_material_al_principal | usa la columna MATERIAL como ultimo respaldo | 11/30 | -2 |
| sin acabado_de_cierre_a_todo_el_set | extiende el acabado final a todo el set | 13/30 | 0 |
| sin longitud_imperial_sin_unidad_a_revision | no supone milimetros en un ASTM | 16/30 | +3 |
| sin dimensiones_en_ambito_a_revision | detecta la pieza principal sin nombrar | 13/30 | 0 |

## Ablaciones de coherencias sobre el mismo MTO

| Configuracion | Resueltas | Delta |
|---|---|---|
| base (todas activas) | 13/30 | 0 |
| sin calidad_solo_tuerca | 13/30 | 0 |
| sin calidad_solo_arandela | 13/30 | 0 |
| sin inox_acabado | 13/30 | 0 |
| sin sistema_medida | 13/30 | 0 |
| sin grado_astm_nombre | 13/30 | 0 |
| sin material_vs_calidad | 13/30 | 0 |
| sin material_vs_norma | 13/30 | 0 |
| sin nombre_vs_norma | 13/30 | 0 |
| sin material_vs_acabado | 13/30 | 0 |
| sin longitud_tuerca_arandela | 13/30 | 0 |
| sin longitud_medida | 13/30 | 0 |
| sin esparrago_equivale_a_varilla | 12/30 | -1 |
| SIN NINGUNA coherencia | 13/30 | 0 |

**Por que apagar un solo interruptor pierde una linea y apagarlos todos no.** `esparrago_equivale_a_varilla` no es una comprobacion: es un SUPRESOR de `nombre_vs_norma` para ese par concreto. La linea L022 dice `Conjunto esparrago M20 x 200 DIN 975`, y DIN 975 es varilla roscada. Con el supresor apagado salta NOMBRE_CONTRADICE_NORMA y la linea va a revision; con TODAS apagadas, `nombre_vs_norma` tampoco corre y no hay nada que saltar.

Eso le pone precio a una pregunta abierta para el cliente: **si esparrago y varilla roscada son una referencia o dos en su maestro vale exactamente una linea de treinta.** No es una decision que pueda tomar yo.

**Ninguna coherencia mueve el numero en este MTO, y eso NO significa que sobren.** Significa que el MTO del cliente es coherente consigo mismo: no hay ni una fila donde dos atributos escritos se contradigan. Lo que compran las coherencias solo se ve contra texto que si se contradice, y para eso esta el corpus de estres.