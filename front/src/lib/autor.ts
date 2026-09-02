const CLAVE = "sapira-mto.autor"

/** Quien resuelve queda registrado en el historico junto a la respuesta: sin
 * autor no es auditable y el servidor la rechaza. No hay login en el alcance
 * del caso, asi que la identidad se guarda en el propio navegador -- suficiente
 * para un puesto de comprador, y honesto sobre lo que es. */
export function leerAutor(): string {
  try {
    return localStorage.getItem(CLAVE) ?? ""
  } catch {
    // Navegador con el almacenamiento bloqueado: se pide en cada sesion.
    return ""
  }
}

export function guardarAutor(autor: string): void {
  try {
    localStorage.setItem(CLAVE, autor.trim())
  } catch {
    // Sin persistencia no se rompe nada: el valor vive en memoria.
  }
}
