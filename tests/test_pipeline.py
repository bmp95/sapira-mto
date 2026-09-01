from pathlib import Path

from datos.guion_falso import puerto_de_guion
from motor.modelos import Estado, Procedencia
from motor.pipeline import POLITICAS_POR_DEFECTO, _calidad_de_columna_material, procesar_mto

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
