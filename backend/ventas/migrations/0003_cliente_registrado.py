"""T-11.4 — Referencia opcional de la venta a su cliente registrado (RF-80).

Columna nula: las ventas existentes quedan como ventas a clientes
ocasionales, que es lo que fueron. Su nombre y telefono no cambian.
Reversible (RNF-29).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0001_initial'),
        ('ventas', '0002_meses_garantia_congelados'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='cliente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ventas', to='clientes.cliente', verbose_name='cliente registrado'),
        ),
    ]
