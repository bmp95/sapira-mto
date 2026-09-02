/** Contrato de datos de la API (api/servidor.py). Cada tipo aquí es un espejo
 * exacto de lo que motor/modelos.py serializa: si el motor cambia de forma,
 * este fichero es el único sitio que hay que tocar en el front. */

export const ATRIBUTOS = [
  "nombre",
  "material",
  "calidad",
  "medida",
  "longitud",
  "norma",
  "acabado",
] as const

export type Atributo = (typeof ATRIBUTOS)[number]

export type Procedencia = "EXTRAIDO" | "DERIVADO" | "HEREDADO" | "INFERIDO" | "AUSENTE"

export type Estado = "RESUELTA" | "REVISION_MANUAL"

export interface Valor {
  valor: string | null
  literal: string | null
  span: [number, number] | null
  procedencia: Procedencia
  regla: string | null
  confianza: number | null
  factores: Record<string, number>
}

export interface Motivo {
  codigo: string
  texto: string
  atributo: Atributo | null
  valor_propuesto: string | null
  factor_limitante: string | null
}

export interface LineaSalida {
  id: string
  fila_origen: number
  cantidad: number
  nombre: Valor
  material: Valor
  calidad: Valor
  medida: Valor
  longitud: Valor
  norma: Valor
  acabado: Valor
  confianza: number
  motivos: Motivo[]
  texto_origen: string
  tramo: [number, number] | null
  estado: Estado
}

export interface Resumen {
  total_lineas: number
  resueltas: number
  en_revision: number
  fallos_de_proceso: number
  segundos: number
  coste: number
}

export interface RespuestaProcesar {
  sesion_id: string
  resumen: Resumen
  lineas: LineaSalida[]
}

export function celdaDe(linea: LineaSalida, atributo: Atributo): Valor {
  return linea[atributo]
}
