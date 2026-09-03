"""A1. Vota 3 pasadas: la firma es (numero, tipos). Los votos alimentan la confianza."""
from collections import Counter

from motor.modelos import Segmentacion
from motor.puerto_llm import PuertoLLM


def _firma(s: Segmentacion) -> tuple:
    return tuple(e.tipo_indicado.upper() for e in s.elementos)


def segmentar_con_votacion(puerto: PuertoLLM, texto: str, pasadas: int = 3) -> Segmentacion:
    resultados = [puerto.segmentar(texto) for _ in range(pasadas)]
    conteo = Counter(_firma(s) for s in resultados)
    firma_ganadora, votos = conteo.most_common(1)[0]
    ganadora = next(s for s in resultados if _firma(s) == firma_ganadora)
    for e in ganadora.elementos:
        e.votos = votos
    return ganadora
