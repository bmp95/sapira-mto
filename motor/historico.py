"""Tarea 18: el historico de respuestas (spec.md seccion 13).

El argumento de negocio no es la lectura del MTO, es no repetir la pregunta.
La misma arandela sin dureza aparece en la revision 9, en la 12 y en la 15:
hoy se consulta a ingenieria las tres veces, porque la respuesta no se
guarda contra una identidad estable. Con clave canonica exacta se pregunta
una vez y las otras revisiones la heredan.

Cuatro reglas que no se negocian (todas de la seccion 13 del spec):

1. Coincidencia EXACTA de tupla. La clave son los seis atributos restantes
   -- los siete de ATRIBUTOS menos el que se pregunta -- ya normalizados,
   ordenados, con el literal AUSENTE para los que no tienen valor. Cero
   coincidencia difusa: un solo atributo distinto es otra pregunta.
2. Conflicto significa no heredar. Dos respuestas con valores distintos
   para la misma clave no dejan heredar ninguna: la busqueda devuelve
   CONFLICTO con las dos candidatas y valor None. Un historico que se
   contradice es peor que uno vacio. Dos respuestas con el MISMO valor no
   son conflicto.
3. Sin sugerencias. Si no hay coincidencia exacta, NINGUNA -- nunca "el
   mas parecido". Eso seria colar la coincidencia difusa por la puerta de
   atras.
4. Toda respuesta identifica quien y cuando: autor, origen, fecha, MTO de
   origen y revision de origen. Una respuesta anonima es inauditable.

Este modulo es solo el almacen -- registrar, buscar, persistir. Integrarlo
en el pipeline (para que una linea sin calidad consulte aqui antes de ir a
revision) es la Tarea 19, igual que la quinta procedencia HEREDADO y el
arreglo del span fabricado en api/servidor.py._resolver_celda. Cuando esa
tarea escriba el registro que nace de que una persona resuelve una celda en
el front, es un RespuestaHistorica lo que debe crear.
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from motor.modelos import ATRIBUTOS, LineaSalida

AUSENTE = "AUSENTE"

# Tupla ordenada de pares (atributo, valor): la identidad canonica de una
# pieza para un atributo dado, sin el atributo que se esta preguntando.
ClaveCanonica = tuple[tuple[str, str], ...]


def clave_de(linea: LineaSalida, atributo: str) -> ClaveCanonica:
    """Los seis atributos de ATRIBUTOS que NO son `atributo`, normalizados
    y ordenados por nombre para que la igualdad de tupla sea estable. El
    que no tiene valor entra como AUSENTE -- nunca se omite, porque un
    atributo ausente y uno con valor son piezas distintas."""
    restantes = sorted(a for a in ATRIBUTOS if a != atributo)
    pares = []
    for nombre in restantes:
        celda = getattr(linea, nombre)
        pares.append((nombre, celda.valor if celda.valor is not None else AUSENTE))
    return tuple(pares)


class RespuestaHistorica(BaseModel):
    """Una respuesta humana con autoridad, sobre una clave canonica exacta.
    Sin autor ni fecha no es auditable y no vale (regla 4): por eso los
    cinco campos de identidad son obligatorios, sin default."""
    clave: ClaveCanonica
    atributo: str
    valor: str
    autor: str
    origen: str
    fecha: str
    mto_origen: str
    revision_origen: str


class Hallazgo(str, Enum):
    UNICA = "UNICA"
    NINGUNA = "NINGUNA"
    CONFLICTO = "CONFLICTO"


class ResultadoBusqueda(BaseModel):
    hallazgo: Hallazgo
    valor: str | None = None
    respuesta: RespuestaHistorica | None = None
    candidatas: list[RespuestaHistorica] = []


class Historico:
    """El almacen. Indexado por (clave, atributo) -- la clave por si sola ya
    excluye el atributo preguntado, pero el par se guarda explicito para que
    la busqueda no dependa de esa propiedad implicita."""

    def __init__(self) -> None:
        self._registros: dict[tuple[ClaveCanonica, str], list[RespuestaHistorica]] = {}

    def registrar(self, respuesta: RespuestaHistorica) -> None:
        llave = (respuesta.clave, respuesta.atributo)
        self._registros.setdefault(llave, []).append(respuesta)

    def buscar(self, clave: ClaveCanonica, atributo: str) -> ResultadoBusqueda:
        registros = self._registros.get((clave, atributo), [])
        if not registros:
            return ResultadoBusqueda(hallazgo=Hallazgo.NINGUNA)

        valores_distintos = {r.valor for r in registros}
        if len(valores_distintos) > 1:
            # Regla 2: dos respuestas en conflicto no heredan ninguna.
            return ResultadoBusqueda(hallazgo=Hallazgo.CONFLICTO, candidatas=list(registros))

        mas_reciente = registros[-1]
        return ResultadoBusqueda(hallazgo=Hallazgo.UNICA, valor=mas_reciente.valor,
                                 respuesta=mas_reciente)

    def guardar(self, ruta: str | Path) -> None:
        """La clave se serializa como lista de pares -- pydantic ya convierte
        cada tupla en una lista JSON al volcar el modelo."""
        todos = [r for registros in self._registros.values() for r in registros]
        datos = [r.model_dump(mode="json") for r in todos]
        Path(ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def cargar(cls, ruta: str | Path) -> Historico:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
        historico = cls()
        for item in datos:
            historico.registrar(RespuestaHistorica.model_validate(item))
        return historico
