# Familia TORNILLERÍA · Reglas de extracción y normalización

Documento de referencia del proyecto. Es el que usa hoy el equipo de compras.

Las secciones 1 a 8 son las reglas tal y como están escritas. La sección 9 recoge lo que estas
reglas **no** deciden.

---

## 1. El flujo

Es el mismo para todos los atributos:

1. **Extracción.** Se saca el valor que aparece en el MTO, y se mira si está en la lista de
   valores posibles o en una equivalencia reconocible.
2. **Normalización.** Se lleva al concepto normalizado usando la tabla del atributo, si la
   tabla lo permite.
3. **Resolución.** La línea queda `RESUELTA`, o pasa a `REVISION_MANUAL`.

Se extrae lo que aparece. Un atributo que el MTO no escribe no se rellena con el valor más
probable.

---

## 2. Los sets

Una fila del MTO puede describir un set completo: en la descripción aparecen a la vez el
tornillo (o el espárrago), la tuerca y la arandela. Cada elemento es un material distinto que
se compra por separado, así que la fila se separa en una línea por elemento.

```
MTO (1 fila)
1.0   STUD BOLT 7/8" X 130 LG, ASTM A193, GR B7
      W/2 HEX. NUT 7/8", ASTM A194, GR 2H, 2 WASHER 7/8", ASTM F436      40 uds

Salida (3 líneas)
L001   ESPARRAGO   ASTM A193   B7   7/8"   130    40
L002   TUERCA      ASTM A194   2H   7/8"   N/A    80
L003   ARANDELA    ASTM F436   --   7/8"   N/A    80
```

Lo que lo hace difícil es que **cada elemento no trae todos sus atributos**. Normalmente sólo
uno de ellos, casi siempre el tornillo o el espárrago, trae la medida.

**La única extrapolación que contemplan estas reglas es la de la medida.** Cuando en un set
sólo uno de los elementos tiene medida, esa medida puede extrapolarse al resto. Ningún otro
atributo se extrapola: en particular, la calidad de un elemento no se deduce de la del
tornillo, y si no consta, la línea va a revisión manual (sección 4).

---

## 3. Nombre / Descripción

**Valores posibles:** `TORNILLO`, `TUERCA`, `ARANDELA`, `VARILLA ROSCADA`, `ESPARRAGO`

| Detectado | Normalizado |
|---|---|
| THREADED ROD, VARILLA ROSCADA | VARILLA ROSCADA |
| STUD, ESPARRAGO, STUD BOLT | ESPARRAGO |
| SCREW, BOLT, TORNILLO | TORNILLO |
| NUT, TUERCA | TUERCA |
| WASHER, ARANDELA | ARANDELA |

El catálogo no distingue subtipos: un tornillo Allen y un tornillo hexagonal son los dos
`TORNILLO`, y una tuerca autoblocante es `TUERCA`. Lo que los diferencia es la norma.

---

## 4. Material

**Valores:** `AC` / `INOX` y otros materiales metálicos. Si no aparece ninguno de los dos, se
extrae el que aparezca.

No hay reglas fuera de la normalización semántica habitual: `ACERO`, `STEEL`, `acero` → `AC`.

> Ojo con la columna del MTO que se llama MATERIAL. En este MTO casi nunca contiene un
> material: contiene la calidad (`8.8`, `A4-70`) o la norma con su grado
> (`ASTM A193 GR B7`). El nombre de la columna no es el atributo.

---

## 5. Calidad

Valores posibles:

```
A2   A2-70   18-8   304   A2-80
A4   A4-70   316   A4-80
8.8   GRADE 5   10.9   GRADE 8   12.9
8     (sólo aplica a tuercas: fabricadas para acoplarse a tornillos de calidad 8.8)
10    (sólo aplica a tuercas: fabricadas para acoplarse a tornillos de calidad 10.9)
100HV   140HV   160HV   200HV   300HV
```

### Tabla de equivalencias

Se sigue tal cual. Dos valores del mismo grupo son equivalentes.

| Grupo | Valores equivalentes |
|---|---|
| G1 | A2, A2-70, 18-8, 304 |
| G2 | A2-80 |
| G3 | A4, A4-70, 316 |
| G4 | A4-80 |
| G5 | 8.8, GRADE 5, GRADO 5 |
| G6 | 10.9, GRADE 8, GRADO 8 |
| G7 | 12.9 |
| G8 | 8 |
| G9 | 10 |
| G10 | 100HV |
| G11 | 140HV |
| G12 | 160HV |
| G13 | 200HV |
| G14 | 300HV |

- Si aparece un valor **marcado como calidad** que está fuera de la lista, se extrae tal cual.
  Es el caso de los grados ASTM: `GR B7`, `GR 2H`.
- Si no se sabe si un valor está marcado como calidad, **no se extrae**.
- **Si falta el campo Calidad, el item se clasifica como revisión manual.** El campo puede no
  existir, especialmente en sets de tornillería. Lo introduce una persona. Si no se introduce,
  se permite crear el elemento sin calidad.

**Esta es la única regla de revisión que contienen estas reglas.**

---

## 6. Medida

Siempre un valor numérico, en pulgadas (`"`) o en métrica (`M`).

**No hay equivalencias entre las dos.** Cuando se encuentra una, sólo se busca en esa medida.

Se extrapola dentro de un set (sección 2).

---

## 7. Longitud

Siempre un valor numérico, en pulgadas (`"`) o en milímetros (`mm`). No hay equivalencias.

**Campo obligatorio para toda la tornillería excepto para tuerca y arandela.**

---

## 8. Norma

Formatos esperables: `DIN...`, `DIN EN...`, `ISO...`, `ASME...`, `ASTM...`, `MSS SP...`

Las siguientes **no se consideran normas** y se normalizan a su equivalente:

| Detectado | Resultado |
|---|---|
| DIN 84 | ISO 1207 |
| DIN 440 | ISO 7094 |
| DIN 603 | ISO 8677 |
| DIN 912 | ISO 4762 |
| DIN 913 | ISO 4026 |
| DIN 916 | ISO 4029 |
| DIN 931 | ISO 4014 |
| DIN 933 | ISO 4017 |
| DIN 934 | ISO 4032 |
| DIN 935 | ISO 7035 |
| DIN 936 | ISO 4035 |
| DIN 960 | ISO 8765 |
| DIN 961 | ISO 1665 |
| DIN 963 | ISO 2009 |
| DIN 965 | ISO 7046 |
| DIN 980 | ISO 7042 |
| DIN 982 | ISO 7040 |
| DIN 985 | ISO 10511 |
| DIN 6923 | EN 1661 |
| DIN 7981 C-H | ISO 7049 |
| DIN 7982 C-H | ISO 7050 |
| DIN 7985 | ISO 7045 |
| DIN 7991 | ISO 10642 |
| DIN 9021 | ISO 7093 |
| DIN 125, DIN 125 A | ISO 7089 |

Una norma DIN que no esté en esta tabla se conserva tal cual: no todas tienen equivalente.
Una vez normalizada, la norma se usa con su estructura exacta.

---

## 9. Acabado

**Valores posibles:** `GEOMET`, `DACROMET`, `GALVANIZADO EN CALIENTE`, `CINCADO`, `PAVONADO`,
`FOSFATADO`, `BICROMATADO`

| Detectado | Normalizado |
|---|---|
| GEOMET | GEOMET |
| DACROMET | DACROMET |
| GALVANIZADO EN CALIENTE, HOT DIP GALVANIZED, GALVA, HDG | GALVANIZADO EN CALIENTE |
| CINCADO, ZINCADO, ZN, ZP, ZINC PLATED | CINCADO |
| PAVONADO, BL, NEGRO | PAVONADO |
| FOSFATADO, PHOSPHATED | FOSFATADO |
| BICROMATADO, YZP, YELLOW ZINC PLATED | BICROMATADO |

- Lo más habitual es que no aparezca, y entonces se queda en blanco. En blanco es un valor
  válido y **no** manda la línea a revisión.
- **No se mezclan items con acabado con items sin acabado.** Un tornillo cincado y el mismo
  tornillo sin acabado son dos materiales distintos.

---

## 10. Lo que estas reglas no deciden

Estas reglas son las que hay, y no cubren todo lo que aparece en un MTO real. Los puntos de
abajo están sin cerrar a propósito.

No hay una respuesta escrita para ellos. Lo que se espera es que se detecten, que se tome una
decisión y que la decisión se pueda defender, no que se resuelvan por lo que parezca más
probable. Si alguno te bloquea, pregunta.

1. **Material.** La regla dice extraerlo del MTO, y el MTO casi nunca lo escribe. No hay regla
   para derivarlo de la calidad ni de la norma.
2. **Falta la norma.** La única regla de revisión escrita es la de la calidad. No hay ninguna
   para una línea sin norma.
3. **Longitud sin unidad.** `7/8" X 130`: el 130 no lleva unidad, y las reglas no dicen qué
   hacer con eso.
4. **Acabado dentro de un set.** La extrapolación escrita cubre sólo la medida. Cuando el
   acabado se escribe una vez para una fila que describe un set entero, no está dicho a qué
   elementos alcanza. Y por la regla de no mezclar, la respuesta cambia el material.
5. **Cantidades.** No hay reglas. `W/2 HEX. NUT` sobre 40 espárragos, y `with NUT` sin
   multiplicidad.
6. **Coherencias.** Está escrito que el `8` y el `10` sólo aplican a tuercas. No está escrito
   lo contrario, y en el MTO hay una tuerca con calidad `8.8`.
