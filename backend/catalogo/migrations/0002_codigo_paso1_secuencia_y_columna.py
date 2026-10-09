"""T-9.1 — Paso 1 de 3 del codigo de producto (plan.md 3.5, RNF-29).

Crea la secuencia y la columna `codigo`, todavia NULA: una columna NOT
NULL UNIQUE no puede anadirse de golpe a una tabla con filas. El paso 2
(T-9.2) asigna un codigo a cada producto existente y el paso 3 impone
NOT NULL y UNIQUE.

Reverso: elimina la columna y la secuencia.
"""

from django.db import migrations, models

CREAR_SECUENCIA = """
CREATE SEQUENCE producto_codigo_seq
    START WITH 1 MINVALUE 1 MAXVALUE 9999999999 NO CYCLE
"""
# MAXVALUE: el codigo tiene diez cifras de secuencia. Al agotarlas, la
# base da un error en lugar de reiniciar y repetir codigos (NO CYCLE).


class Migration(migrations.Migration):
    dependencies = [
        ("catalogo", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREAR_SECUENCIA,
            reverse_sql="DROP SEQUENCE producto_codigo_seq",
        ),
        migrations.AddField(
            model_name="producto",
            name="codigo",
            field=models.CharField(
                editable=False,
                help_text="EAN-13 interno asignado por el sistema (RN-CAT-08).",
                max_length=13,
                null=True,
                verbose_name="código",
            ),
        ),
    ]
