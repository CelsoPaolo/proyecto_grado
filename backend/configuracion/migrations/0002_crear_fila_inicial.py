"""Crea la fila unica de configuracion.

Va en una migracion de datos y no en codigo de arranque para que
cualquier base migrada tenga la configuracion desde el primer momento:
el catalogo la consulta en cada listado (RF-53) y el panel en cada
carga, asi que no puede faltar.
"""

from django.db import migrations

UMBRAL_INICIAL = 5


def crear_configuracion(apps, schema_editor):
    ConfiguracionSistema = apps.get_model("configuracion", "ConfiguracionSistema")
    ConfiguracionSistema.objects.get_or_create(
        pk=1, defaults={"umbral_stock_bajo": UMBRAL_INICIAL}
    )


def borrar_configuracion(apps, schema_editor):
    ConfiguracionSistema = apps.get_model("configuracion", "ConfiguracionSistema")
    ConfiguracionSistema.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0001_initial")]

    operations = [
        migrations.RunPython(crear_configuracion, borrar_configuracion),
    ]
