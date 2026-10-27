"""T-15.3 — Formato del telefono en las solicitudes NUEVAS (RF-100, RNF-30).

El telefono de contacto de una solicitud tiene 8 digitos (RN-SER-05,
RN-CLI-09), solo en las solicitudes registradas despues de esta
migracion.

Mismo razonamiento que ventas/0004_telefono_formato: una restriccion
`NOT VALID` se vuelve a comprobar al actualizar una fila antigua, y una
solicitud abierta se actualiza en cada cambio de estado y al cotizarla.
Hay solicitudes anteriores con telefonos fuera de formato que deben
poder seguir atendiendose (plan.md 3.6).

No se declara en `SolicitudServicio.Meta.constraints`: el numero es
propio de cada base.

Reverso: elimina la restriccion (RNF-29). No toca ningun dato.
"""

from django.db import migrations

NOMBRE = "solicitud_telefono_formato"


def crear(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM servicios_solicitudservicio")
        ultimo = int(cursor.fetchone()[0])
        cursor.execute(
            f"ALTER TABLE servicios_solicitudservicio ADD CONSTRAINT {NOMBRE} CHECK ("
            f"id <= {ultimo} OR cliente_telefono ~ '^[0-9]{{8}}$')"
        )


def eliminar(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"ALTER TABLE servicios_solicitudservicio DROP CONSTRAINT IF EXISTS {NOMBRE}"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("servicios", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear, eliminar),
    ]
