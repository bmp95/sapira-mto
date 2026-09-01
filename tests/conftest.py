"""Los tests marcados @pytest.mark.red llaman de verdad a una API externa (Gemini): cuestan
dinero, tiempo y necesitan red y clave. No corren en una pasada normal -- solo con `--red`."""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--red", action="store_true", default=False,
        help="Ejecuta tambien los tests marcados @pytest.mark.red (llaman a APIs reales).")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--red"):
        return
    saltar = pytest.mark.skip(reason="marcado @pytest.mark.red: pasa --red para ejecutarlo")
    for item in items:
        if "red" in item.keywords:
            item.add_marker(saltar)
