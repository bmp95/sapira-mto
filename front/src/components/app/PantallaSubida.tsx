import { type ChangeEvent, type DragEvent, useEffect, useRef, useState } from "react"
import { FileSpreadsheet, Loader2, UploadCloud } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface PantallaSubidaProps {
  cargando: boolean
  error: string | null
  onProcesar: (archivo: File) => void
}

function esXlsx(nombre: string): boolean {
  return nombre.toLowerCase().endsWith(".xlsx")
}

function mensajeExtensionInvalida(nombre: string): string {
  return `El fichero "${nombre}" no es un .xlsx válido. Sube el MTO en formato Excel (.xlsx).`
}

/** Si sueltan varios ficheros a la vez (p.ej. una selección múltiple desde
 * el explorador), no hace falta que el primero de la lista sea el bueno --
 * basta con que exista un .xlsx entre ellos. Si ninguno lo es, se informa
 * del primero para que el mensaje de error sea concreto. */
function primerXlsxDe(lista: FileList): File | null {
  for (let i = 0; i < lista.length; i++) {
    const candidato = lista.item(i)
    if (candidato && esXlsx(candidato.name)) return candidato
  }
  return null
}

export function PantallaSubida({ cargando, error, onProcesar }: PantallaSubidaProps) {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const [arrastrando, setArrastrando] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Si el usuario falla la puntería y suelta el fichero fuera de la zona,
  // el navegador por defecto lo abre o lo descarga -- se sale de la
  // aplicación con el trabajo hecho. Estos manejadores a nivel de ventana
  // lo evitan sin interferir con el drop dentro de la zona: React ya llama
  // a preventDefault ahí antes de que el evento burbujee hasta aquí.
  useEffect(() => {
    function evitarNavegacion(evento: globalThis.DragEvent) {
      evento.preventDefault()
    }
    window.addEventListener("dragover", evitarNavegacion)
    window.addEventListener("drop", evitarNavegacion)
    return () => {
      window.removeEventListener("dragover", evitarNavegacion)
      window.removeEventListener("drop", evitarNavegacion)
    }
  }, [])

  function aceptarArchivo(candidato: File | null) {
    if (!candidato) return
    if (!esXlsx(candidato.name)) {
      setErrorLocal(mensajeExtensionInvalida(candidato.name))
      return
    }
    setErrorLocal(null)
    setArchivo(candidato)
  }

  function manejarSeleccion(evento: ChangeEvent<HTMLInputElement>) {
    aceptarArchivo(evento.target.files?.[0] ?? null)
    // Permite volver a elegir el mismo fichero dos veces seguidas (si no se
    // limpia, el segundo `change` con el mismo path no dispara evento).
    evento.target.value = ""
  }

  function manejarSubmit() {
    if (archivo) onProcesar(archivo)
  }

  function manejarDragEnter(evento: DragEvent<HTMLDivElement>) {
    evento.preventDefault()
    if (cargando) return
    setArrastrando(true)
  }

  function manejarDragOver(evento: DragEvent<HTMLDivElement>) {
    // Imprescindible: sin este preventDefault el navegador nunca dispara
    // el evento drop -- el arrastre se trata como una navegación normal.
    evento.preventDefault()
  }

  function manejarDragLeave(evento: DragEvent<HTMLDivElement>) {
    evento.preventDefault()
    // dragenter/dragleave se disparan también al pasar sobre los hijos
    // (icono, texto). Si el destino del ratón sigue dentro de la zona, no
    // es una salida real -- comprobar por contención evita el parpadeo que
    // daría un contador ingenuo, y no se rompe cuando el contenido de la
    // zona cambia de icono/texto en cuanto empieza a arrastrarse.
    const destino = evento.relatedTarget as Node | null
    if (destino && evento.currentTarget.contains(destino)) return
    setArrastrando(false)
  }

  function manejarDrop(evento: DragEvent<HTMLDivElement>) {
    evento.preventDefault()
    setArrastrando(false)
    if (cargando) return
    const lista = evento.dataTransfer.files
    if (lista.length === 0) return
    aceptarArchivo(primerXlsxDe(lista) ?? lista.item(0))
  }

  const mensajeError = error ?? errorLocal

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted/30 p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl">Reconciliación de MTO · Tornillería</CardTitle>
          <CardDescription>
            Sube el MTO en formato Excel para generar la cola de compras.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Zona de arrastre: un div, no un botón -- anidar el botón real
              de "seleccionar fichero" dentro de otro elemento interactivo
              da problemas de accesibilidad y de eventos de arrastre entre
              navegadores. El div solo recibe los eventos de drag/drop; abrir
              el selector es responsabilidad exclusiva del botón de dentro,
              que ya es accesible por teclado sin ningún manejador extra. */}
          <div
            onDragEnter={manejarDragEnter}
            onDragOver={manejarDragOver}
            onDragLeave={manejarDragLeave}
            onDrop={manejarDrop}
            className={cn(
              "flex w-full flex-col items-center gap-2 rounded-md border-2 border-dashed p-8 text-center transition-colors",
              cargando ? "opacity-60" : "border-border",
              arrastrando && !cargando && "border-primary bg-primary/5",
            )}
          >
            {arrastrando ? (
              <>
                <UploadCloud className="size-8 text-primary" />
                <span className="text-sm font-medium">Suelta el fichero aquí</span>
              </>
            ) : archivo ? (
              <>
                <FileSpreadsheet className="size-8 text-muted-foreground" />
                <span className="text-sm font-medium">{archivo.name}</span>
                <span className="text-xs text-muted-foreground">
                  {(archivo.size / 1024).toFixed(0)} KB
                </span>
              </>
            ) : (
              <>
                <UploadCloud className="size-8 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">o arrastra el MTO aquí</span>
              </>
            )}

            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mt-2"
              disabled={cargando}
              onClick={() => inputRef.current?.click()}
            >
              {archivo ? "Cambiar fichero" : "Seleccionar fichero"}
            </Button>
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={manejarSeleccion}
              disabled={cargando}
            />
          </div>

          {mensajeError && (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {mensajeError}
            </p>
          )}

          <Button className="w-full" disabled={!archivo || cargando} onClick={manejarSubmit}>
            {cargando ? (
              <>
                <Loader2 className="animate-spin" />
                Procesando el MTO…
              </>
            ) : (
              "Procesar MTO"
            )}
          </Button>
          {cargando && (
            <p className="text-center text-xs text-muted-foreground">
              Segmentando, extrayendo y validando cada fila. Puede tardar hasta un minuto.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
