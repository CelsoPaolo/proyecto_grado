"""T-15.5 — Codigo por unidad (RN-VEN-18, RF-102, plan.md 3.6).

Crea la secuencia `unidad_codigo_seq` y la tabla `UnidadVendida`. Nace
vacia: las ventas anteriores no reciben codigos de unidad (RNF-30), asi
que no hay migracion de datos.

Reverso: elimina la tabla y la secuencia (RNF-29).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0004_telefono_formato'),
    ]

    operations = [
        # Mismo criterio que producto_codigo_seq (catalogo/0002): diez
        # cifras de secuencia y error al agotarlas, nunca reinicio.
        migrations.RunSQL(
            sql=(
                "CREATE SEQUENCE unidad_codigo_seq "
                "START WITH 1 MINVALUE 1 MAXVALUE 9999999999 NO CYCLE"
            ),
            reverse_sql="DROP SEQUENCE unidad_codigo_seq",
        ),
        migrations.CreateModel(
            name='UnidadVendida',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(editable=False, max_length=13, unique=True, verbose_name='código de unidad')),
                ('anulada', models.BooleanField(default=False, verbose_name='anulada')),
                ('detalle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unidades', to='ventas.detalleventa', verbose_name='línea de la venta')),
            ],
            options={
                'verbose_name': 'unidad vendida',
                'verbose_name_plural': 'unidades vendidas',
                'ordering': ['id'],
                'constraints': [models.CheckConstraint(condition=models.Q(('codigo__regex', '^21[0-9]{11}$')), name='unidad_codigo_formato', violation_error_message='El código de unidad debe tener 13 dígitos y empezar por 21.')],
            },
        ),
    ]
