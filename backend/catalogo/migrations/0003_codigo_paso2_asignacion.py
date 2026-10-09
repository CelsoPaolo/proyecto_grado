"""T-9.2 — Paso 2 de 3 del codigo de producto (plan.md 3.5, RNF-29).

Asigna un codigo interno a cada producto que no lo tiene, recorriendolos
por `id` ascendente para que el orden sea reproducible: el producto mas
antiguo recibe el primer numero libre de la secuencia.

Es idempotente: solo toca los que tienen el codigo nulo.

El reverso NO borra los codigos (plan.md 3.5, revisado el 2026-10-09).
Si los borrara, volver a aplicar este paso daria a cada producto un
codigo DISTINTO del que ya tenia, y las etiquetas impresas dejarian de
corresponder (RN-CAT-08: el codigo no cambia nunca). Revertir los tres
pasos sigue devolviendo la tabla a su estado anterior: el paso 1 elimina
la columna entera.

Las funciones de catalogo.codigos no importan modelos, por eso la
migracion puede usarlas: son las mismas que asignan el codigo al crear.
"""

from django.db import migrations

from catalogo.codigos import codigo_para, siguiente_numero


def asignar_codigos(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    conexion = schema_editor.connection
    for producto in Producto.objects.filter(codigo__isnull=True).order_by("id").only("id"):
        Producto.objects.filter(pk=producto.pk).update(
            codigo=codigo_para(siguiente_numero(conexion))
        )


class Migration(migrations.Migration):
    dependencies = [
        ("catalogo", "0002_codigo_paso1_secuencia_y_columna"),
    ]

    operations = [
        migrations.RunPython(asignar_codigos, reverse_code=migrations.RunPython.noop),
    ]
