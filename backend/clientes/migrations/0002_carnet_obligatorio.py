"""T-15.9 — Carnet obligatorio de 7 u 8 digitos (RF-101, RN-CLI-02).

Hace obligatorio el carnet, cambia su unicidad de parcial a total y
anade las restricciones de formato del carnet y del telefono. Estas SI
comprueban todas las filas (plan.md 3.6): se aplico solo despues de que
el propietario corrigiera los clientes que incumplian y de volver a
comprobarlo (plan.md 11.5). La migracion no corrige ningun dato.

Reverso: vuelve a la unicidad parcial y quita las restricciones de
formato (RNF-29); los carnets se conservan tal cual.
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='cliente',
            name='cliente_carnet_unico',
        ),
        migrations.AlterField(
            model_name='cliente',
            name='carnet',
            field=models.CharField(help_text='7 u 8 dígitos. Dato personal: solo visible en el detalle (RN-CLI-06).', max_length=20, verbose_name='carnet de identidad'),
        ),
        migrations.AddConstraint(
            model_name='cliente',
            constraint=models.UniqueConstraint(fields=('carnet',), name='cliente_carnet_unico', violation_error_message='Ya hay un cliente registrado con ese carnet.'),
        ),
        migrations.AddConstraint(
            model_name='cliente',
            constraint=models.CheckConstraint(condition=models.Q(('carnet__regex', '^[0-9]{7,8}$')), name='cliente_carnet_formato', violation_error_message='El carnet debe tener 7 u 8 dígitos, solo números.'),
        ),
        migrations.AddConstraint(
            model_name='cliente',
            constraint=models.CheckConstraint(condition=models.Q(('telefono__regex', '^[0-9]{8}$')), name='cliente_telefono_formato', violation_error_message='El teléfono debe tener exactamente 8 dígitos, solo números.'),
        ),
    ]
