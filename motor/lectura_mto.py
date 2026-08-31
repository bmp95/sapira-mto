"""xlsx -> filas. La cabecera esta en la fila 4; los datos empiezan en la 5."""
from pathlib import Path
from pydantic import BaseModel
import openpyxl
from motor.saneado import sanear


class FilaMTO(BaseModel):
    item: int
    descripcion: str
    material_col: str
    medida_col: str
    cantidad: int
    unidad: str


def leer_mto(ruta: Path) -> list[FilaMTO]:
    hoja = openpyxl.load_workbook(ruta, data_only=True).worksheets[0]
    filas: list[FilaMTO] = []
    for f in hoja.iter_rows(min_row=5, values_only=True):
        if f[0] is None:
            continue
        filas.append(FilaMTO(
            item=int(f[0]),
            descripcion=sanear(str(f[1] or "")),
            material_col=sanear(str(f[2] or "")),
            medida_col=sanear(str(f[3] or "")),
            cantidad=int(f[4] or 0),
            unidad=str(f[5] or ""),
        ))
    return filas
