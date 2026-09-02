from pathlib import Path

import openpyxl

from datos.guion_falso import puerto_de_guion
from motor.coherencias import TODAS_ACTIVAS
from motor.lectura_mto import FilaMTO, leer_mto
from motor.modelos import Elemento, Estado, Procedencia, Segmentacion
from motor.pipeline import (CODIGO_FALLO_DE_PROCESO, POLITICAS_POR_DEFECTO,
                            _calidad_de_columna_material, _procesar_fila,
                            contar_fallos_de_proceso, procesar_mto)
from motor.puerto_llm import PuertoFalso

RUTA = Path("datos/MTO_tornilleria.xlsx")


def _con_politica(nombre: str, valor: bool) -> dict[str, bool]:
    return {**POLITICAS_POR_DEFECTO, nombre: valor}


def test_quince_filas_dan_treinta_lineas():
    lineas = procesar_mto(RUTA, puerto_de_guion())
    assert len(lineas) == 30


def test_reparto_por_tipo():
    lineas = procesar_mto(RUTA, puerto_de_guion())
    tipos = [l.nombre.valor for l in lineas]
    assert tipos.count("TUERCA") == 11
    assert tipos.count("ARANDELA") == 7


def test_las_siete_arandelas_van_a_revision_por_falta_de_calidad():
    lineas = procesar_mto(RUTA, puerto_de_guion())
    arandelas = [l for l in lineas if l.nombre.valor == "ARANDELA"]
    assert len(arandelas) == 7
    assert all(l.estado is Estado.REVISION_MANUAL for l in arandelas)
    assert all(l.calidad.procedencia is Procedencia.AUSENTE for l in arandelas)


def test_cantidades_de_la_fila_uno():
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion())
              if l.fila_origen == 1]
    assert sorted(l.cantidad for l in lineas) == [40, 80, 80]


def test_ninguna_celda_sin_procedencia():
    lineas = procesar_mto(RUTA, puerto_de_guion())
    assert len(lineas) > 0
    for l in lineas:
        for nombre, celda in l.celdas().items():
            assert celda.procedencia is not None, f"{l.id}.{nombre} sin procedencia"


def test_longitud_imperial_sin_unidad_es_inferida():
    """Decision seccion 4.3 del diseno: fila 12, 'STUD BOLT 3/4" X 110 LG, ASTM A193,
    GR B7'. La norma es imperial (ASTM) y el 110 no trae unidad: la
    alternativa (110 pulgadas = 2,8 m) existe pero es absurda, asi que es
    INFERIDO, no DERIVADO, y la linea va a revision con el valor propuesto
    en el motivo -- no en silencio."""
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion()) if l.fila_origen == 12]
    assert len(lineas) == 1
    linea = lineas[0]
    assert linea.longitud.procedencia is Procedencia.INFERIDO
    assert linea.longitud.literal == "110"
    assert linea.estado is Estado.REVISION_MANUAL
    motivo = next(m for m in linea.motivos if m.codigo == "LONGITUD_SIN_UNIDAD")
    assert motivo.valor_propuesto is not None
    assert "110" in motivo.valor_propuesto


def test_linea_sin_norma_va_a_revision():
    """Decision seccion 4.2 del diseno: fila 8, 'HEX BOLT M16 x 70 c/w NUT AND
    WASHER, 8.8, ZN' no menciona DIN/ISO/ASTM/ASME/MSS en ningun tramo.
    Sin norma no se puede pedir a un proveedor (motivo SIN_NORMA), y esto
    manda a revision incluso al tornillo, que por lo demas trae calidad y
    acabado propios."""
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion()) if l.fila_origen == 8]
    assert len(lineas) == 3
    for linea in lineas:
        assert linea.norma.procedencia is Procedencia.AUSENTE
        assert linea.estado is Estado.REVISION_MANUAL
        assert any(m.codigo == "SIN_NORMA" for m in linea.motivos)


def test_la_columna_material_da_la_calidad_del_principal():
    """Ronda de correccion: fila 2, 'BOLT DIN 931 M20x90 with NUT DIN 934 M20'.
    La descripcion no menciona ninguna calidad en absoluto, pero la columna
    MATERIAL del xlsx trae 'A4-70' -- la del tornillo (evidencia: fila 7,
    donde MATERIAL coincide exactamente con la calidad propia del
    elemento principal y no con la de la tuerca). El tornillo pasa a
    resolverse con esa calidad, procedencia EXTRAIDO y el span apuntando a
    la columna MATERIAL, no a la descripcion."""
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion()) if l.fila_origen == 2]
    assert len(lineas) == 2
    tornillo = next(l for l in lineas if l.nombre.valor == "TORNILLO")
    assert tornillo.calidad.valor == "A4-70"
    assert tornillo.calidad.procedencia is Procedencia.EXTRAIDO
    assert tornillo.estado is Estado.RESUELTA


def test_la_columna_material_no_alcanza_a_los_demas_elementos():
    """Misma fila 2: la calidad de la columna MATERIAL es del tornillo
    (elemento principal) y nunca se propaga a la tuerca -- es la regla mas
    importante del caso. La tuerca sigue en revision por SIN_CALIDAD."""
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion()) if l.fila_origen == 2]
    assert len(lineas) == 2
    tuerca = next(l for l in lineas if l.nombre.valor == "TUERCA")
    assert tuerca.calidad.procedencia is Procedencia.AUSENTE
    assert tuerca.estado is Estado.REVISION_MANUAL
    assert any(m.codigo == "SIN_CALIDAD" for m in tuerca.motivos)


def test_de_la_columna_solo_se_toma_lo_que_es_calidad():
    """La columna MATERIAL de la fila 1 dice 'ASTM A193 GR B7/A194 GR 2H':
    una norma con su grado, no una calidad suelta. Del texto entero solo se
    reconoce 'GR B7' como calidad (la del elemento principal, el
    esparrago), nunca la cadena completa ni el grado de la tuerca (GR 2H).

    Se prueba el extractor directamente y no a traves de procesar_mto()
    porque en la fila 1 real el esparrago ya trae su propia calidad en el
    tramo de la descripcion ('GR B7'), asi que el pipeline nunca llega a
    consultar la columna MATERIAL para esa fila -- este test verifica el
    extractor en el caso exacto en que si haria falta."""
    resultado = _calidad_de_columna_material("ASTM A193 GR B7/A194 GR 2H")
    assert resultado is not None
    valor, literal, _span = resultado
    assert valor == "GR B7"
    assert literal == "GR B7"


def test_por_defecto_todo_activo_da_13_resueltas_de_30():
    """Test de no regresion explicito: con las cuatro politicas activas (el
    valor por defecto) el numero comprometido es 13 lineas RESUELTA de 30.
    Cualquier cambio futuro que mueva la cobertura tiene que hacer saltar
    este test, no descubrirse mirando el CSV a ojo."""
    lineas = procesar_mto(RUTA, puerto_de_guion())
    assert len(lineas) == 30
    resueltas = [l for l in lineas if l.estado is Estado.RESUELTA]
    assert len(resueltas) == 13


def test_apagar_derivacion_de_material_deja_el_campo_ausente():
    """Fila 4: el tornillo trae calidad 8.8 propia (del ambito de fila) y
    con la politica activa deriva material AC. Con `derivar_material` en
    False esa derivacion no se aplica: el material queda AUSENTE aunque la
    calidad se siga resolviendo con normalidad."""
    politicas = _con_politica("derivar_material", False)
    lineas = procesar_mto(RUTA, puerto_de_guion(), politicas=politicas)
    tornillo = next(l for l in lineas if l.fila_origen == 4 and l.nombre.valor == "TORNILLO")
    assert tornillo.calidad.valor == "8.8"
    assert tornillo.material.procedencia is Procedencia.AUSENTE
    assert tornillo.material.valor is None


def test_apagar_la_columna_material_devuelve_a_revision_los_tornillos_de_filas_2_y_3():
    """Con `columna_material_al_principal` en False no se lee la columna
    MATERIAL del xlsx: las filas 2 y 3, cuya descripcion no trae ninguna
    calidad en el texto, vuelven a REVISION_MANUAL por SIN_CALIDAD -- el
    estado de antes de la ronda de correccion anterior."""
    politicas = _con_politica("columna_material_al_principal", False)
    lineas = procesar_mto(RUTA, puerto_de_guion(), politicas=politicas)
    tornillo2 = next(l for l in lineas if l.fila_origen == 2 and l.nombre.valor == "TORNILLO")
    tornillo3 = next(l for l in lineas if l.fila_origen == 3 and l.nombre.valor == "TORNILLO")
    for tornillo in (tornillo2, tornillo3):
        assert tornillo.calidad.procedencia is Procedencia.AUSENTE
        assert tornillo.estado is Estado.REVISION_MANUAL
        assert any(m.codigo == "SIN_CALIDAD" for m in tornillo.motivos)
    resueltas = [l for l in lineas if l.estado is Estado.RESUELTA]
    assert len(resueltas) == 11


def test_apagar_el_acabado_de_cierre_deja_sin_acabado_a_tuercas_y_arandelas():
    """Fila 4: 'BOLT DIN 933 M16x60 with NUT DIN 934 and WASHER DIN 125,
    8.8, zinc plated'. Con `acabado_de_cierre_a_todo_el_set` en False el
    acabado de cierre (CINCADO) solo alcanza al elemento principal (el
    tornillo); la tuerca y la arandela se quedan sin acabado, no con un
    acabado INFERIDO."""
    politicas = _con_politica("acabado_de_cierre_a_todo_el_set", False)
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion(), politicas=politicas)
              if l.fila_origen == 4]
    assert len(lineas) == 3
    tornillo = next(l for l in lineas if l.nombre.valor == "TORNILLO")
    tuerca = next(l for l in lineas if l.nombre.valor == "TUERCA")
    arandela = next(l for l in lineas if l.nombre.valor == "ARANDELA")
    assert tornillo.acabado.valor == "CINCADO"
    assert tornillo.acabado.procedencia is Procedencia.EXTRAIDO
    assert tuerca.acabado.procedencia is Procedencia.AUSENTE
    assert arandela.acabado.procedencia is Procedencia.AUSENTE


def test_el_principal_se_decide_por_tipo_no_por_posicion():
    """Segmentador real, fila con la tuerca escrita antes que el tornillo:
    '2 TUERCAS DIN 934 M20 y 2 ARANDELAS DIN 125 para TORNILLO DIN 931
    M20x90, zincado'. Con `datos[0]` como principal (la logica de antes de
    este arreglo) la tuerca se habria quedado con la calidad de la columna
    MATERIAL y el acabado del cierre de fila. El principal se decide por
    tipo (esparrago/tornillo/varilla roscada), no por posicion: el
    tornillo es el principal aunque vaya tercero en el texto."""
    texto = ("2 TUERCAS DIN 934 M20 y 2 ARANDELAS DIN 125 para TORNILLO "
             "DIN 931 M20x90, zincado")
    seg = Segmentacion(
        elementos=[
            Elemento(tipo_indicado="TUERCAS", span=(0, 21)),
            Elemento(tipo_indicado="ARANDELAS", span=(24, 43)),
            Elemento(tipo_indicado="TORNILLO", span=(49, 72)),
        ],
        ambito_fila=[(72, 81)],
        conectores=[(21, 24), (43, 49)],
    )
    fila = FilaMTO(item=99, descripcion=texto, material_col="8.8", medida_col="M20",
                   cantidad=10, unidad="uds")
    puerto = PuertoFalso(respuestas={texto: seg})
    contador = {"n": 0}

    def siguiente_id():
        contador["n"] += 1
        return f"T{contador['n']}"

    lineas = _procesar_fila(fila, puerto, POLITICAS_POR_DEFECTO, TODAS_ACTIVAS, siguiente_id)
    assert len(lineas) == 3
    tuerca = next(l for l in lineas if l.nombre.valor == "TUERCA")
    tornillo = next(l for l in lineas if l.nombre.valor == "TORNILLO")

    # La calidad de la columna MATERIAL va al tornillo, no a la tuerca.
    assert tornillo.calidad.valor == "8.8"
    assert tornillo.calidad.procedencia is Procedencia.EXTRAIDO
    assert tuerca.calidad.procedencia is Procedencia.AUSENTE

    # El acabado del cierre de fila va EXTRAIDO al tornillo (principal) e
    # INFERIDO a la tuerca (accesorio), nunca al reves.
    assert tornillo.acabado.valor == "CINCADO"
    assert tornillo.acabado.procedencia is Procedencia.EXTRAIDO
    assert tuerca.acabado.valor == "CINCADO"
    assert tuerca.acabado.procedencia is Procedencia.INFERIDO


def test_indice_principal_con_una_sola_tuerca_no_cambia_filas_11_y_13():
    """Filas 11 y 13 del MTO solo describen una tuerca -- no hay ningun
    elemento de tipo principal (esparrago/tornillo/varilla roscada) en la
    fila. `_indice_principal` cae al primer elemento, que es exactamente
    el comportamiento de antes de este arreglo: no debe cambiar nada."""
    lineas = procesar_mto(RUTA, puerto_de_guion())
    fila11 = next(l for l in lineas if l.fila_origen == 11)
    fila13 = next(l for l in lineas if l.fila_origen == 13)

    assert fila11.nombre.valor == "TUERCA"
    assert fila11.calidad.valor == "A4-80"
    assert fila11.material.valor == "INOX"
    assert fila11.estado is Estado.RESUELTA

    assert fila13.nombre.valor == "TUERCA"
    assert fila13.calidad.valor == "8.8"
    assert fila13.acabado.valor == "CINCADO"
    assert fila13.material.valor == "AC"
    assert fila13.estado is Estado.RESUELTA


def test_la_columna_material_da_el_material_cuando_es_reconocible():
    """Fila 14, 'Arandela plana DIN 125 M10, acero, zincada': es la unica
    de las 15 filas donde la columna MATERIAL trae material en vez de
    calidad o norma ('acero' -> AC). La arandela sigue en revision por
    SIN_CALIDAD -- nunca tuvo calidad, ni propia ni de la columna -- pero
    el material ya no se pierde."""
    lineas = [l for l in procesar_mto(RUTA, puerto_de_guion()) if l.fila_origen == 14]
    assert len(lineas) == 1
    arandela = lineas[0]
    assert arandela.material.valor == "AC"
    assert arandela.material.procedencia is Procedencia.EXTRAIDO
    assert arandela.calidad.procedencia is Procedencia.AUSENTE
    assert arandela.estado is Estado.REVISION_MANUAL


def test_arandelas_astm_f436_reciben_material_por_la_norma():
    """Filas 1 y 5: la arandela es ASTM F436 y no trae calidad propia (ni
    GR ni nada marcado como calidad), asi que antes se quedaba sin
    material. F436 es la norma de arandela de acero templado y no existe
    una version inoxidable: la norma sola fija el material."""
    lineas = procesar_mto(RUTA, puerto_de_guion())
    for fila_origen in (1, 5):
        arandela = next(l for l in lineas
                        if l.fila_origen == fila_origen and l.nombre.valor == "ARANDELA")
        assert arandela.norma.valor == "ASTM F436"
        assert arandela.material.valor == "AC"
        assert arandela.material.procedencia is Procedencia.DERIVADO
        assert arandela.calidad.procedencia is Procedencia.AUSENTE


def test_por_defecto_todo_activo_sigue_dando_20_de_20_en_material():
    """No regresion del efecto conjunto de los tres arreglos: con las
    politicas por defecto, las 20 celdas de material evaluables (10 lineas
    sin calidad ni norma que la fije quedan AUSENTE y no cuentan aqui)
    quedan todas resueltas. Es lo que reporta `evaluacion.arnes` contra el
    gold: 20/20, subido desde 17/20."""
    lineas = procesar_mto(RUTA, puerto_de_guion())
    resueltos = [l for l in lineas if l.material.procedencia is not Procedencia.AUSENTE]
    assert len(resueltos) == 20
    assert all(l.material.valor is not None for l in resueltos)


# --------------------------------------------------------------------------
# El fallo de una fila no tumba el lote (ronda de correccion: corte de red a
# mitad de una tirada de 300 filas abortaba las ~199 ya procesadas).
# --------------------------------------------------------------------------

def _escribir_mto_de_prueba(ruta: Path, descripciones: list[str]) -> None:
    """xlsx minimo con el mismo layout que `motor.lectura_mto.leer_mto` espera:
    cabecera en las filas 1-4 (contenido irrelevante, `leer_mto` empieza en la 5)."""
    libro = openpyxl.Workbook()
    hoja = libro.active
    for _ in range(4):
        hoja.append([None] * 6)
    for item, descripcion in enumerate(descripciones, start=1):
        hoja.append([item, descripcion, "", "", 1, "uds"])
    libro.save(ruta)


class _PuertoQueFallaEnUnTexto:
    """Segmenta con normalidad salvo para `texto_que_falla`, donde lanza -- simula el
    corte de red real: el puerto agoto sus reintentos y `segmentar_con_votacion` deja
    escapar la excepcion sin controlar."""
    def __init__(self, respuestas: dict[str, Segmentacion], texto_que_falla: str):
        self.respuestas = respuestas
        self.texto_que_falla = texto_que_falla

    def segmentar(self, texto: str) -> Segmentacion:
        if texto == self.texto_que_falla:
            raise ConnectionError("corte de red simulado")
        return self.respuestas[texto]

    def extraer(self, tramo: str) -> list[dict]:
        return []


def test_una_fila_fallida_no_tumba_el_lote(tmp_path):
    """Puerto falso que revienta en la tercera fila de cinco: la tirada debe devolver
    lineas para las cinco filas -- la tercera en REVISION_MANUAL con motivo
    FALLO_DE_PROCESO, confianza 0 y sin trazas tecnicas en el texto -- y las otras cuatro
    procesadas con normalidad."""
    ruta = tmp_path / "mto_prueba.xlsx"
    descripciones = [
        "Tornillo hexagonal DIN 933 M10 x 40, 8.8, zincado",
        "Tuerca hexagonal DIN 934 M16, A4-80",
        'STUD BOLT 3/4" X 110 LG, ASTM A193, GR B7',
        "Tuerca autoblocante DIN 985 M12, 8.8, zincada",
        "Arandela plana DIN 125 M10, acero, zincada",
    ]
    _escribir_mto_de_prueba(ruta, descripciones)
    filas = leer_mto(ruta)
    assert len(filas) == 5
    texto_que_falla = filas[2].descripcion  # tercera fila (item 3)

    respuestas = {
        f.descripcion: Segmentacion(elementos=[
            Elemento(tipo_indicado="X", span=(0, len(f.descripcion)))])
        for f in filas if f.descripcion != texto_que_falla
    }
    puerto = _PuertoQueFallaEnUnTexto(respuestas, texto_que_falla)

    lineas = procesar_mto(ruta, puerto)

    assert sorted(set(l.fila_origen for l in lineas)) == [1, 2, 3, 4, 5]

    fila_rota = [l for l in lineas if l.fila_origen == 3]
    assert len(fila_rota) == 1
    assert fila_rota[0].estado is Estado.REVISION_MANUAL
    assert fila_rota[0].confianza == 0
    assert [m.codigo for m in fila_rota[0].motivos] == [CODIGO_FALLO_DE_PROCESO]
    texto_motivo = fila_rota[0].motivos[0].texto
    assert "ConnectionError" not in texto_motivo  # sin nombres de excepcion
    assert "Traceback" not in texto_motivo  # sin trazas tecnicas

    assert contar_fallos_de_proceso(lineas) == 1

    for item in (1, 2, 4, 5):
        lineas_fila = [l for l in lineas if l.fila_origen == item]
        assert len(lineas_fila) == 1
        assert CODIGO_FALLO_DE_PROCESO not in [m.codigo for m in lineas_fila[0].motivos]
        # se proceso de verdad: el nombre se resolvio por extraccion determinista,
        # independiente del "X" de guion que puso el puerto falso.
        assert lineas_fila[0].nombre.procedencia is Procedencia.EXTRAIDO


# --------------------------------------------------------------------------
# Bug real: el ambito de fila puede venir partido en varios tramos.
# --------------------------------------------------------------------------

def _fila_del_bug_de_ambito_partido(sufijo_ambito, ambito_fila):
    """Construye la fila 'BOLT DIN 931 M12x100 with 2 NUT DIN 980 and 2
    WASHER DIN 440' + `sufijo_ambito` (el cierre de fila, calidad '8.8' y
    acabado 'CINCADO'), con la Segmentacion ya armada con los tramos de
    elemento fijos y el `ambito_fila` que decide cada test -- 1, 2 o 3
    tramos sobre el mismo contenido. Caso real reportado sobre un blind
    set de 300 filas con el segmentador real (39/200 afectadas): el
    segmentador puede devolver el cierre partido, `ambito_fila: ['8.8',
    'CINCADO']`, y leer solo `ambito_fila[0]` perdia el acabado."""
    texto = "BOLT DIN 931 M12x100 with 2 NUT DIN 980 and 2 WASHER DIN 440" + sufijo_ambito
    seg = Segmentacion(
        elementos=[
            Elemento(tipo_indicado="BOLT", span=(0, 20)),
            Elemento(tipo_indicado="NUT", span=(26, 39)),
            Elemento(tipo_indicado="WASHER", span=(44, 60)),
        ],
        ambito_fila=ambito_fila,
        conectores=[(20, 26), (39, 44)],
    )
    fila = FilaMTO(item=98, descripcion=texto, material_col="", medida_col="M12",
                   cantidad=5, unidad="uds")
    return fila, PuertoFalso(respuestas={texto: seg})


def _procesar_una_fila_sintetica(fila, puerto, politicas=None):
    politicas = politicas if politicas is not None else POLITICAS_POR_DEFECTO
    contador = {"n": 0}

    def siguiente_id():
        contador["n"] += 1
        return f"B{contador['n']}"

    return _procesar_fila(fila, puerto, politicas, TODAS_ACTIVAS, siguiente_id)


def test_ambito_de_fila_en_dos_tramos_el_principal_recibe_los_dos():
    """Caso real del coordinador: ', 8.8' y ', CINCADO' llegan como dos
    tramos separados de `ambito_fila`. El tornillo (principal) tiene que
    recibir la calidad (del primer tramo) Y el acabado (del segundo) --
    antes del arreglo, el acabado se perdia por completo."""
    fila, puerto = _fila_del_bug_de_ambito_partido(
        ", 8.8, CINCADO", ambito_fila=[(60, 65), (65, 74)])
    lineas = _procesar_una_fila_sintetica(fila, puerto)
    tornillo = next(l for l in lineas if l.nombre.valor == "TORNILLO")
    assert tornillo.calidad.valor == "8.8"
    assert tornillo.calidad.procedencia is Procedencia.EXTRAIDO
    assert tornillo.acabado.valor == "CINCADO"
    assert tornillo.acabado.procedencia is Procedencia.EXTRAIDO
    assert tornillo.estado is Estado.RESUELTA


def test_ambito_de_fila_en_un_solo_tramo_da_el_mismo_resultado():
    """Mismo contenido exacto (', 8.8, CINCADO') pero como UN solo tramo de
    `ambito_fila` -- el caso de las 15 filas del MTO del cliente, con el
    segmentador de guion. El resultado tiene que ser identico al de dos
    tramos: el arreglo no puede cambiar el comportamiento de lo que ya
    funcionaba."""
    fila, puerto = _fila_del_bug_de_ambito_partido(
        ", 8.8, CINCADO", ambito_fila=[(60, 74)])
    lineas = _procesar_una_fila_sintetica(fila, puerto)
    tornillo = next(l for l in lineas if l.nombre.valor == "TORNILLO")
    assert tornillo.calidad.valor == "8.8"
    assert tornillo.calidad.procedencia is Procedencia.EXTRAIDO
    assert tornillo.acabado.valor == "CINCADO"
    assert tornillo.acabado.procedencia is Procedencia.EXTRAIDO
    assert tornillo.estado is Estado.RESUELTA


def test_ambito_de_fila_en_tres_tramos_con_acabado_en_el_ultimo():
    """Tres tramos: ', 8.8' (calidad), ', revisado' (nada reconocible) y
    ', CINCADO' (acabado, en el ULTIMO tramo). Tiene que encontrarse igual
    que si viniera en el primero o el segundo -- se recorren todos."""
    fila, puerto = _fila_del_bug_de_ambito_partido(
        ", 8.8, revisado, CINCADO", ambito_fila=[(60, 65), (65, 75), (75, 84)])
    lineas = _procesar_una_fila_sintetica(fila, puerto)
    tornillo = next(l for l in lineas if l.nombre.valor == "TORNILLO")
    assert tornillo.calidad.valor == "8.8"
    assert tornillo.acabado.valor == "CINCADO"
    assert tornillo.acabado.procedencia is Procedencia.EXTRAIDO
    assert tornillo.estado is Estado.RESUELTA


def test_ambito_partido_con_acabado_de_cierre_apagado_el_resto_sigue_sin_recibirlo():
    """Con `acabado_de_cierre_a_todo_el_set` en False, el tornillo (
    principal) sigue recibiendo calidad y acabado de los dos tramos del
    ambito -- eso no lo gobierna esta politica -- pero la tuerca y la
    arandela siguen sin acabado, igual que con un ambito de un tramo."""
    fila, puerto = _fila_del_bug_de_ambito_partido(
        ", 8.8, CINCADO", ambito_fila=[(60, 65), (65, 74)])
    politicas = {**POLITICAS_POR_DEFECTO, "acabado_de_cierre_a_todo_el_set": False}
    lineas = _procesar_una_fila_sintetica(fila, puerto, politicas)
    tornillo = next(l for l in lineas if l.nombre.valor == "TORNILLO")
    tuerca = next(l for l in lineas if l.nombre.valor == "TUERCA")
    arandela = next(l for l in lineas if l.nombre.valor == "ARANDELA")
    assert tornillo.acabado.valor == "CINCADO"
    assert tornillo.acabado.procedencia is Procedencia.EXTRAIDO
    assert tuerca.acabado.procedencia is Procedencia.AUSENTE
    assert arandela.acabado.procedencia is Procedencia.AUSENTE


# --------------------------------------------------------------------------
# Bug real: el ambito de fila puede contener la descripcion de una pieza
# que nunca se nombro (invariante nueva ambito_sin_dimensiones).
# --------------------------------------------------------------------------

def _fila_de_pieza_sin_nombrar():
    """Caso real reportado por el coordinador contra un blind set de 300
    filas: '3/4" IN DIA X 200MM LONG, FULLY THREADED, C/W 1 HEAVY HEXAGON
    NUTS ASTM A194 GR 2H'. El texto nunca nombra la pieza principal -- no
    dice 'stud', 'bolt' ni 'esparrago', solo sus dimensiones -- asi que el
    segmentador real mete esa descripcion en el ambito de fila en vez de
    crear un elemento. Cobertura=1.0 (todo el texto esta asignado a algo)
    y recuento de sustantivos=1=elementos (de verdad solo hay un
    sustantivo, NUTS): ninguna otra invariante lo caza."""
    texto = ('3/4" IN DIA X 200MM LONG, FULLY THREADED, C/W 1 HEAVY HEXAGON '
             'NUTS ASTM A194 GR 2H')
    seg = Segmentacion(
        elementos=[Elemento(tipo_indicado="NUTS", span=(46, 82))],
        ambito_fila=[(0, 40)],
        conectores=[(40, 46)],
    )
    fila = FilaMTO(item=97, descripcion=texto, material_col="", medida_col="",
                   cantidad=1, unidad="uds")
    return fila, PuertoFalso(respuestas={texto: seg})


def test_pieza_sin_nombrar_manda_la_fila_a_revision():
    """La fila entera tiene que ir a REVISION_MANUAL con motivo
    PIEZA_SIN_NOMBRAR, sin inventar el esparrago que falta: la linea sale
    vacia (nombre AUSENTE), no como una TUERCA resuelta con sus propios
    datos -- que es exactamente el escape que describio el coordinador."""
    fila, puerto = _fila_de_pieza_sin_nombrar()
    lineas = _procesar_una_fila_sintetica(fila, puerto)
    assert len(lineas) == 1
    linea = lineas[0]
    assert linea.estado is Estado.REVISION_MANUAL
    assert linea.confianza == 0
    assert [m.codigo for m in linea.motivos] == ["PIEZA_SIN_NOMBRAR"]
    assert linea.nombre.procedencia is Procedencia.AUSENTE


def test_pieza_sin_nombrar_con_interruptor_apagado_no_dispara():
    """Misma fila, con `dimensiones_en_ambito_a_revision` en False: vuelve
    el comportamiento de antes del arreglo -- la tuerca sale RESUELTA con
    sus propios datos (nombre, norma y calidad estan en su propio tramo) y
    la pieza sin nombrar se pierde en silencio. Reproduce a proposito el
    escape que describio el coordinador, para probar que el interruptor
    es lo que lo gobierna."""
    fila, puerto = _fila_de_pieza_sin_nombrar()
    politicas = {**POLITICAS_POR_DEFECTO, "dimensiones_en_ambito_a_revision": False}
    lineas = _procesar_una_fila_sintetica(fila, puerto, politicas)
    assert len(lineas) == 1
    linea = lineas[0]
    assert linea.nombre.valor == "TUERCA"
    assert linea.calidad.valor == "GR 2H"
    assert linea.estado is Estado.RESUELTA
