"""Genera un blind set de 300 filas para probar el sistema contra lo que no ha visto.

DOS BLOQUES:

  A) ~200 filas COMPUESTAS a partir de piezas reales del catalogo, en combinaciones y
     estilos de escritura que el MTO de muestra nunca usa. Como las compone este script,
     la verdad se conoce por construccion: cada fila lleva su gold. Aqui se mide ACIERTO.

  B) ~100 filas ADVERSARIAS: normas inventadas, calidades que no existen, nombres de
     pieza inventados, materiales imposibles, contradicciones deliberadas, suciedad
     tipografica, idiomas y estructuras degeneradas. Aqui no se mide acierto: se mide
     que el sistema FALLE DEL LADO SEGURO y no invente ningun valor que no este escrito.

Los estilos de escritura salen de formatos reales de proveedor de tornilleria de tuberia:
  "5/8 x 90 mm LONG ASTM A193-B7 W/2 HH NUTS ASTM A194-2H"
  "2.1/2 IN DIA X 470MM LONG, FULLY THREADED, C/W 2 HEAVY HEXAGON NUTS"
"""
import random
import openpyxl

random.seed(20260901)  # reproducible: el blind set es el mismo en cada ejecucion

# --------------------------------------------------------------------------
# Piezas reales del catalogo del cliente
# --------------------------------------------------------------------------
NORMAS_TORNILLO = [("DIN 931", "ISO 4014"), ("DIN 933", "ISO 4017"), ("DIN 912", "ISO 4762"),
                   ("DIN 7991", "ISO 10642"), ("DIN 963", "ISO 2009"), ("DIN 7985", "ISO 7045"),
                   ("DIN 84", "ISO 1207"), ("DIN 603", "ISO 8677"), ("DIN 965", "ISO 7046")]
NORMAS_TUERCA = [("DIN 934", "ISO 4032"), ("DIN 985", "ISO 10511"), ("DIN 980", "ISO 7042"),
                 ("DIN 936", "ISO 4035"), ("DIN 6923", "EN 1661"), ("DIN 935", "ISO 7035")]
NORMAS_ARANDELA = [("DIN 125", "ISO 7089"), ("DIN 9021", "ISO 7093"), ("DIN 440", "ISO 7094")]

CAL_ACERO = ["8.8", "10.9", "12.9", "GRADE 5", "GRADE 8"]
CAL_INOX = ["A2", "A2-70", "A2-80", "A4", "A4-70", "A4-80", "304", "316", "18-8"]
CAL_TUERCA = ["8", "10"]
CAL_ARANDELA = ["100HV", "140HV", "160HV", "200HV", "300HV"]

ACABADOS = [("cincado", "CINCADO"), ("zincado", "CINCADO"), ("ZN", "CINCADO"),
            ("zinc plated", "CINCADO"), ("galvanizado en caliente", "GALVANIZADO EN CALIENTE"),
            ("HDG", "GALVANIZADO EN CALIENTE"), ("hot dip galvanized", "GALVANIZADO EN CALIENTE"),
            ("pavonado", "PAVONADO"), ("negro", "PAVONADO"), ("fosfatado", "FOSFATADO"),
            ("phosphated", "FOSFATADO"), ("bicromatado", "BICROMATADO"), ("YZP", "BICROMATADO"),
            ("geomet", "GEOMET"), ("dacromet", "DACROMET")]

METRICAS = ["M6", "M8", "M10", "M12", "M14", "M16", "M20", "M24", "M27", "M30"]
PULGADAS = ['1/2"', '5/8"', '3/4"', '7/8"', '1"', '1-1/4"', '1-1/2"']
LARGOS = [20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 150, 180, 200, 250]

filas = []   # (descripcion, material_col, medida_col, cantidad, bloque, gold)


def _g(**kw):
    """Gold de una linea: solo los atributos que la fila fija de verdad."""
    base = dict(nombre=None, material=None, calidad=None, medida=None,
                longitud=None, norma=None, acabado=None)
    base.update(kw)
    return base


# --------------------------------------------------------------------------
# BLOQUE A - filas compuestas, verdad conocida
# --------------------------------------------------------------------------

def bloque_a():
    out = []

    # A1 - tornillo suelto, seis estilos de escritura distintos
    for _ in range(60):
        din, iso = random.choice(NORMAS_TORNILLO)
        med = random.choice(METRICAS)
        lar = random.choice(LARGOS)
        inox = random.random() < 0.35
        cal = random.choice(CAL_INOX if inox else CAL_ACERO)
        aca = random.choice(ACABADOS) if (not inox and random.random() < 0.6) else None
        acat = f", {aca[0]}" if aca else ""
        estilo = random.randrange(6)
        if estilo == 0:
            t = f"Tornillo hexagonal {din} {med} x {lar}, {cal}{acat}"
        elif estilo == 1:
            t = f"HEX BOLT {din} {med}x{lar} {cal}{acat.upper()}"
        elif estilo == 2:
            t = f"{med} x {lar} {din} {cal} tornillo{acat}"
        elif estilo == 3:
            t = f"Tornillo {din} {med} x {lar} mm, {cal}{acat}"
        elif estilo == 4:
            t = f"SCREW {iso} {med}x{lar}, {cal}{acat.upper()}"
        else:
            t = f"TORNILLO {din.replace(' ', '')} {med}X{lar} {cal}{acat.upper()}"
        out.append((t, cal, f"{med}x{lar}", random.randrange(10, 900),
                    _g(nombre="TORNILLO", material="INOX" if inox else "AC", calidad=cal,
                       medida=med, longitud=f"{lar} mm", norma=iso,
                       acabado=aca[1] if aca else "")))

    # A2 - tuerca suelta
    for _ in range(35):
        din, iso = random.choice(NORMAS_TUERCA)
        med = random.choice(METRICAS)
        inox = random.random() < 0.4
        cal = random.choice(CAL_INOX if inox else (CAL_ACERO + CAL_TUERCA))
        aca = random.choice(ACABADOS) if (not inox and random.random() < 0.5) else None
        acat = f", {aca[0]}" if aca else ""
        t = random.choice([
            f"Tuerca hexagonal {din} {med}, {cal}{acat}",
            f"HEX NUT {din} {med}, {cal}{acat.upper()}",
            f"Tuerca autoblocante {din} {med}, {cal}{acat}",
            f"NUT {iso} {med} {cal}{acat.upper()}"])
        out.append((t, cal, med, random.randrange(20, 2000),
                    _g(nombre="TUERCA", material="INOX" if inox else "AC", calidad=cal,
                       medida=med, longitud="N/A", norma=iso,
                       acabado=aca[1] if aca else "")))

    # A3 - arandela suelta, con las clases HV que el MTO nunca usa
    for _ in range(25):
        din, iso = random.choice(NORMAS_ARANDELA)
        med = random.choice(METRICAS)
        inox = random.random() < 0.3
        cal = random.choice(CAL_INOX if inox else CAL_ARANDELA)
        aca = random.choice(ACABADOS) if (not inox and random.random() < 0.5) else None
        acat = f", {aca[0]}" if aca else ""
        t = random.choice([
            f"Arandela plana {din} {med}, {cal}{acat}",
            f"WASHER {din} {med} {cal}{acat.upper()}",
            f"Arandela {din} {med}, {cal}{acat}"])
        out.append((t, cal, med, random.randrange(50, 3000),
                    _g(nombre="ARANDELA", material="INOX" if inox else "AC", calidad=cal,
                       medida=med, longitud="N/A", norma=iso,
                       acabado=aca[1] if aca else "")))

    # A4 - esparragos ASTM en formato REAL de proveedor de tuberia
    for _ in range(40):
        pul = random.choice(PULGADAS)
        lar = random.choice([60, 90, 110, 130, 150, 180, 200, 250, 470])
        n = random.choice([1, 2])
        estilo = random.randrange(5)
        if estilo == 0:
            t = f'STUD BOLT {pul} X {lar} LG, ASTM A193, GR B7 W/{n} HEX. NUT {pul}, ASTM A194, GR 2H'
        elif estilo == 1:
            t = f'{pul} x {lar} mm LONG ASTM A193-B7 W/{n} HH NUTS ASTM A194-2H'
        elif estilo == 2:
            t = f'{pul} IN DIA X {lar}MM LONG, FULLY THREADED, C/W {n} HEAVY HEXAGON NUTS ASTM A194 GR 2H'
        elif estilo == 3:
            t = f'Esparrago {pul} x {lar}, ASTM A193 GR B7, con {n} tuercas ASTM A194 GR 2H'
        else:
            t = f'STUD BOLT ASTM A193 GR B7 {pul} X {lar} LG'
        gold_p = _g(nombre="ESPARRAGO", material="AC", calidad="GR B7", medida=pul,
                    longitud=f"{lar} mm", norma="ASTM A193", acabado="")
        out.append((t, "ASTM A193 GR B7", f"{pul} X {lar}", random.randrange(10, 400), gold_p))

    # A5 - sets metricos completos
    for _ in range(40):
        dt, it = random.choice(NORMAS_TORNILLO)
        dn, inn = random.choice(NORMAS_TUERCA)
        da, ia = random.choice(NORMAS_ARANDELA)
        med = random.choice(METRICAS)
        lar = random.choice(LARGOS)
        cal = random.choice(CAL_ACERO)
        aca = random.choice(ACABADOS)
        n = random.choice([1, 2])
        t = random.choice([
            f"Tornillo {dt} {med} x {lar} con {n} tuercas {dn} y {n} arandelas {da}, {cal}, {aca[0]}",
            f"BOLT {dt} {med}x{lar} with {n} NUT {dn} and {n} WASHER {da}, {cal}, {aca[0].upper()}",
            f"Conjunto {med} x {lar}: tornillo {dt} + {n} tuerca {dn} + {n} arandela {da}, {cal}, {aca[0]}"])
        out.append((t, cal, f"{med}x{lar}", random.randrange(10, 500),
                    _g(nombre="TORNILLO", material="AC", calidad=cal, medida=med,
                       longitud=f"{lar} mm", norma=it, acabado=aca[1])))
    return out


# --------------------------------------------------------------------------
# BLOQUE B - adversarias. Aqui solo se mide que no invente.
# --------------------------------------------------------------------------

def bloque_b():
    out = []
    A = lambda t, m="", md="", c=1: out.append((t, m, md, c, None))

    # normas que no existen
    for n in ("DIN 99999", "DIN 12345", "ISO 99999", "ASTM Z999", "MSS SP-999", "EN 000000"):
        A(f"Tornillo {n} M10 x 40, 8.8, cincado", "8.8", "M10x40", 100)
    # calidades que no existen
    for c in ("A6-90", "14.9", "B99", "GRADE 99", "999HV", "A9-70", "22.2"):
        A(f"Tornillo DIN 933 M10 x 40, {c}", c, "M10x40", 100)
    # acabados que no existen
    for a in ("plastificado en frio", "xilan 1070", "anodizado duro", "recubrimiento lunar",
              "PTFE coated", "teflonado", "esmaltado al fuego"):
        A(f"Tornillo DIN 933 M10 x 40, 8.8, {a}", "8.8", "M10x40", 100)
    # nombres de pieza inventados
    for p in ("Flanborte hexagonal", "Zurrapa roscada", "Perno cuantico", "Tirafondo estelar",
              "Grapon de sujecion", "Clavija hexalobular", "Remachuelo pasante"):
        A(f"{p} DIN 933 M10 x 40, 8.8", "8.8", "M10x40", 100)
    # materiales imposibles o fuera de catalogo
    for m in ("aluminio", "laton", "bronce", "titanio", "nylon", "policarbonato", "madera"):
        A(f"Tornillo DIN 933 M10 x 40, {m}", m, "M10x40", 100)
    # contradicciones deliberadas
    A("Tuerca DIN 934 M16, 8.8, ISO 4017", "8.8", "M16", 50)          # tuerca con norma de tornillo
    A("Arandela DIN 125 M10, ISO 4032, 200HV", "200HV", "M10", 50)     # arandela con norma de tuerca
    A("Tornillo DIN 933 M10 x 40, A4-70, galvanizado en caliente", "A4-70", "M10x40", 50)  # inox galvanizado
    A("Tornillo DIN 933 M10 x 40, aluminio, 8.8", "aluminio", "M10x40", 50)  # material contra calidad
    A("Arandela ASTM F436 M10, INOX", "INOX", "M10", 50)               # material contra norma
    A("Tuerca DIN 934 M16, 200HV", "200HV", "M16", 50)                 # HV en tuerca
    A("Tornillo DIN 933 M10 x 40, 10", "10", "M10x40", 50)             # calidad de tuerca en tornillo
    A("Tornillo DIN 933 M20 x 5, 8.8", "8.8", "M20x5", 50)             # mas corto que su diametro
    A("Tuerca DIN 934 M16 x 60, 8", "8", "M16x60", 50)                 # tuerca con longitud
    A("Esparrago M20 x 200 DIN 975 y varilla roscada M20 DIN 975", "8.8", "M20x200", 50)
    # suciedad tipografica y formatos raros
    A('STUD BOLT 7/8″ X 130 LG, ASTM A193, GR B7', "ASTM A193 GR B7", '7/8" X 130', 40)
    A('Tornillo “DIN 933” M10 x 40, 8.8', "8.8", "M10x40", 40)
    A("Tornillo DIN 933 Ø10 x 40, 8.8", "8.8", "M10x40", 40)
    A("Tornillo    DIN   933    M10   x   40,   8.8", "8.8", "M10x40", 40)
    A("TORNILLO DIN933 M10X40 8.8 ZINCADO", "8.8", "M10x40", 40)
    A("2.1/2 IN DIA X 470MM LONG, FULLY THREADED, C/W 2 HEAVY HEXAGON NUTS", "", '2.1/2"', 20)
    A("Tornillo DIN 933 M20x1.5 x 60, 8.8", "8.8", "M20x1.5x60", 40)
    A("HEX BOLT 1-1/4\" x 6\", ASTM A193 GR B7", "ASTM A193 GR B7", '1-1/4"', 20)
    A("Tornillo DIN 7981 C-H 4.8 x 25, cincado", "", "4.8x25", 40)
    A("Soporte MSS SP-58 M12, 8.8, HDG", "8.8", "M12", 30)
    A("Tuerca DIN EN 1661 M10, 10, cincada", "10", "M10", 30)
    # otros idiomas
    for t in ("Parafuso sextavado DIN 933 M10 x 40, 8.8, zincado",
              "Vite esagonale DIN 933 M10 x 40, 8.8",
              "Vis a tete hexagonale DIN 933 M10 x 40, 8.8",
              "Sechskantschraube DIN 933 M10 x 40, 8.8",
              "Bout zeskant DIN 933 M10 x 40, 8.8",
              "Sruba szesciokatna DIN 933 M10 x 40, 8.8"):
        A(t, "8.8", "M10x40", 60)
    # estructuras raras y degenerados
    A("2 TUERCAS DIN 934 M20 y 2 ARANDELAS DIN 125 para TORNILLO DIN 931 M20x90, 8.8", "8.8", "M20x90", 80)
    A("BOLT DIN 931 M16x80 with 2 NUT DIN 934 and 4 WASHER DIN 125, 8.8, ZN", "8.8", "M16x80", 80)
    A("Kit: 1 esparrago M20x200 DIN 975 + 2 tuercas DIN 934 + 2 arandelas DIN 125", "8.8", "M20x200", 30)
    A("Tornillo DIN 933 M10 x 40 y tornillo DIN 931 M12 x 50, 8.8", "8.8", "M10x40", 60)
    for t in ("", "-", "40", "ver plano 3421-B", "MATERIAL SEGUN ESPECIFICACION TECNICA",
              "8.8", "SIN DEFINIR", "N/A", "???", "TBD por ingenieria"):
        A(t, "", "", 10)
    # formatos reales de proveedor de tuberia, sin equivalente en el MTO de muestra
    A('3/4" x 4.1/2" LG STUD BOLT A193-B7 C/W 2 HEX NUTS A194-2H, HDG TO ASTM F2329', "A193-B7", '3/4"', 60)
    A('1.1/8 IN X 6.1/2 IN LG THREADED ROD ASTM A193 GR B7 W/4 NUTS', "ASTM A193 GR B7", '1.1/8"', 25)
    A('M20 X 90 LG HEX HD BOLT GR 8.8 HDG TO ASTM A153', "8.8", "M20x90", 120)
    A('BOLT, HEX HD, 3/4"-10UNC X 3.1/2" LG, ASTM A193 B7', "ASTM A193 B7", '3/4"', 45)
    A('STUD, THREADED, 5/8" DIA X 130MM, A193-B7, PTFE COATED BLUE', "A193-B7", '5/8"', 30)
    A('SCREW HEX HD M12X1.75 X 45MM CL 8.8 ZP', "8.8", "M12x45", 200)
    A('WASHER, PLAIN, M10, ASTM F436 TYPE 1, HDG', "ASTM F436", "M10", 400)
    A('NUT, HEAVY HEX, 7/8"-9UNC, ASTM A194 GR 2H, HDG', "ASTM A194 GR 2H", '7/8"', 160)
    # abreviaturas y jerga de obra
    A("Torn. hex. DIN 933 M10x40 8.8 zinc.", "8.8", "M10x40", 300)
    A("TUERC. HEX. DIN 934 M10 CL.8 GALV.", "8", "M10", 300)
    A("Ar. plana DIN125 M10 zinc", "", "M10", 500)
    A("T/H DIN 933 M8x30 A2", "A2", "M8x30", 250)
    # cantidades y unidades raras
    A("Tornillo DIN 933 M10 x 40, 8.8, cincado (caja de 100)", "8.8", "M10x40", 12)
    A("Tornillo DIN 933 M10 x 40, 8.8 - 25 kg", "8.8", "M10x40", 25)
    A("Varilla roscada DIN 975 M12 x 1000 mm, 8.8, barras de 1 m", "8.8", "M12x1000", 40)
    # contradicciones adicionales
    A("Tornillo DIN 933 M10 x 40, INOX, 8.8, cincado", "INOX", "M10x40", 50)
    A("Arandela DIN 125 M10, GRADE 8", "GRADE 8", "M10", 50)
    A("Esparrago DIN 934 M20 x 200, GR B7", "GR B7", "M20x200", 50)
    A("Tornillo ASTM A193 M20 x 90, 8.8", "8.8", "M20x90", 50)
    A("Tuerca DIN 934 7/8\", A4-80", "A4-80", '7/8"', 50)
    A("Tornillo DIN 933 M10 x 40, A2-70, 8.8", "A2-70", "M10x40", 50)
    # texto que no describe tornilleria
    A("Junta espirometalica 4\" 300# grafito", "", '4"', 20)
    A("Valvula de bola 2\" clase 150 acero al carbono", "", '2"', 5)
    A("Codo 90 grados 6\" SCH 40 ASTM A234 WPB", "", '6"', 10)
    A("Brida WN 8\" 150# ASTM A105 RF SCH 40", "", '8"', 8)
    return out


def generar(ruta_mto="datos/blind_set.xlsx", ruta_gold="datos/blind_set_gold.xlsx"):
    a, b = bloque_a(), bloque_b()
    todo = [(t, m, md, c, "A", g) for t, m, md, c, g in a] + \
           [(t, m, md, c, "B", g) for t, m, md, c, g in b]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "MTO"
    ws.append(["BLIND SET GENERADO - 300 filas"])
    ws.append([])
    ws.append([])
    ws.append(["ITEM", "DESCRIPCION", "MATERIAL", "MEDIDA", "CANT.", "UD"])
    for i, (t, m, md, c, _, _) in enumerate(todo, start=1):
        ws.append([i, t, m, md, c, "uds"])
    ws.column_dimensions["B"].width = 90
    wb.save(ruta_mto)

    wg = openpyxl.Workbook()
    g = wg.active
    g.title = "gold"
    g.append(["item", "bloque", "descripcion", "nombre", "material", "calidad",
              "medida", "longitud", "norma", "acabado"])
    for i, (t, _, _, _, bloque, gold) in enumerate(todo, start=1):
        if gold is None:
            g.append([i, bloque, t, "", "", "", "", "", "", ""])
        else:
            g.append([i, bloque, t, gold["nombre"], gold["material"], gold["calidad"],
                      gold["medida"], gold["longitud"], gold["norma"], gold["acabado"]])
    g.column_dimensions["C"].width = 90
    wg.save(ruta_gold)
    return len(a), len(b), len(todo)


if __name__ == "__main__":
    na, nb, n = generar()
    print(f"bloque A (verdad conocida): {na} filas")
    print(f"bloque B (adversarias):     {nb} filas")
    print(f"TOTAL:                      {n} filas")
