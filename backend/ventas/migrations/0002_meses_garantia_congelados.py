"""T-10.1 — Meses de garantia congelados en la linea de venta (RN-VEN-12).

Las lineas existentes quedan en CERO, no con los meses actuales de su
producto: asignarles una garantia hoy seria inventar un dato que no
existia cuando se vendio (plan.md 3.5). Reversible (RNF-29).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0006_meses_garantia'),
        ('ventas', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='detalleventa',
            name='meses_garantia',
            field=models.IntegerField(default=0, help_text='Congelado al confirmar la venta (RN-VEN-12).', verbose_name='meses de garantía'),
        ),
        migrations.AddConstraint(
            model_name='detalleventa',
            constraint=models.CheckConstraint(condition=models.Q(('meses_garantia__gte', 0)), name='detalle_meses_garantia_no_negativos', violation_error_message='Los meses de garantía no pueden ser negativos.'),
        ),
    ]
