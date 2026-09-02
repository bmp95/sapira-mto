"""Tipos del dominio. El estado nunca se escribe: se deriva de la confianza."""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, model_validator

ATRIBUTOS = ("nombre", "material", "calidad", "medida", "longitud", "norma", "acabado")


class Procedencia(str, Enum):
    EXTRAIDO = "EXTRAIDO"
    DERIVADO = "DERIVADO"
    HEREDADO = "HEREDADO"
    INFERIDO = "INFERIDO"
    AUSENTE = "AUSENTE"


class Estado(str, Enum):
    RESUELTA = "RESUELTA"
    REVISION_MANUAL = "REVISION_MANUAL"


PUNTOS_PROCEDENCIA = {
    Procedencia.EXTRAIDO: 100,
    Procedencia.DERIVADO: 100,
    # Una respuesta humana con clave exacta vale lo mismo que un dato escrito:
    # no la esta suponiendo el sistema, la contesto una persona con autoridad.
    Procedencia.HEREDADO: 100,
    Procedencia.INFERIDO: 70,
}


class Valor(BaseModel):
    valor: Optional[str] = None
    literal: Optional[str] = None
    span: Optional[tuple[int, int]] = None
    procedencia: Procedencia
    regla: Optional[str] = None
    confianza: Optional[int] = None
    factores: dict[str, int] = {}

    @model_validator(mode="after")
    def _exige_evidencia(self):
        if self.procedencia is Procedencia.EXTRAIDO and self.span is None:
            raise ValueError("un valor EXTRAIDO necesita span")
        # DERIVADO guarda la regla que lo dedujo; HEREDADO, el puntero al
        # registro historico (quien contesto y cuando). Sin ese puntero un
        # valor heredado es inauditable, que es justo lo que no puede pasar.
        if self.procedencia is Procedencia.DERIVADO and not self.regla:
            raise ValueError("un valor DERIVADO necesita regla")
        if self.procedencia is Procedencia.HEREDADO and not self.regla:
            raise ValueError("un valor HEREDADO necesita regla con su origen")
        return self

    @property
    def confianza_procedencia(self) -> Optional[int]:
        return PUNTOS_PROCEDENCIA.get(self.procedencia)


class Elemento(BaseModel):
    tipo_indicado: str
    span: tuple[int, int]
    votos: int = 3


class Segmentacion(BaseModel):
    elementos: list[Elemento]
    ambito_fila: list[tuple[int, int]] = []
    conectores: list[tuple[int, int]] = []


class Motivo(BaseModel):
    codigo: str
    texto: str
    atributo: Optional[str] = None
    valor_propuesto: Optional[str] = None
    factor_limitante: Optional[str] = None


class LineaSalida(BaseModel):
    id: str
    fila_origen: int
    cantidad: int
    nombre: Valor
    material: Valor
    calidad: Valor
    medida: Valor
    longitud: Valor
    norma: Valor
    acabado: Valor
    confianza: int = 0
    motivos: list[Motivo] = []
    # De que tramo del texto original salio esta linea, para el panel de
    # traza del front: `texto_origen` es la descripcion saneada de la fila
    # completa (todas las lineas de una misma fila comparten el mismo
    # texto), `tramo` es el span de ESTE elemento dentro de ese texto --
    # None cuando la fila entera fue a revision antes de segmentarse (una
    # invariante rota o una excepcion) y no hay tramo de elemento que
    # resaltar. Ambos con default para no romper ningun constructor
    # existente (LineaSalida.vacia() y los tests que la usan): es aditivo.
    texto_origen: str = ""
    tramo: Optional[tuple[int, int]] = None

    @classmethod
    def vacia(cls, id: str, fila_origen: int, cantidad: int) -> "LineaSalida":
        hueco = Valor(procedencia=Procedencia.AUSENTE)
        return cls(id=id, fila_origen=fila_origen, cantidad=cantidad,
                   **{a: hueco.model_copy() for a in ATRIBUTOS})

    @property
    def estado(self) -> Estado:
        return Estado.RESUELTA if self.confianza == 100 else Estado.REVISION_MANUAL

    def celdas(self) -> dict[str, Valor]:
        return {a: getattr(self, a) for a in ATRIBUTOS}
