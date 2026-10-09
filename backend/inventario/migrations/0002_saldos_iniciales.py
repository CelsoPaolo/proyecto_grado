"""T-8.4 — Saldo inicial de los productos que ya existian (RN-MOV-02).

El libro de movimientos empieza a llevarse en la v1.4, pero los
productos ya tenian existencias. Esta migracion les da su punto de
partida: un movimiento SALDO_INICIAL, sin autor —lo crea el sistema, no
una persona—, para que a partir de aqui la suma de los movimientos de
cada producto sea su stock (RN-MOV-03).

Tres propiedades, todas probadas en inventario/tests/test_migracion_saldos.py:

  REVERSIBLE (RNF-29). El reverso borra las filas SALDO_INICIAL y nada
  mas: son las unicas que crea esta migracion, y ningun otro camino del
  sistema produce ese tipo.

  IDEMPOTENTE. Solo crea el saldo de los productos que aun no tienen un
  punto de partida en el libro. Aplicarla, revertirla y volver a
  aplicarla, o ejecutar la funcion dos veces, deja exactamente los
  mismos movimientos. Un producto creado despues de T-8.3 ya tiene su
  ALTA y no recibe un segundo origen: si lo recibiera, el libro contaria
  sus existencias dos veces.

  CUADRA AUNQUE HAYA VENTAS PREVIAS. Si un producto se vendio entre T-8.2
  y esta migracion, ya tiene movimientos VENTA sin origen. Su saldo es
  entonces el stock MENOS lo que ya suman esos movimientos, no el stock
  a secas: asi el libro cuadra igual.

Usa los modelos historicos (apps.get_model), no los de la aplicacion.
Por eso el reverso puede borrar: el queryset que impide reescribir el
libro (RN-MOV-04) pertenece al modelo de la aplicacion, y una migracion
es justamente quien tiene derecho a deshacer lo que ella misma creo.
"""

from django.db import migrations
from django.db.models import Sum

SALDO_INICIAL = "SALDO_INICIAL"
TIPOS_DE_ORIGEN = ("SALDO_INICIAL", "ALTA")
MOTIVO = "Saldo inicial al incorporar el historial de movimientos de stock."


class LibroInconsistente(Exception):
    """Un producto tiene movimientos que suman mas que su stock.

    No deberia ocurrir: el CHECK de existencias no negativas lo impide.
    Si ocurre, la migracion se detiene entera —corre en una transaccion—
    en lugar de inventar un saldo negativo que la base rechazaria de
    todos modos con un mensaje menos claro.
    """


def crear_saldos_iniciales(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    Movimiento = apps.get_model("inventario", "MovimientoStock")

    con_origen = set(
        Movimiento.objects.filter(tipo__in=TIPOS_DE_ORIGEN).values_list(
            "producto_id", flat=True
        )
    )
    ya_movido = dict(
        Movimiento.objects.values("producto_id")
        .annotate(total=Sum("cantidad"))
        .values_list("producto_id", "total")
    )

    saldos = []
    for producto in Producto.objects.order_by("id").only("id", "nombre", "stock"):
        if producto.id in con_origen:
            continue
        saldo = producto.stock - (ya_movido.get(producto.id) or 0)
        if saldo < 0:
            raise LibroInconsistente(
                f"El producto #{producto.id} «{producto.nombre}» tiene "
                f"{producto.stock} unidades, pero sus movimientos ya suman "
                f"{ya_movido[producto.id]}."
            )
        saldos.append(
            Movimiento(
                producto_id=producto.id,
                tipo=SALDO_INICIAL,
                cantidad=saldo,
                stock_resultante=saldo,
                usuario=None,
                venta=None,
                motivo=MOTIVO,
            )
        )

    Movimiento.objects.bulk_create(saldos, batch_size=500)


def borrar_saldos_iniciales(apps, schema_editor):
    Movimiento = apps.get_model("inventario", "MovimientoStock")
    Movimiento.objects.filter(tipo=SALDO_INICIAL).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0001_initial"),
        ("catalogo", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_saldos_iniciales, borrar_saldos_iniciales),
    ]
