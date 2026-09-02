import { MapPin } from "lucide-react"

import type { Atributo, Valor } from "@/api/tipos"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ESTILOS_PROCEDENCIA } from "@/lib/procedencia"
import { cn } from "@/lib/utils"

const ETIQUETA_FACTOR: Record<string, string> = {
  procedencia: "Procedencia",
  literal: "Literal",
  segmentacion: "Segmentación",
  coherencia: "Coherencia",
}

interface TrazaCeldaCardProps {
  atributo: Atributo
  etiqueta: string
  valor: Valor
  activo: boolean
  spanValido: boolean
  onToggle: () => void
}

export function TrazaCeldaCard({
  atributo,
  etiqueta,
  valor,
  activo,
  spanValido,
  onToggle,
}: TrazaCeldaCardProps) {
  const estilo = ESTILOS_PROCEDENCIA[valor.procedencia]
  const entradasFactores = Object.entries(valor.factores)
  const minimo = entradasFactores.length > 0 ? Math.min(...entradasFactores.map(([, v]) => v)) : null

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-md border p-3",
        activo && "border-primary ring-1 ring-primary",
      )}
      data-atributo={atributo}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{etiqueta}</span>
        <Badge className={estilo.clasesBadge}>{estilo.etiqueta}</Badge>
      </div>

      <div className="text-lg font-semibold">{valor.valor ?? <span className="text-muted-foreground italic">sin dato</span>}</div>

      {valor.literal && spanValido && (
        <Button
          variant="outline"
          size="sm"
          className="w-fit gap-1 text-xs"
          onClick={onToggle}
        >
          <MapPin className="size-3" />
          literal «{valor.literal}» {activo ? "· ocultar en el texto" : "· ver en el texto"}
        </Button>
      )}
      {valor.literal && !spanValido && (
        <p className="text-xs text-muted-foreground">
          Valor «{valor.literal}» confirmado en la cola, sin posición en el texto original.
        </p>
      )}

      {valor.regla && (
        <p className="text-xs text-muted-foreground">
          Regla: <code className="rounded bg-muted px-1 py-0.5">{valor.regla}</code>
        </p>
      )}

      {entradasFactores.length > 0 ? (
        <div className="flex flex-wrap gap-1 pt-1">
          {entradasFactores.map(([clave, puntos]) => (
            <span
              key={clave}
              className={cn(
                "rounded border px-1.5 py-0.5 text-[11px] tabular-nums",
                puntos === 100
                  ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
                  : "border-destructive/40 bg-destructive/10 text-destructive",
                puntos === minimo && puntos < 100 && "font-semibold ring-1 ring-destructive/60",
              )}
              title={puntos === minimo && puntos < 100 ? "Factor limitante de esta celda" : undefined}
            >
              {ETIQUETA_FACTOR[clave] ?? clave}: {puntos}
            </span>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">Sin factores: la celda no se evaluó.</p>
      )}

      <p className="text-xs text-muted-foreground">
        Confianza de la celda: {valor.confianza ?? "—"}
      </p>
    </div>
  )
}
