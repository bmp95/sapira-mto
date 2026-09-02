import { type ChangeEvent, useRef, useState } from "react"
import { FileSpreadsheet, Loader2, UploadCloud } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface PantallaSubidaProps {
  cargando: boolean
  error: string | null
  onProcesar: (archivo: File) => void
}

export function PantallaSubida({ cargando, error, onProcesar }: PantallaSubidaProps) {
  const [archivo, setArchivo] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  function manejarSeleccion(evento: ChangeEvent<HTMLInputElement>) {
    const elegido = evento.target.files?.[0] ?? null
    setArchivo(elegido)
  }

  function manejarSubmit() {
    if (archivo) onProcesar(archivo)
  }

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
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={cargando}
            className="flex w-full flex-col items-center gap-2 rounded-md border-2 border-dashed border-border p-8 text-center transition-colors hover:border-primary/50 hover:bg-muted/40 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {archivo ? (
              <>
                <FileSpreadsheet className="size-8 text-muted-foreground" />
                <span className="text-sm font-medium">{archivo.name}</span>
                <span className="text-xs text-muted-foreground">
                  {(archivo.size / 1024).toFixed(0)} KB · cambiar fichero
                </span>
              </>
            ) : (
              <>
                <UploadCloud className="size-8 text-muted-foreground" />
                <span className="text-sm font-medium">Selecciona un fichero .xlsx</span>
                <span className="text-xs text-muted-foreground">o arrastra el MTO aquí</span>
              </>
            )}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={manejarSeleccion}
            disabled={cargando}
          />

          {error && (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
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
