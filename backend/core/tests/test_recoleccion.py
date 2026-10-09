"""Guardian de la recoleccion de pruebas.

`pytest.ini` enumera a mano las apps en `testpaths`. Al crear la app
`inventario` (T-8.1) nadie la anadio, y la suite completa se ejecuto
durante dos tareas SIN sus 43 pruebas: pasaban, pero solo cuando se
lanzaban aparte. Un fallo en ellas no habria aparecido en ninguna
ejecucion completa.

Este guardian hace que no vuelva a pasar: toda app del proyecto que
tenga carpeta `tests/` debe estar en `testpaths`.
"""

import configparser
from pathlib import Path

from django.conf import settings

BACKEND = Path(settings.BASE_DIR)


def _testpaths():
    ini = configparser.ConfigParser()
    ini.read(BACKEND / "pytest.ini", encoding="utf-8")
    return set(ini["pytest"]["testpaths"].split())


def _apps_propias_con_pruebas():
    """Las apps de INSTALLED_APPS que viven en este repositorio y tienen
    pruebas. Las de Django y de terceros no tienen carpeta aqui."""
    return {
        app
        for app in settings.INSTALLED_APPS
        if "." not in app and (BACKEND / app / "tests").is_dir()
    }


def test_toda_app_con_pruebas_esta_en_testpaths():
    faltan = sorted(_apps_propias_con_pruebas() - _testpaths())

    assert not faltan, (
        f"Estas apps tienen pruebas pero no estan en `testpaths` de "
        f"pytest.ini, asi que la suite completa no las ejecuta: {faltan}"
    )


def test_testpaths_no_apunta_a_carpetas_inexistentes():
    """El reverso: una app renombrada o borrada dejaria una ruta muerta."""
    muertas = sorted(p for p in _testpaths() if not (BACKEND / p).is_dir())

    assert not muertas, f"testpaths incluye carpetas que no existen: {muertas}"
