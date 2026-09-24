"""Ajustes de desarrollo.

Unico entorno implementado (decision PT-01): el sistema se ejecuta en
el equipo del autor para la defensa del proyecto. El README documenta
lo que haria falta para un despliegue real, sin implementarlo.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = env.bool("DEBUG", default=True)

# Django sirve los archivos subidos (imagenes de producto) en
# desarrollo; en produccion lo haria el servidor web.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

# Mensajes de error completos en consola durante el desarrollo.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
