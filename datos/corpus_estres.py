"""Corpus de estres: lo que el MTO de muestra NUNCA contiene.

La pregunta que responde no es "acierta?" sino "FALLA DEL LADO SEGURO?".
Un valor inventado con aspecto de bueno cuesta 50.000 euros; un hueco cuesta 1 euro.

Cada caso trae lo que se espera del sistema, no la respuesta correcta:
  OK     -> deberia resolverlo bien
  HUECO  -> deberia dejarlo vacio o mandarlo a revision, nunca inventar
"""

# (categoria, texto, que se espera)
CASOS = [
    # --- 1. catalogo real que el MTO nunca ejercita -------------------------
    ("catalogo sin usar", "Arandela plana DIN 125 M10, 200HV, zincada", "OK"),
    ("catalogo sin usar", "Arandela DIN 9021 M12, 140HV", "OK"),
    ("catalogo sin usar", "HEX BOLT 1/2\" x 2\", GRADE 5, ZP", "OK"),
    ("catalogo sin usar", "HEX BOLT M16 x 60, GRADE 8, HDG", "OK"),
    ("catalogo sin usar", "Tornillo DIN 933 M12 x 40, 10.9, pavonado", "OK"),
    ("catalogo sin usar", "Tornillo DIN 7991 M8 x 30, A2-80", "OK"),
    ("catalogo sin usar", "Tuerca DIN 6923 M10, 8, bicromatada", "OK"),
    ("catalogo sin usar", "Tornillo DIN 963 M6 x 20, 304, dacromet", "OK"),
    ("catalogo sin usar", "Tuerca DIN 985 M16, 316, fosfatada", "OK"),
    ("catalogo sin usar", "VARILLA ROSCADA M12 x 1000, DIN 975, 8.8", "OK"),
    ("catalogo sin usar", "THREADED ROD 3/4\" x 3000, ASTM A193 GR B7", "OK"),
    ("catalogo sin usar", "Tornillo DIN 84 M5 x 25, A4-70", "OK"),
    ("catalogo sin usar", "Tornillo DIN 7981 C-H 4.8 x 25, cincado", "OK"),

    # --- 2. formatos de norma que las reglas nombran y el MTO no usa --------
    ("formato ausente", "HEX BOLT ASME B18.2.1 3/4\" x 4\", GRADE 5", "OK"),
    ("formato ausente", "Soporte MSS SP-58 M12, 8.8, galvanizado en caliente", "OK"),
    ("formato ausente", "Tuerca DIN EN 1661 M10, 10, cincada", "OK"),
    ("formato ausente", "Tornillo ISO 4017 M10 x 30, 8.8", "OK"),

    # --- 3. valores REALES pero fuera del catalogo cerrado ------------------
    ("real fuera de catalogo", "Tornillo DIN 933 M10 x 40, 5.6, cincado", "HUECO"),
    ("real fuera de catalogo", "Tornillo DIN 933 M10 x 40, 5.8", "HUECO"),
    ("real fuera de catalogo", "Tornillo DIN 933 M8 x 20, laton", "HUECO"),
    ("real fuera de catalogo", "Tuerca DIN 934 M8, aluminio", "HUECO"),
    ("real fuera de catalogo", "Arandela DIN 125 M8, nylon", "HUECO"),
    ("real fuera de catalogo", "Tornillo DIN 912 M10 x 40, 12.9, anodizado", "HUECO"),
    ("real fuera de catalogo", "Tornillo DIN 933 M10 x 40, 8.8, xilan", "HUECO"),

    # --- 4. inventado: no existe en ninguna parte ---------------------------
    ("inventado", "Tornillo DIN 99999 M10 x 40, 8.8", "HUECO"),
    ("inventado", "Tuerca ISO 12345 M10, A4-70", "HUECO"),
    ("inventado", "Tornillo DIN 933 M10 x 40, A6-90", "HUECO"),
    ("inventado", "Tornillo DIN 933 M10 x 40, 14.9", "HUECO"),
    ("inventado", "Tornillo DIN 933 M10 x 40, 8.8, plastificado en frio", "HUECO"),
    ("inventado", "Flanborte hexagonal DIN 933 M10 x 40, 8.8", "HUECO"),
    ("inventado", "Zurrapa roscada M10 x 40, 8.8, cincada", "HUECO"),

    # --- 5. formatos raros de medida y longitud ----------------------------
    ("formato raro", "HEX BOLT 1-1/4\" x 6\", ASTM A193 GR B7", "OK"),
    ("formato raro", "Tornillo DIN 933 M20x1.5 x 60, 8.8", "OK"),
    ("formato raro", "Tornillo DIN 933 M10 x 40 mm, 8.8, cincado", "OK"),
    ("formato raro", "STUD BOLT 5/8\" X 4-1/2\" LG, ASTM A193, GR B7", "OK"),

    # --- 6. suciedad tipografica -------------------------------------------
    ("suciedad", "STUD BOLT 7/8″ X 130 LG, ASTM A193, GR B7", "OK"),
    ("suciedad", "Tornillo “DIN 933” M10 x 40, 8.8", "OK"),
    ("suciedad", "Tornillo DIN 933 Ø10 x 40, 8.8", "OK"),
    ("suciedad", "Tornillo    DIN   933   M10  x  40,  8.8", "OK"),
    ("suciedad", "TORNILLO DIN933 M10X40 8.8 ZINCADO", "OK"),

    # --- 7. estructura rara del set ----------------------------------------
    ("estructura", "BOLT DIN 931 M16x80 with 2 NUT DIN 934 and 4 WASHER DIN 125, 8.8, ZN", "OK"),
    ("estructura", "DIN 934 M20 tuerca, A4-80", "OK"),
    ("estructura", "2 x DIN 125 M10 arandela, 200HV", "OK"),
    ("estructura", "M10 x 40 DIN 933 8.8 cincado tornillo hexagonal", "OK"),
    ("estructura", "Kit: 1 esparrago M20x200 DIN 975 + 2 tuercas DIN 934 + 2 arandelas DIN 125", "OK"),

    # --- 8. otros idiomas ---------------------------------------------------
    ("idioma", "Parafuso sextavado DIN 933 M10 x 40, 8.8, zincado", "OK"),
    ("idioma", "Vite esagonale DIN 933 M10 x 40, 8.8", "OK"),
    ("idioma", "Vis a tete hexagonale DIN 933 M10 x 40, 8.8", "OK"),
    ("idioma", "Sechskantschraube DIN 933 M10 x 40, 8.8", "OK"),

    # --- 9. degenerados -----------------------------------------------------
    ("degenerado", "", "HUECO"),
    ("degenerado", "-", "HUECO"),
    ("degenerado", "40", "HUECO"),
    ("degenerado", "ver plano 3421-B", "HUECO"),
    ("degenerado", "MATERIAL SEGUN ESPECIFICACION TECNICA", "HUECO"),
    ("degenerado", "8.8", "HUECO"),
]
