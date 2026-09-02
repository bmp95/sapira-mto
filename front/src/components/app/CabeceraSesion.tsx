import { Download, RotateCcw } from "lucide-react"

import { urlExportar } from "@/api/cliente"
import type { Resumen } from "@/api/tipos"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

interface CabeceraSesionProps {
  sesionId: string
  resumen: Resumen
  onReiniciar: () => void
}

export function CabeceraSesion({ sesionId, resumen, onReiniciar }: CabeceraSesionProps) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-background px-6 py-3">
      <div className="flex items-center gap-2">
        <h1 className="text-base font-semibold">Cola de compras · Tornillería</h1>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">{resumen.total_lineas} líneas</Badge>
        <Badge className="border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
          {resumen.resueltas} resueltas
        </Badge>
        <Badge className="border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          {resumen.en_revision} en revisión
        </Badge>
        {resumen.fallos_de_proceso > 0 && (
          <Badge variant="destructive">{resumen.fallos_de_proceso} fallos de proceso</Badge>
        )}
        <Badge variant="outline">{resumen.segundos.toFixed(1)} s</Badge>
        <Badge variant="outline">{resumen.coste.toFixed(4)} $</Badge>

        <Button variant="outline" size="sm" asChild>
          <a href={urlExportar(sesionId)} download>
            <Download />
            Exportar
          </a>
        </Button>
        <Button variant="ghost" size="sm" onClick={onReiniciar}>
          <RotateCcw />
          Procesar otro MTO
        </Button>
      </div>
    </header>
  )
}
