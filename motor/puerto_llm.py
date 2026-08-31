"""El proveedor vive detras de un puerto. Cambiar de modelo es un parametro."""
from typing import Protocol
from motor.modelos import Segmentacion


class PuertoLLM(Protocol):
    def segmentar(self, texto: str) -> Segmentacion: ...
    def extraer(self, tramo: str) -> list[dict]: ...


class PuertoFalso:
    """Segmentador de guion para tests y para el pipeline sin red."""
    def __init__(self, respuestas: dict[str, Segmentacion]):
        self.respuestas = respuestas

    def segmentar(self, texto: str) -> Segmentacion:
        if texto not in self.respuestas:
            raise KeyError(f"PuertoFalso sin guion para: {texto[:60]}")
        return self.respuestas[texto]

    def extraer(self, tramo: str) -> list[dict]:
        return []
