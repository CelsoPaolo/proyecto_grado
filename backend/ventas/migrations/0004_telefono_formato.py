"""T-15.3 — Formato del telefono en las ventas NUEVAS (RF-100, RNF-30).

La venta guarda su copia del telefono del cliente: vacia (cliente
ocasional sin telefono, RN-VEN-10) o de 8 digitos (RN-CLI-09).

La regla rige solo para las ventas registradas despues de esta
migracion. `ADD CONSTRAINT ... NOT VALID` no basta: PostgreSQL no
revisa las filas existentes al crearla, pero si cada vez que una de
ellas se actualiza, y anular una venta antigua con un telefono fuera de
formato fallaria (plan.md 3.6). Por eso la condicion deja fuera, por su
id, a las ventas que ya existian al migrar.

El numero es propio de cada base, asi que esta restriccion no se declara
en `Venta.Meta.constraints`: solo vive aqui.

Reverso: elimina la restriccion (RNF-29). No toca ningun dato.
"""

from django.db import migrations

NOMBRE = "venta_telefono_formato"


def crear(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM ventas_venta")
        ultimo = int(cursor.fetchone()[0])
        cursor.execute(
            f"ALTER TABLE ventas_venta ADD CONSTRAINT {NOMBRE} CHECK ("
            f"id <= {ultimo} OR cliente_telefono = '' "
            f"OR cliente_telefono ~ '^[0-9]{{8}}$')"
        )


def eliminar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE ventas_venta DROP CONSTRAINT IF EXISTS {NOMBRE}")


class Migration(migrations.Migration):
    dependencies = [
        ("ventas", "0003_cliente_registrado"),
    ]

    operations = [
        migrations.RunPython(crear, eliminar),
    ]
