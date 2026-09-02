import { useMemo, useState } from "react"
import { CheckCircle2, Waypoints } from "lucide-react"
import { toast } from "sonner"

import { resolverCelda } from "@/api/cliente"
import { guardarAutor, leerAutor } from "@/lib/autor"
import { ATRIBUTOS, type Atributo, type LineaSalida, type Motivo } from "@/api/tipos"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { ESTILOS_PROCEDENCIA } from "@/lib/procedencia"

const ETIQUETA_ATRIBUTO: Record<Atributo, string> = {
  nombre: "Nombre",
  material: "Material",
  calidad: "Calidad",
  medida: "Medida",
  longitud: "Longitud",
  norma: "Norma",
  acabado: "Acabado",
}

interface PanelResolucionProps {
  sesionId: string
  linea: LineaSalida | null
  abierto: boolean
  onOpenChange: (abierto: boolean) => void
  onResuelto: (linea: LineaSalida) => void
  onVerTraza: (lineaId: string) => void
}

interface GrupoMotivo {
  atributo: Atributo
  motivos: Motivo[]
}

export function PanelResolucion({
  sesionId,
  linea,
  abierto,
  onOpenChange,
  onResuelto,
  onVerTraza,
}: PanelResolucionProps) {
  const [guardando, setGuardando] = useState<Atributo | null>(null)
  const [valoresManuales, setValoresManuales] = useState<Record<string, string>>({})
  const [autor, setAutor] = useState<string>(() => leerAutor())

  const { grupos, motivosGenerales } = useMemo(() => {
    const grupos: GrupoMotivo[] = []
    const motivosGenerales: Motivo[] = []
    if (linea) {
      for (const atributo of ATRIBUTOS) {
        const motivosDelAtributo = linea.motivos.filter((m) => m.atributo === atributo)
        if (motivosDelAtributo.length > 0) grupos.push({ atributo, motivos: motivosDelAtributo })
      }
      for (const motivo of linea.motivos) {
        if (!motivo.atributo) motivosGenerales.push(motivo)
      }
    }
    return { grupos, motivosGenerales }
  }, [linea])

  if (!linea) return null

  async function resolver(atributo: Atributo, valor: string) {
    if (!linea || !valor.trim()) return
    if (!autor.trim()) {
      toast.error("Indica quién resuelve: la respuesta se guarda con su nombre.")
      return
    }
    guardarAutor(autor)
    setGuardando(atributo)
    try {
      const actualizada = await resolverCelda(sesionId, linea.id, atributo, valor.trim(), autor.trim())
      onResuelto(actualizada)
      toast.success(`${ETIQUETA_ATRIBUTO[atributo]} resuelto para la fila ${linea.fila_origen}.`)
      if (actualizada.estado === "RESUELTA") {
        onOpenChange(false)
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "No se pudo resolver la celda.")
    } finally {
      setGuardando(null)
    }
  }

  return (
    <Sheet open={abierto} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>
            Fila {linea.fila_origen} · {linea.nombre.valor ?? "sin nombre"}
          </SheetTitle>
          <SheetDescription>
            Línea {linea.id} · cantidad {linea.cantidad} · confianza {linea.confianza}
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-4 px-4 pb-6">
          {/* La respuesta se guarda en el histórico con quien la dio: sin autor
              no es auditable y el servidor la rechaza con un 422. */}
          {linea.estado !== "RESUELTA" && (
            <div className="space-y-1.5">
              <Label htmlFor="autor-resolucion" className="text-xs text-muted-foreground">
                Quién resuelve
              </Label>
              <Input
                id="autor-resolucion"
                value={autor}
                placeholder="tu.nombre@empresa.com"
                onChange={(e) => setAutor(e.target.value)}
                onBlur={() => guardarAutor(autor)}
              />
            </div>
          )}
          {linea.estado === "RESUELTA" ? (
            <div className="flex items-center gap-2 rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
              <CheckCircle2 className="size-4" />
              Esta línea ya está resuelta.
            </div>
          ) : (
            grupos.map((grupo) => {
              const conPropuesta = grupo.motivos.find((m) => m.valor_propuesto)
              const guardandoEste = guardando === grupo.atributo
              const sinAutor = !autor.trim()
              return (
                <div key={grupo.atributo} className="space-y-2 rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{ETIQUETA_ATRIBUTO[grupo.atributo]}</span>
                    <Badge className={ESTILOS_PROCEDENCIA[linea[grupo.atributo].procedencia].clasesBadge}>
                      {ESTILOS_PROCEDENCIA[linea[grupo.atributo].procedencia].etiqueta}
                    </Badge>
                  </div>
                  {grupo.motivos.map((motivo) => (
                    <p key={motivo.codigo} className="text-sm text-muted-foreground">
                      {motivo.texto}
                    </p>
                  ))}

                  {conPropuesta?.valor_propuesto ? (
                    <Button
                      size="sm"
                      disabled={guardando !== null || sinAutor}
                      onClick={() => resolver(grupo.atributo, conPropuesta.valor_propuesto!)}
                    >
                      {guardandoEste ? "Confirmando…" : `Usar «${conPropuesta.valor_propuesto}»`}
                    </Button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <Label htmlFor={`valor-${grupo.atributo}`} className="sr-only">
                        Valor para {ETIQUETA_ATRIBUTO[grupo.atributo]}
                      </Label>
                      <Input
                        id={`valor-${grupo.atributo}`}
                        placeholder="Escribe el valor correcto"
                        value={valoresManuales[grupo.atributo] ?? ""}
                        disabled={guardando !== null || sinAutor}
                        onChange={(e) =>
                          setValoresManuales((prev) => ({
                            ...prev,
                            [grupo.atributo]: e.target.value,
                          }))
                        }
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            resolver(grupo.atributo, valoresManuales[grupo.atributo] ?? "")
                          }
                        }}
                      />
                      <Button
                        size="sm"
                        disabled={guardando !== null || sinAutor || !(valoresManuales[grupo.atributo] ?? "").trim()}
                        onClick={() => resolver(grupo.atributo, valoresManuales[grupo.atributo] ?? "")}
                      >
                        {guardandoEste ? "Confirmando…" : "Confirmar"}
                      </Button>
                    </div>
                  )}
                </div>
              )
            })
          )}

          {motivosGenerales.length > 0 && (
            <div className="space-y-2 rounded-md border border-dashed p-3">
              <span className="text-sm font-medium">Aviso de fila completa</span>
              {motivosGenerales.map((motivo) => (
                <p key={motivo.codigo} className="text-sm text-muted-foreground">
                  {motivo.texto}
                </p>
              ))}
              <p className="text-xs text-muted-foreground">
                No se resuelve con un clic: requiere revisar la fila entera contra el MTO
                original.
              </p>
            </div>
          )}

          <Button variant="outline" onClick={() => onVerTraza(linea.id)}>
            <Waypoints />
            Ver traza completa
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
