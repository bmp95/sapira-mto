"""Renderiza los HTML de docs/activos a PDF A4 con Chromium.

Sustituye el marcador LOGO_B64 por el logo de Sapira embebido en base64 para
que el documento sea un unico fichero autocontenido, sin dependencias de red.

Uso:  python docs/activos/render.py one-pager-visual [guia-visual ...]
"""

import base64
import pathlib
import sys

from playwright.sync_api import sync_playwright

AQUI = pathlib.Path(__file__).resolve().parent
DOCS = AQUI.parent


def logo_data_uri() -> str:
    crudo = (AQUI / "sapira-logo.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(crudo).decode("ascii")


def render(nombre: str, destino_pdf: pathlib.Path, ancho_px: int = 794) -> None:
    fuente = AQUI / f"{nombre}.html"
    html = fuente.read_text(encoding="utf-8").replace("LOGO_B64", logo_data_uri())
    temporal = AQUI / f".{nombre}.render.html"
    temporal.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            pagina = navegador.new_page(viewport={"width": ancho_px, "height": 1123})
            pagina.goto(temporal.as_uri(), wait_until="networkidle")
            pagina.emulate_media(media="print")
            pagina.pdf(
                path=str(destino_pdf),
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            # Guardian de maquetacion: si algun bloque desborda su caja, el PDF
            # sale con texto cortado y en una captura pequena no se ve. Se
            # comprueba en el DOM, no a ojo.
            # Solo miran los contenedores de altura fija: un elemento de texto
            # con line-height apretado tambien da scrollHeight>clientHeight y
            # no es un recorte, es metrica de la fuente.
            desbordes = pagina.evaluate(
                """() => [...document.querySelectorAll('.hoja, .cuerpo, .izq, .der, .pagina, .dos, .flujo, .notas')]
                    .filter(e => e.scrollHeight - e.clientHeight > 2)
                    .map(e => `${e.className}: ${e.scrollHeight}>${e.clientHeight}`)"""
            )
            if desbordes:
                raise SystemExit("CONTENIDO CORTADO en %s -> %s" % (nombre, desbordes))

            # Captura para revision visual, a la anchura real de la hoja.
            pagina.screenshot(path=str(AQUI / f"{nombre}.png"), full_page=True)
            navegador.close()
    finally:
        temporal.unlink(missing_ok=True)

    paginas = destino_pdf.read_bytes().count(b"/Type /Page\n") or destino_pdf.read_bytes().count(b"/Type/Page")
    print(f"{destino_pdf.name}: {destino_pdf.stat().st_size // 1024} KB, ~{paginas} pag.")


SALIDAS = {
    "one-pager-visual": DOCS / "De aqui a produccion - One-pager.pdf",
    "guia-visual": DOCS / "Guia interna - Como funciona.pdf",
}

if __name__ == "__main__":
    for nombre in sys.argv[1:] or ["one-pager-visual"]:
        render(nombre, SALIDAS[nombre])
