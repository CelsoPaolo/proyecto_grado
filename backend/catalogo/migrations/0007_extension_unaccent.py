"""T-15.1 — Extension `unaccent` de PostgreSQL (RF-98, plan.md 3.6).

La busqueda sin tildes de productos y clientes usa el lookup
`__unaccent`. Activar la extension en una migracion, y no a mano, hace
que la tenga tambien la base de pruebas y cualquier base restaurada.

`unaccent` es una extension de confianza desde PostgreSQL 13: la crea
el dueno de la base sin ser superusuario.

Reverso: elimina la extension (RNF-29). No hay datos que perder.
"""

from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalogo", "0006_meses_garantia"),
    ]

    operations = [
        UnaccentExtension(),
    ]
