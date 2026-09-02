import { useMemo, useState } from "react"
import { Search } from "lucide-react"

import type { LineaSalida } from "@/api/tipos"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { etiquetaMotivo } from "@/lib/motivos"

import { TablaCola } from "./TablaCola"

interface PestanaColaProps {
  lineas: LineaSalida[]
  lineaSeleccionadaId: string | null
  onSeleccionar: (linea: LineaSalida) => void
  onVerTraza: (lineaId: string) => void
}

function textoBusquedaDe(linea: LineaSalida): string {
  const valores = [
    String(linea.fila_origen),
    linea.nombre.valor,
    linea.material.valor,
    linea.calidad.valor,
    linea.medida.valor,
    linea.longitud.valor,
    linea.norma.valor,
    linea.acabado.valor,
    linea.texto_origen,
  ]
  return valores.filter(Boolean).join(" ").toLowerCase()
}

export function PestanaCola({
  lineas,
  lineaSeleccionadaId,
  onSeleccionar,
  onVerTraza,
}: PestanaColaProps) {
  const [busqueda, setBusqueda] = useState("")
  const [filtroEstado, setFiltroEstado] = useState<"todas" | "RESUELTA" | "REVISION_MANUAL">(
    "todas",
  )
  const [filtroMotivo, setFiltroMotivo] = useState<string>("todos")

  const motivosDisponibles = useMemo(() => {
    const codigos = new Set<string>()
    for (const linea of lineas) {
      for (const motivo of linea.motivos) codigos.add(motivo.codigo)
    }
    return Array.from(codigos).sort((a, b) => etiquetaMotivo(a).localeCompare(etiquetaMotivo(b)))
  }, [lineas])

  const lineasFiltradas = useMemo(() => {
    const busquedaNorm = busqueda.trim().toLowerCase()
    return lineas.filter((linea) => {
      if (filtroEstado !== "todas" && linea.estado !== filtroEstado) return false
      if (filtroMotivo !== "todos" && !linea.motivos.some((m) => m.codigo === filtroMotivo)) {
        return false
      }
      if (busquedaNorm && !textoBusquedaDe(linea).includes(busquedaNorm)) return false
      return true
    })
  }, [lineas, filtroEstado, filtroMotivo, busqueda])

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b bg-background px-6 py-3">
        <div className="relative w-64">
          <Search className="absolute top-1/2 left-2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por texto, nombre, calidad…"
            className="pl-8"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>

        <Select
          value={filtroEstado}
          onValueChange={(v) => setFiltroEstado(v as "todas" | "RESUELTA" | "REVISION_MANUAL")}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todas">Todos los estados</SelectItem>
            <SelectItem value="RESUELTA">Resueltas</SelectItem>
            <SelectItem value="REVISION_MANUAL">En revisión</SelectItem>
          </SelectContent>
        </Select>

        <Select value={filtroMotivo} onValueChange={setFiltroMotivo}>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="Motivo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos los motivos</SelectItem>
            {motivosDisponibles.map((codigo) => (
              <SelectItem key={codigo} value={codigo}>
                {etiquetaMotivo(codigo)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <span className="ml-auto text-xs text-muted-foreground">
          {lineasFiltradas.length} de {lineas.length} líneas
        </span>
      </div>

      <TablaCola
        lineas={lineasFiltradas}
        lineaSeleccionadaId={lineaSeleccionadaId}
        onSeleccionar={onSeleccionar}
        onVerTraza={onVerTraza}
      />
    </div>
  )
}
