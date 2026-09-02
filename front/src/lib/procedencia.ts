import type { Procedencia } from "@/api/tipos"

/** La idea central del sistema tiene que verse sin leer nada: cada
 * procedencia lleva un color fijo, el mismo en la celda de la Cola y en el
 * panel de Traza. Paleta de Tailwind, sin tonos a medida. */

interface EstiloProcedencia {
  etiqueta: string
  clasesCelda: string
  clasesBadge: string
  punto: string
}

export const ESTILOS_PROCEDENCIA: Record<Procedencia, EstiloProcedencia> = {
  EXTRAIDO: {
    etiqueta: "Extraído",
    clasesCelda: "bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200",
    clasesBadge:
      "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200",
    punto: "bg-emerald-500",
  },
  DERIVADO: {
    etiqueta: "Derivado",
    clasesCelda: "bg-sky-50 text-sky-900 dark:bg-sky-950/40 dark:text-sky-200",
    clasesBadge:
      "border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200",
    punto: "bg-sky-500",
  },
  HEREDADO: {
    etiqueta: "Heredado",
    clasesCelda: "bg-violet-50 text-violet-900 dark:bg-violet-950/40 dark:text-violet-200",
    clasesBadge:
      "border-violet-300 bg-violet-50 text-violet-800 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-200",
    punto: "bg-violet-500",
  },
  INFERIDO: {
    etiqueta: "Inferido",
    clasesCelda: "bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200",
    clasesBadge:
      "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200",
    punto: "bg-amber-500",
  },
  AUSENTE: {
    etiqueta: "Ausente",
    clasesCelda: "bg-muted/60 text-muted-foreground",
    clasesBadge: "border-border bg-muted text-muted-foreground",
    punto: "bg-muted-foreground/40",
  },
}

export const ORDEN_PROCEDENCIA: Procedencia[] = [
  "EXTRAIDO",
  "DERIVADO",
  "HEREDADO",
  "INFERIDO",
  "AUSENTE",
]
