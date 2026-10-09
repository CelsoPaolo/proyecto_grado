"""T-10.1 — Meses de garantia del producto (RN-CAT-09, RF-72).

Campo nuevo con cero por defecto: los productos existentes quedan sin
garantia hasta que el Administrador la indique. Reversible (RNF-29).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0005_codigo_fabrica'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='meses_garantia',
            field=models.IntegerField(default=0, help_text='0 = sin garantía (RN-CAT-09).', verbose_name='meses de garantía'),
        ),
        migrations.AddConstraint(
            model_name='producto',
            constraint=models.CheckConstraint(condition=models.Q(('meses_garantia__gte', 0)), name='producto_meses_garantia_no_negativos', violation_error_message='Los meses de garantía no pueden ser negativos.'),
        ),
    ]
