/** Divide un texto en segmentos según una lista de rangos [inicio, fin) que
 * pueden anidarse o solaparse (p.ej. el span de una celda vive dentro del
 * `tramo` del elemento). Cada segmento resultante lleva las clases CSS de
 * todos los rangos que lo cubren, así que un tramo con una celda resaltada
 * dentro sale con las dos capas de color a la vez. */

export interface RangoResaltado {
  inicio: number
  fin: number
  clase: string
}

export interface SegmentoTexto {
  texto: string
  clase: string
}

/** Un valor resuelto a mano en la Cola lleva un span sintético
 * `(0, longitud del valor)` -- api/servidor.py lo fabrica solo para que el
 * validador de Pydantic acepte un `Valor` EXTRAIDO, no porque ese texto
 * exista en esa posición de `texto_origen`. Resaltar ese span sería mentir
 * sobre la procedencia -- justo lo que la invariante 1 del sistema prohíbe.
 * Antes de ofrecer "ver en el texto" hay que comprobar que el span, tal
 * cual, reproduce el literal en el texto original. */
export function spanCoincideConTexto(
  texto: string,
  span: [number, number] | null,
  literal: string | null,
): boolean {
  if (!span || !literal) return false
  const [inicio, fin] = span
  if (inicio < 0 || fin > texto.length || inicio >= fin) return false
  return texto.slice(inicio, fin) === literal
}

export function construirSegmentos(texto: string, rangos: RangoResaltado[]): SegmentoTexto[] {
  const validos = rangos.filter(
    (r) => r.inicio >= 0 && r.fin <= texto.length && r.inicio < r.fin,
  )
  const puntos = new Set<number>([0, texto.length])
  for (const r of validos) {
    puntos.add(r.inicio)
    puntos.add(r.fin)
  }
  const cortes = Array.from(puntos).sort((a, b) => a - b)

  const segmentos: SegmentoTexto[] = []
  for (let i = 0; i < cortes.length - 1; i++) {
    const inicio = cortes[i]
    const fin = cortes[i + 1]
    if (inicio >= fin) continue
    const clase = validos
      .filter((r) => r.inicio <= inicio && r.fin >= fin)
      .map((r) => r.clase)
      .join(" ")
    segmentos.push({ texto: texto.slice(inicio, fin), clase })
  }
  return segmentos
}
