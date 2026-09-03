"""Carga el gold set anotado a mano (Tarea 11) desde el xlsx.

La hoja se llama "gold" y cada fila del xlsx es una linea del gold set (no
una fila del MTO: una fila del MTO puede dar varias lineas). Las columnas
relevantes, por indice fijo (spec de la Tarea 12): A=id, B=fila del MTO,
G=nombre, H=conf, I=cantidad, J=material, K=conf, L=calidad, M=conf,
N=medida, O=conf, P=longitud, Q=conf, R=norma, S=conf, T=acabado, U=conf.

Este modulo solo carga: no normaliza valores ni decide que cuenta como
hueco. Esa normalizacion es responsabilidad de `evaluacion.arnes`, que es
quien compara -- cargar_gold se limita a ser fiel al xlsx.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

import openpyxl
from pydantic import BaseModel

from motor.modelos import ATRIBUTOS

HOJA = "gold"

COL_ID = 1
COL_FILA = 2
COL_NOMBRE = 7
COL_CONF_NOMBRE = 8
COL_CANTIDAD = 9
COL_MATERIAL = 10
COL_CONF_MATERIAL = 11
COL_CALIDAD = 12
COL_CONF_CALIDAD = 13
COL_MEDIDA = 14
COL_CONF_MEDIDA = 15
COL_LONGITUD = 16
COL_CONF_LONGITUD = 17
COL_NORMA = 18
COL_CONF_NORMA = 19
COL_ACABADO = 20
COL_CONF_ACABADO = 21


class ConfianzaGold(str, Enum):
    CIERTA = "cierta"
    INTERPRETADA = "interpretada"
    INDECIDIBLE = "indecidible"


class LineaGold(BaseModel):
    id: str
    fila: int
    cantidad: int
    nombre: str
    conf_nombre: ConfianzaGold
    material: str | None = None
    conf_material: ConfianzaGold
    calidad: str | None = None
    conf_calidad: ConfianzaGold
    medida: str | None = None
    conf_medida: ConfianzaGold
    longitud: str | None = None
    conf_longitud: ConfianzaGold
    norma: str | None = None
    conf_norma: ConfianzaGold
    acabado: str | None = None
    conf_acabado: ConfianzaGold

    def celdas(self) -> dict[str, tuple[str | None, ConfianzaGold]]:
        """Un par (valor, confianza) por cada uno de los 7 atributos, en el
        mismo orden que `LineaSalida.celdas()` -- misma clave, misma tabla."""
        return {atributo: (getattr(self, atributo), getattr(self, f"conf_{atributo}"))
                for atributo in ATRIBUTOS}


def _texto(valor) -> str | None:
    return str(valor) if valor is not None else None


def cargar_gold(ruta: Path) -> list[LineaGold]:
    hoja = openpyxl.load_workbook(ruta, data_only=True)[HOJA]
    lineas: list[LineaGold] = []
    for fila_celdas in hoja.iter_rows(min_row=2):
        if fila_celdas[COL_ID - 1].value is None:
            continue
        lineas.append(LineaGold(
            id=str(fila_celdas[COL_ID - 1].value),
            fila=int(fila_celdas[COL_FILA - 1].value),
            cantidad=int(fila_celdas[COL_CANTIDAD - 1].value),
            nombre=str(fila_celdas[COL_NOMBRE - 1].value),
            conf_nombre=fila_celdas[COL_CONF_NOMBRE - 1].value,
            material=_texto(fila_celdas[COL_MATERIAL - 1].value),
            conf_material=fila_celdas[COL_CONF_MATERIAL - 1].value,
            calidad=_texto(fila_celdas[COL_CALIDAD - 1].value),
            conf_calidad=fila_celdas[COL_CONF_CALIDAD - 1].value,
            medida=_texto(fila_celdas[COL_MEDIDA - 1].value),
            conf_medida=fila_celdas[COL_CONF_MEDIDA - 1].value,
            longitud=_texto(fila_celdas[COL_LONGITUD - 1].value),
            conf_longitud=fila_celdas[COL_CONF_LONGITUD - 1].value,
            norma=_texto(fila_celdas[COL_NORMA - 1].value),
            conf_norma=fila_celdas[COL_CONF_NORMA - 1].value,
            acabado=_texto(fila_celdas[COL_ACABADO - 1].value),
            conf_acabado=fila_celdas[COL_CONF_ACABADO - 1].value,
        ))
    return lineas
