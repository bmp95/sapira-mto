import type { LineaSalida, Resumen } from "@/api/tipos"

/** `/api/resolver` devuelve solo la línea recalculada, no un resumen nuevo.
 * El resumen que se ve en la cabecera se recalcula en el cliente a partir de
 * las líneas ya en memoria -- `total_lineas`, `fallos_de_proceso`, `segundos`
 * y `coste` no cambian al resolver una celda, así que se conservan del
 * resumen original y solo se recuentan `resueltas` / `en_revision`. */
export function recalcularResumen(base: Resumen, lineas: LineaSalida[]): Resumen {
  const resueltas = lineas.filter((l) => l.estado === "RESUELTA").length
  return {
    ...base,
    resueltas,
    en_revision: lineas.length - resueltas,
  }
}
