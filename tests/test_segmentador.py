from motor.modelos import Elemento, Segmentacion
from motor.segmentador import segmentar_con_votacion


class PuertoGuion:
    """Devuelve una segmentacion distinta en cada pasada, segun guion."""
    def __init__(self, guion):
        self.guion, self.i = guion, 0

    def segmentar(self, texto):
        s = self.guion[self.i % len(self.guion)]
        self.i += 1
        return s

    def extraer(self, tramo):
        return []


def _seg(*tipos):
    return Segmentacion(elementos=[Elemento(tipo_indicado=t, span=(i, i + 1))
                                   for i, t in enumerate(tipos)])


def test_unanimidad_da_tres_votos():
    p = PuertoGuion([_seg("BOLT", "NUT")] * 3)
    r = segmentar_con_votacion(p, "x", pasadas=3)
    assert [e.votos for e in r.elementos] == [3, 3]


def test_dos_de_tres_baja_los_votos():
    p = PuertoGuion([_seg("BOLT", "NUT"), _seg("BOLT", "NUT"), _seg("BOLT")])
    r = segmentar_con_votacion(p, "x", pasadas=3)
    assert max(e.votos for e in r.elementos) == 2


def test_gana_la_segmentacion_mayoritaria():
    p = PuertoGuion([_seg("BOLT"), _seg("BOLT", "NUT"), _seg("BOLT", "NUT")])
    r = segmentar_con_votacion(p, "x", pasadas=3)
    assert [e.tipo_indicado for e in r.elementos] == ["BOLT", "NUT"]
