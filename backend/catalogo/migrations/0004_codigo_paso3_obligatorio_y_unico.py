"""T-9.2 — Paso 3 de 3 del codigo de producto (plan.md 3.5, RNF-29).

Impone NOT NULL y UNIQUE ahora que el paso 2 ha asignado un codigo a
cada producto. Si quedara alguno sin codigo, la base rechazaria el NOT
NULL y la migracion fallaria entera, sin dejar la tabla a medias.

Reverso: vuelve a admitir nulos y quita la unicidad; los codigos quedan
donde estaban.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalogo", "0003_codigo_paso2_asignacion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="producto",
            name="codigo",
            field=models.CharField(
                editable=False,
                help_text="EAN-13 interno asignado por el sistema (RN-CAT-08).",
                max_length=13,
                unique=True,
                verbose_name="código",
            ),
        ),
    ]
