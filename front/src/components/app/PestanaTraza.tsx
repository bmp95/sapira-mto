import { useState } from "react"
import { ArrowLeft } from "lucide-react"

import { ATRIBUTOS, type Atributo, type LineaSalida } from "@/api/tipos"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { spanCoincideConTexto } from "@/lib/resaltado"

import { TextoOrigenResaltado } from "./TextoOrigenResaltado"
import { TrazaCeldaCard } from "./TrazaCeldaCard"

const ETIQUETA_ATRIBUTO: Record<Atributo, string> = {
  nombre: "Nombre",
  material: "Material",
  calidad: "Calidad",
  medida: "Medida",
  longitud: "Longitud",
  norma: "Norma",
  acabado: "Acabado",
}

interface PestanaTrazaProps {
  lineas: LineaSalida[]
  lineaSeleccionada: LineaSalida | null
  onSeleccionar: (linea: LineaSalida) => void
  onVolverACola: () => void
}

function spanEsValido(linea: LineaSalida, atributo: Atributo): boolean {
  const celda = linea[atributo]
  return spanCoincideConTexto(linea.texto_origen, celda.span, celda.literal)
}

export function PestanaTraza({
  lineas,
  lineaSeleccionada,
  onSeleccionar,
  onVolverACola,
}: PestanaTrazaProps) {
  const [atributoActivo, setAtributoActivo] = useState<Atributo | null>(null)

  function seleccionarPorId(id: string) {
    const encontrada = lineas.find((l) => l.id === id)
    if (encontrada) {
      setAtributoActivo(null)
      onSeleccionar(encontrada)
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b bg-background px-6 py-3">
        <Button variant="ghost" size="sm" onClick={onVolverACola}>
          <ArrowLeft />
          Volver a la cola
        </Button>
        <Separator orientation="vertical" className="h-6" />
        <span className="text-sm text-muted-foreground">Ir a la fila:</span>
        <Select value={lineaSeleccionada?.id ?? ""} onValueChange={seleccionarPorId}>
          <SelectTrigger className="w-72">
            <SelectValue placeholder="Selecciona una línea" />
          </SelectTrigger>
          <SelectContent>
            {lineas.map((linea) => (
              <SelectItem key={linea.id} value={linea.id}>
                Fila {linea.fila_origen} · {linea.nombre.valor ?? "sin nombre"} · {linea.id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        {!lineaSeleccionada ? (
          <p className="text-sm text-muted-foreground">
            Selecciona una línea en la pestaña Cola (o en el desplegable de arriba) para ver su
            traza completa.
          </p>
        ) : (
          <div className="mx-auto flex max-w-4xl flex-col gap-6">
            <div>
              <h2 className="mb-2 text-sm font-medium text-muted-foreground">
                Fila {lineaSeleccionada.fila_origen} · texto original completo
              </h2>
              <div className="rounded-md border bg-card p-4">
                <TextoOrigenResaltado
                  texto={lineaSeleccionada.texto_origen}
                  tramo={lineaSeleccionada.tramo}
                  spanAtributo={
                    atributoActivo && spanEsValido(lineaSeleccionada, atributoActivo)
                      ? lineaSeleccionada[atributoActivo].span
                      : null
                  }
                />
              </div>
              {!lineaSeleccionada.tramo && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Esta fila no llegó a segmentarse en elementos: no hay tramo que resaltar.
                </p>
              )}
            </div>

            <div>
              <h2 className="mb-2 text-sm font-medium text-muted-foreground">
                Los siete atributos
              </h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {ATRIBUTOS.map((atributo) => (
                  <TrazaCeldaCard
                    key={atributo}
                    atributo={atributo}
                    etiqueta={ETIQUETA_ATRIBUTO[atributo]}
                    valor={lineaSeleccionada[atributo]}
                    activo={atributoActivo === atributo}
                    spanValido={spanEsValido(lineaSeleccionada, atributo)}
                    onToggle={() =>
                      setAtributoActivo((actual) => (actual === atributo ? null : atributo))
                    }
                  />
                ))}
              </div>
            </div>

            <div>
              <h2 className="mb-2 text-sm font-medium text-muted-foreground">
                Motivos de la línea ({lineaSeleccionada.motivos.length})
              </h2>
              {lineaSeleccionada.motivos.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin motivos: la línea es limpia.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {lineaSeleccionada.motivos.map((motivo, indice) => (
                    <div key={`${motivo.codigo}-${indice}`} className="rounded-md border p-3">
                      <div className="mb-1 flex items-center gap-2">
                        <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                          {motivo.codigo}
                        </code>
                        {motivo.atributo && (
                          <span className="text-xs text-muted-foreground">
                            {ETIQUETA_ATRIBUTO[motivo.atributo]}
                          </span>
                        )}
                      </div>
                      <p className="text-sm">{motivo.texto}</p>
                      {motivo.valor_propuesto && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          Valor propuesto: <strong>{motivo.valor_propuesto}</strong>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
