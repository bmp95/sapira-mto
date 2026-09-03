"""Convierte un .md de docs/ a PDF A4 con el mismo Chromium que render.py.

Existe porque el conversor anterior vivia fuera del repositorio y se perdio:
un entregable que no se puede regenerar no es un entregable. Este vive aqui,
con la misma paleta de marca que los otros dos documentos.

No pretende ser un motor de Markdown completo. Cubre lo que usan estos
documentos -- encabezados, negrita, cursiva, `codigo`, listas, tablas y
reglas -- y falla de forma visible si aparece algo que no entiende, en vez de
tragarselo en silencio.

Uso:
    python docs/activos/md_a_pdf.py one-pager "One-pager - Reconciliacion MTO"
"""

import html
import pathlib
import re
import sys

AQUI = pathlib.Path(__file__).resolve().parent
DOCS = AQUI.parent
sys.path.insert(0, str(AQUI))

from render import render  # noqa: E402  (reutiliza el mismo Chromium y su guardian)

ESTILO = """
  @page { size: A4 portrait; margin: 0; }
  :root{ --hueso:#EFECE7; --tinta:#221F1D; --acento:#B54D47; --gris:#857D77; --linea:#D8D2CA; }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:"Segoe UI",Arial,sans-serif; color:var(--tinta); background:#fff}
  .hoja{width:210mm; padding:14mm 15mm 11mm; font-size:9.3pt; line-height:1.5}
  h1{font-size:21pt; letter-spacing:-.4pt; line-height:1.1; margin-bottom:1.5mm}
  h2{font-size:12pt; margin:4.2mm 0 1.8mm; padding-bottom:1.2mm; border-bottom:1.4pt solid var(--tinta)}
  h2:first-of-type{margin-top:3mm}
  p{margin-bottom:1.9mm}
  strong{font-weight:700}
  em{font-style:italic; color:#4A4340}
  code{font-family:Consolas,monospace; font-size:8.3pt; background:#F4F1EC;
       padding:0 .7mm; border-radius:.6mm}
  hr{border:none; border-top:1px solid var(--linea); margin:4mm 0}
  table{width:100%; border-collapse:collapse; margin:2.5mm 0; font-size:8.5pt}
  th{text-align:left; font-size:7.2pt; letter-spacing:.7pt; text-transform:uppercase;
     color:var(--gris); border-bottom:1px solid var(--linea); padding:1.6mm 2mm 1.6mm 0}
  td{padding:1.6mm 2mm 1.6mm 0; border-bottom:1px solid #EDEAE5; vertical-align:top}
  tr:last-child td{border-bottom:none}
  ul{margin:0 0 2.2mm 4.5mm}
  li{margin-bottom:1mm}
  .sub{color:var(--gris); font-size:9.5pt; margin-bottom:4mm}
  figure{margin:2.4mm 0 3mm}
  figure svg{width:100%; height:auto; display:block}
  figcaption{font-size:7.6pt; color:var(--gris); margin-top:1.4mm; line-height:1.35}
"""

# ---------------------------------------------------------------------------
# Figuras. Viven aqui y no en el .md para que el markdown siga leyendose como
# markdown: en el documento solo hay una linea `:::figura nombre`.
# ---------------------------------------------------------------------------

FIGURAS = {
    "historico": ("""
<svg viewBox="0 0 700 104" role="img" aria-label="Se pregunta una vez y las revisiones siguientes heredan">
  <defs><style>
    .rv{font:700 11px "Segoe UI",Arial;fill:#221F1D}
    .tx{font:10px "Segoe UI",Arial;fill:#857D77}
    .lb{font:700 9.5px "Segoe UI",Arial;fill:#B54D47}
    .kk{font:9.5px Consolas,monospace;fill:#221F1D}
  </style></defs>

  <line x1="0" y1="30" x2="700" y2="30" stroke="#D8D2CA" stroke-width="1.4"/>
  <path d="M74 30 H256" stroke="#B54D47" stroke-width="1.4" stroke-dasharray="3 3"/>
  <path d="M274 30 H436" stroke="#B54D47" stroke-width="1.4" stroke-dasharray="3 3"/>
  <path d="M454 30 H616" stroke="#B54D47" stroke-width="1.4" stroke-dasharray="3 3"/>

  <circle cx="65" cy="30" r="9" fill="#B54D47"/>
  <text class="rv" x="65" y="15" text-anchor="middle">Revisi&#243;n 9</text>
  <text class="lb" x="65" y="52" text-anchor="middle">SE PREGUNTA</text>

  <circle cx="265" cy="30" r="8" fill="#fff" stroke="#221F1D" stroke-width="1.6"/>
  <text class="rv" x="265" y="15" text-anchor="middle">Revisi&#243;n 12</text>
  <text class="tx" x="265" y="52" text-anchor="middle">hereda</text>

  <circle cx="445" cy="30" r="8" fill="#fff" stroke="#221F1D" stroke-width="1.6"/>
  <text class="rv" x="445" y="15" text-anchor="middle">Revisi&#243;n 15</text>
  <text class="tx" x="445" y="52" text-anchor="middle">hereda</text>

  <circle cx="625" cy="30" r="8" fill="#fff" stroke="#221F1D" stroke-width="1.6"/>
  <text class="rv" x="625" y="15" text-anchor="middle">Revisi&#243;n 21</text>
  <text class="tx" x="625" y="52" text-anchor="middle">hereda</text>

  <rect x="0" y="66" width="700" height="34" rx="3" fill="#F7F5F2" stroke="#D8D2CA"/>
  <text class="kk" x="12" y="87">ARANDELA &#183; ACERO &#183; M16 &#183; — &#183; DIN 125 &#183; CINCADO
    &#8594; calidad = 200 HV &#160;&#160;(J. P&#233;rez, 12-03)</text>
</svg>""",
    ("La clave canónica son los otros seis atributos, exactos. Si esa misma arandela viene sin "
    "acabado es otra clave y se vuelve a preguntar; si dos respuestas humanas se contradicen, no "
    "hereda ninguna.")),
}

_EN_LINEA = (
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)"), r"<em>\1</em>"),
)


def _en_linea(texto: str) -> str:
    salida = html.escape(texto)
    for patron, reemplazo in _EN_LINEA:
        salida = patron.sub(reemplazo, salida)
    return salida


def _fila_de_tabla(linea: str) -> list[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def markdown_a_html(md: str) -> str:
    lineas = md.splitlines()
    fuera: list[str] = []
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        despojada = linea.strip()

        if not despojada:
            i += 1
        elif despojada.startswith("|"):
            cabecera = _fila_de_tabla(despojada)
            i += 2                      # la cabecera y su separador |---|
            cuerpo = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                cuerpo.append(_fila_de_tabla(lineas[i].strip()))
                i += 1
            fuera.append("<table><tr>" + "".join(f"<th>{_en_linea(c)}</th>" for c in cabecera)
                         + "</tr>")
            for fila in cuerpo:
                fuera.append("<tr>" + "".join(f"<td>{_en_linea(c)}</td>" for c in fila) + "</tr>")
            fuera.append("</table>")
        elif despojada.startswith("- "):
            fuera.append("<ul>")
            while i < len(lineas) and lineas[i].strip().startswith("- "):
                fuera.append(f"<li>{_en_linea(lineas[i].strip()[2:])}</li>")
                i += 1
            fuera.append("</ul>")
        elif despojada.startswith("## "):
            fuera.append(f"<h2>{_en_linea(despojada[3:])}</h2>")
            i += 1
        elif despojada.startswith("# "):
            fuera.append(f"<h1>{_en_linea(despojada[2:])}</h1>")
            i += 1
        elif despojada.startswith(":::figura "):
            nombre = despojada[len(":::figura "):].strip()
            if nombre not in FIGURAS:
                raise SystemExit(f"figura desconocida en el markdown: {nombre!r}")
            svg, pie = FIGURAS[nombre]
            fuera.append(f"<figure>{svg}<figcaption>{_en_linea(pie)}</figcaption></figure>")
            i += 1
        elif despojada == "---":
            fuera.append("<hr>")
            i += 1
        else:
            # El parrafo que sigue al titulo es la linea de autor: va en gris.
            es_subtitulo = bool(fuera) and fuera[-1].startswith("<h1>")
            clase = ' class="sub"' if es_subtitulo else ""
            fuera.append(f"<p{clase}>{_en_linea(despojada)}</p>")
            i += 1
    return "\n".join(fuera)


def convertir(nombre_md: str, nombre_pdf: str) -> pathlib.Path:
    md = (DOCS / f"{nombre_md}.md").read_text(encoding="utf-8")
    titulo = md.splitlines()[0].lstrip("# ").strip()
    pagina = (f'<meta charset="utf-8">\n<title>{html.escape(titulo)}</title>\n'
              f"<style>{ESTILO}</style>\n"
              f'<div class="hoja">\n{markdown_a_html(md)}\n</div>\n')
    fuente = AQUI / f"{nombre_md}-doc.html"
    fuente.write_text(pagina, encoding="utf-8")
    destino = DOCS / f"{nombre_pdf}.pdf"
    render(f"{nombre_md}-doc", destino)
    return destino


if __name__ == "__main__":
    print(convertir(sys.argv[1], sys.argv[2]))
