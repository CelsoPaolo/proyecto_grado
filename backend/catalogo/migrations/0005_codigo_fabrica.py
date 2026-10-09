"""T-9.7 — Codigo de fabrica opcional (RN-CAT-11, PA-07, plan.md 3.5).

Un campo nuevo con valor por defecto vacio: no hay datos que
transformar. Reversible: el reverso quita las dos restricciones y la
columna (RNF-29).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0004_codigo_paso3_obligatorio_y_unico'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='codigo_fabrica',
            field=models.CharField(blank=True, default='', help_text='Opcional: el código que trae impreso el producto o su caja (RN-CAT-11).', max_length=50, verbose_name='código de fábrica'),
        ),
        migrations.AddConstraint(
            model_name='producto',
            constraint=models.UniqueConstraint(condition=models.Q(('codigo_fabrica', ''), _negated=True), fields=('codigo_fabrica',), name='producto_codigo_fabrica_unico', violation_error_message='Ya hay otro producto con ese código de fábrica.'),
        ),
        migrations.AddConstraint(
            model_name='producto',
            constraint=models.CheckConstraint(condition=models.Q(('codigo_fabrica__regex', '^20[0-9]{11}$'), _negated=True), name='producto_codigo_fabrica_fuera_del_interno', violation_error_message='Un código de fábrica no puede tener la forma de un código interno.'),
        ),
    ]
