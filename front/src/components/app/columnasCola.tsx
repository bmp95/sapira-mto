import { createColumnHelper } from "@tanstack/react-table"
import { Waypoints } from "lucide-react"

import { ATRIBUTOS, type LineaSalida } from "@/api/tipos"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

import { CeldaAtributo } from "./CeldaAtributo"

const columnHelper = createColumnHelper<LineaSalida>()

const ETIQUETA_ATRIBUTO: Record<(typeof ATRIBUTOS)[number], string> = {
  nombre: "Nombre",
  material: "Material",
  calidad: "Calidad",
  medida: "Medida",
  longitud: "Longitud",
  norma: "Norma",
  acabado: "Acabado",
}

interface OpcionesColumnas {
  onVerTraza: (lineaId: string) => void
}

export function construirColumnas({ onVerTraza }: OpcionesColumnas) {
  return [
    columnHelper.accessor("fila_origen", {
      header: "Fila",
      size: 56,
      cell: (info) => <span className="text-sm text-muted-foreground">{info.getValue()}</span>,
    }),
    columnHelper.accessor("cantidad", {
      header: "Cant.",
      size: 56,
      cell: (info) => <span className="text-sm tabular-nums">{info.getValue()}</span>,
    }),
    columnHelper.accessor("estado", {
      header: "Estado",
      size: 130,
      cell: (info) => {
        const resuelta = info.getValue() === "RESUELTA"
        return (
          <Badge
            className={
              resuelta
                ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
                : "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
            }
          >
            {resuelta ? "Resuelta" : "En revisión"}
          </Badge>
        )
      },
    }),
    columnHelper.accessor("confianza", {
      header: "Conf.",
      size: 60,
      cell: (info) => <span className="text-sm tabular-nums">{info.getValue()}</span>,
    }),
    ...ATRIBUTOS.map((atributo) =>
      columnHelper.accessor(atributo, {
        id: atributo,
        header: ETIQUETA_ATRIBUTO[atributo],
        size: atributo === "nombre" || atributo === "norma" ? 150 : 110,
        cell: (info) => <CeldaAtributo valor={info.getValue()} />,
      }),
    ),
    columnHelper.display({
      id: "acciones",
      header: "",
      size: 90,
      cell: (info) => (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={(evento) => {
            evento.stopPropagation()
            onVerTraza(info.row.original.id)
          }}
        >
          <Waypoints />
          Traza
        </Button>
      ),
    }),
  ]
}
