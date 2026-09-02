/** Etiquetas cortas para el filtro por motivo de la Cola. El texto completo
 * en castellano (la frase entera) ya lo manda la API en `motivo.texto` — esto
 * es solo para el desplegable de filtro, donde hace falta algo breve.
 * Si el motor añade un código nuevo que no está aquí, se humaniza el código
 * en vez de mostrarlo en mayúsculas y con guiones bajos: el front no se
 * rompe ni queda desactualizado por un código nuevo. */

const ETIQUETAS_MOTIVO: Record<string, string> = {
  SIN_NOMBRE: "Sin nombre",
  SIN_NORMA: "Sin norma",
  SIN_CALIDAD: "Sin calidad",
  LONGITUD_OBLIGATORIA_AUSENTE: "Longitud obligatoria ausente",
  LONGITUD_SIN_UNIDAD: "Longitud sin unidad",
  CONFIANZA_INSUFICIENTE: "Confianza insuficiente",
  LINEA_SIN_CELDAS_EVALUABLES: "Línea sin celdas evaluables",
  COBERTURA_INSUFICIENTE: "Cobertura insuficiente",
  SOLAPE_DE_TRAMOS: "Solape de tramos",
  RECUENTO_DE_SUSTANTIVOS_INCONSISTENTE: "Recuento de sustantivos inconsistente",
  PIEZA_SIN_NOMBRAR: "Pieza sin nombrar",
  FALLO_DE_PROCESO: "Fallo de proceso",
  CALIDAD_SOLO_TUERCA: "Calidad solo de tuerca",
  CALIDAD_SOLO_ARANDELA: "Calidad solo de arandela",
  INOX_CON_ACABADO_ZINC: "Inox con acabado de zinc",
  MATERIAL_NO_ADMITE_ZINC: "Material no admite zinc",
  SISTEMA_MEDIDA_INCOHERENTE: "Sistema de medida incoherente",
  GRADO_ASTM_INCOHERENTE: "Grado ASTM incoherente",
  MATERIAL_CONTRADICE_CALIDAD: "Material contradice calidad",
  MATERIAL_CONTRADICE_NORMA: "Material contradice norma",
  NOMBRE_CONTRADICE_NORMA: "Nombre contradice norma",
  NOMBRE_Y_NORMA_EQUIVALENTES: "Nombre y norma equivalentes",
  LONGITUD_INESPERADA: "Longitud inesperada",
  LONGITUD_IMPOSIBLE: "Longitud imposible",
  HISTORICO_EN_CONFLICTO: "Histórico en conflicto",
}

export function etiquetaMotivo(codigo: string): string {
  if (ETIQUETAS_MOTIVO[codigo]) return ETIQUETAS_MOTIVO[codigo]
  return codigo
    .toLowerCase()
    .split("_")
    .map((palabra) => palabra.charAt(0).toUpperCase() + palabra.slice(1))
    .join(" ")
}
