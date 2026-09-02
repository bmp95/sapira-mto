import { useMemo, useState } from "react"

import { procesarMTO } from "@/api/cliente"
import type { LineaSalida, Resumen } from "@/api/tipos"
import { CabeceraSesion } from "@/components/app/CabeceraSesion"
import { PanelResolucion } from "@/components/app/PanelResolucion"
import { PantallaSubida } from "@/components/app/PantallaSubida"
import { PestanaCola } from "@/components/app/PestanaCola"
import { PestanaTraza } from "@/components/app/PestanaTraza"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Toaster } from "@/components/ui/sonner"
import { recalcularResumen } from "@/lib/resumen"

type Pestana = "cola" | "traza"

function App() {
  const [sesionId, setSesionId] = useState<string | null>(null)
  const [resumen, setResumen] = useState<Resumen | null>(null)
  const [lineas, setLineas] = useState<LineaSalida[]>([])
  const [cargando, setCargando] = useState(false)
  const [errorSubida, setErrorSubida] = useState<string | null>(null)

  const [pestana, setPestana] = useState<Pestana>("cola")
  const [lineaSeleccionadaId, setLineaSeleccionadaId] = useState<string | null>(null)
  const [panelAbierto, setPanelAbierto] = useState(false)

  const lineaSeleccionada = useMemo(
    () => lineas.find((l) => l.id === lineaSeleccionadaId) ?? null,
    [lineas, lineaSeleccionadaId],
  )

  async function manejarProcesar(archivo: File) {
    setCargando(true)
    setErrorSubida(null)
    try {
      const respuesta = await procesarMTO(archivo)
      setSesionId(respuesta.sesion_id)
      setResumen(respuesta.resumen)
      setLineas(respuesta.lineas)
      setPestana("cola")
      setLineaSeleccionadaId(null)
    } catch (error) {
      setErrorSubida(error instanceof Error ? error.message : "No se pudo procesar el MTO.")
    } finally {
      setCargando(false)
    }
  }

  function manejarReiniciar() {
    setSesionId(null)
    setResumen(null)
    setLineas([])
    setErrorSubida(null)
    setLineaSeleccionadaId(null)
    setPanelAbierto(false)
    setPestana("cola")
  }

  function manejarSeleccionEnCola(linea: LineaSalida) {
    setLineaSeleccionadaId(linea.id)
    setPanelAbierto(linea.estado === "REVISION_MANUAL")
  }

  function manejarVerTraza(lineaId: string) {
    setLineaSeleccionadaId(lineaId)
    setPanelAbierto(false)
    setPestana("traza")
  }

  function manejarResuelto(actualizada: LineaSalida) {
    const siguientes = lineas.map((l) => (l.id === actualizada.id ? actualizada : l))
    setLineas(siguientes)
    setResumen((actual) => (actual ? recalcularResumen(actual, siguientes) : actual))
  }

  if (!sesionId || !resumen) {
    return (
      <>
        <PantallaSubida cargando={cargando} error={errorSubida} onProcesar={manejarProcesar} />
        <Toaster position="bottom-right" />
      </>
    )
  }

  return (
    <div className="flex h-svh flex-col">
      <CabeceraSesion sesionId={sesionId} resumen={resumen} onReiniciar={manejarReiniciar} />

      <Tabs
        value={pestana}
        onValueChange={(v) => setPestana(v as Pestana)}
        className="min-h-0 flex-1 gap-0"
      >
        <TabsList className="mx-6 mt-3 w-fit">
          <TabsTrigger value="cola">Cola</TabsTrigger>
          <TabsTrigger value="traza">Traza</TabsTrigger>
        </TabsList>

        <TabsContent value="cola" className="mt-0 flex min-h-0 flex-1 flex-col">
          <PestanaCola
            lineas={lineas}
            lineaSeleccionadaId={lineaSeleccionadaId}
            onSeleccionar={manejarSeleccionEnCola}
            onVerTraza={manejarVerTraza}
          />
        </TabsContent>

        <TabsContent value="traza" className="mt-0 flex min-h-0 flex-1 flex-col">
          <PestanaTraza
            lineas={lineas}
            lineaSeleccionada={lineaSeleccionada}
            onSeleccionar={(linea) => setLineaSeleccionadaId(linea.id)}
            onVolverACola={() => setPestana("cola")}
          />
        </TabsContent>
      </Tabs>

      <PanelResolucion
        sesionId={sesionId}
        linea={lineaSeleccionada}
        abierto={panelAbierto}
        onOpenChange={setPanelAbierto}
        onResuelto={manejarResuelto}
        onVerTraza={manejarVerTraza}
      />

      <Toaster position="bottom-right" />
    </div>
  )
}

export default App
