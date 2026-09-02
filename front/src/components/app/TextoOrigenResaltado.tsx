import { construirSegmentos, type RangoResaltado } from "@/lib/resaltado"
import { cn } from "@/lib/utils"

interface TextoOrigenResaltadoProps {
  texto: string
  tramo: [number, number] | null
  spanAtributo: [number, number] | null
}

/** El texto completo de la fila, con el tramo del elemento en un tono suave
 * siempre visible, y -- cuando hay un atributo activo -- su span exacto
 * remarcado encima. Las dos capas conviven porque `construirSegmentos`
 * acumula clases por rango en vez de elegir un único ganador. */
export function TextoOrigenResaltado({ texto, tramo, spanAtributo }: TextoOrigenResaltadoProps) {
  const rangos: RangoResaltado[] = []
  if (tramo) rangos.push({ inicio: tramo[0], fin: tramo[1], clase: "bg-muted rounded-sm" })
  if (spanAtributo) {
    rangos.push({
      inicio: spanAtributo[0],
      fin: spanAtributo[1],
      clase:
        "bg-amber-200 text-amber-950 ring-1 ring-amber-400 rounded-sm dark:bg-amber-900/70 dark:text-amber-100 dark:ring-amber-600",
    })
  }
  const segmentos = construirSegmentos(texto, rangos)

  return (
    <p className="font-mono text-sm leading-relaxed break-words whitespace-pre-wrap">
      {segmentos.map((segmento, indice) => (
        <span key={indice} className={cn(segmento.clase)}>
          {segmento.texto}
        </span>
      ))}
    </p>
  )
}
