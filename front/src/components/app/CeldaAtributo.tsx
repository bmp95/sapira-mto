import type { Valor } from "@/api/tipos"
import { ESTILOS_PROCEDENCIA } from "@/lib/procedencia"
import { cn } from "@/lib/utils"

interface CeldaAtributoProps {
  valor: Valor
  className?: string
}

/** La celda de la tabla de Cola: color de fondo por procedencia, para que se
 * distinga de un vistazo sin leer nada. El `title` nativo (no un Tooltip de
 * Radix) es deliberado -- con 20.000 filas x 7 columnas montar un trigger de
 * tooltip por celda sería carísimo; el navegador ya da un tooltip gratis. */
export function CeldaAtributo({ valor, className }: CeldaAtributoProps) {
  const estilo = ESTILOS_PROCEDENCIA[valor.procedencia]
  const texto = valor.valor ?? "—"
  const titulo = `${estilo.etiqueta}${valor.confianza !== null ? ` · confianza ${valor.confianza}` : ""}`

  return (
    <div
      title={titulo}
      className={cn(
        "flex h-full items-center truncate rounded-sm px-2 py-1 text-sm",
        estilo.clasesCelda,
        valor.valor === null && "italic",
        className,
      )}
    >
      {texto}
    </div>
  )
}
