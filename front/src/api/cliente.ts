import type { LineaSalida, RespuestaProcesar } from "./tipos"

/** El front lo sirve el mismo proceso FastAPI (api/servidor.py) desde
 * front/dist, así que todas las llamadas van a origen relativo: no hay CORS
 * ni URL base que configurar, ni en desarrollo (Vite proxy) ni en frío. */

async function extraerMensajeError(respuesta: Response): Promise<string> {
  try {
    const datos = await respuesta.json()
    if (typeof datos?.detail === "string") return datos.detail
    return JSON.stringify(datos)
  } catch {
    return `Error ${respuesta.status} al llamar a la API.`
  }
}

export async function procesarMTO(archivo: File): Promise<RespuestaProcesar> {
  const formulario = new FormData()
  formulario.append("archivo", archivo)
  const respuesta = await fetch("/api/procesar", { method: "POST", body: formulario })
  if (!respuesta.ok) throw new Error(await extraerMensajeError(respuesta))
  return respuesta.json()
}

export async function resolverCelda(
  sesionId: string,
  lineaId: string,
  atributo: string,
  valor: string,
  autor: string,
): Promise<LineaSalida> {
  const respuesta = await fetch("/api/resolver", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sesion_id: sesionId, linea_id: lineaId, atributo, valor, autor }),
  })
  if (!respuesta.ok) throw new Error(await extraerMensajeError(respuesta))
  return respuesta.json()
}

export function urlExportar(sesionId: string): string {
  return `/api/exportar?sesion_id=${encodeURIComponent(sesionId)}`
}
