import { useRef } from "react"
import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { useVirtualizer } from "@tanstack/react-virtual"

import type { LineaSalida } from "@/api/tipos"
import { cn } from "@/lib/utils"

import { construirColumnas } from "./columnasCola"

interface TablaColaProps {
  lineas: LineaSalida[]
  lineaSeleccionadaId: string | null
  onSeleccionar: (linea: LineaSalida) => void
  onVerTraza: (lineaId: string) => void
}

const ALTO_FILA = 40

/** Tabla virtualizada: TanStack Table calcula columnas y modelo de filas,
 * TanStack Virtual decide cuáles de esas filas tocan pintarse. Ni <table>
 * ni <tr> -- filas como divs de ancho fijo por columna, que es el patrón
 * que permite combinar los dos sin que el layout se recalcule en cada
 * scroll. Así se mantiene fluida con 20.000 filas. */
export function TablaCola({
  lineas,
  lineaSeleccionadaId,
  onSeleccionar,
  onVerTraza,
}: TablaColaProps) {
  const columnas = useRef(construirColumnas({ onVerTraza })).current
  const contenedorRef = useRef<HTMLDivElement>(null)

  const tabla = useReactTable({
    data: lineas,
    columns: columnas,
    getCoreRowModel: getCoreRowModel(),
  })

  const filas = tabla.getRowModel().rows

  const virtualizador = useVirtualizer({
    count: filas.length,
    getScrollElement: () => contenedorRef.current,
    estimateSize: () => ALTO_FILA,
    overscan: 12,
  })

  const anchoTotal = tabla.getHeaderGroups()[0]?.headers.reduce((s, h) => s + h.getSize(), 0) ?? 0

  return (
    <div ref={contenedorRef} className="relative flex-1 overflow-auto">
      <div style={{ minWidth: anchoTotal }}>
        {/* Cabecera, pegada arriba del propio contenedor con scroll. */}
        {tabla.getHeaderGroups().map((grupo) => (
          <div key={grupo.id} className="sticky top-0 z-10 flex border-b bg-background">
            {grupo.headers.map((header) => (
              <div
                key={header.id}
                style={{ width: header.getSize() }}
                className="shrink-0 truncate px-2 py-2 text-xs font-medium text-muted-foreground"
              >
                {flexRender(header.column.columnDef.header, header.getContext())}
              </div>
            ))}
          </div>
        ))}

        {filas.length === 0 && (
          <p className="p-8 text-center text-sm text-muted-foreground">
            Ninguna línea coincide con los filtros actuales.
          </p>
        )}

        <div style={{ height: virtualizador.getTotalSize(), position: "relative" }}>
          {virtualizador.getVirtualItems().map((filaVirtual) => {
            const fila = filas[filaVirtual.index]
            const linea = fila.original
            const seleccionada = linea.id === lineaSeleccionadaId
            return (
              <div
                key={fila.id}
                data-index={filaVirtual.index}
                onClick={() => onSeleccionar(linea)}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: `${filaVirtual.size}px`,
                  transform: `translateY(${filaVirtual.start}px)`,
                }}
                className={cn(
                  "flex cursor-pointer items-stretch border-b hover:bg-muted/50",
                  seleccionada && "bg-muted",
                )}
              >
                {fila.getVisibleCells().map((celda) => (
                  <div
                    key={celda.id}
                    style={{ width: celda.column.getSize() }}
                    className="flex shrink-0 items-center overflow-hidden px-1 py-1"
                  >
                    {flexRender(celda.column.columnDef.cell, celda.getContext())}
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
