"""Codigo interno de producto en EAN-13 (RN-CAT-08, RF-69, plan.md 3.5).

    2 0 | 0 0 0 0 0 0 0 1 4 7 | 0      <- producto n.o 147
    GS1 | secuencia, 10 cifras | control

- Prefijo 20: GS1 reserva 20-29 para circulacion restringida, es decir,
  codigos que un comercio asigna para uso interno. Ningun fabricante
  puede tener uno, asi que el codigo interno nunca coincide con el de
  una caja real (RN-CAT-11).
- Secuencia PostgreSQL propia (`producto_codigo_seq`), no la clave
  primaria: el codigo se conoce antes de insertar, y una secuencia
  nunca devuelve dos veces el mismo numero, ni aunque la transaccion
  que lo pidio se revierta. Eso es literalmente «no se reutiliza».
- Digito de control EAN-13: sin el, un lector estandar rechaza la
  etiqueta impresa.

Este modulo no importa modelos: la migracion que asigna codigos a los
productos existentes (T-9.2) usa las mismas funciones.
"""

import re

PREFIJO_INTERNO = "20"
SECUENCIA = "producto_codigo_seq"
CIFRAS_DE_SECUENCIA = 10

#: Forma de un codigo interno. El codigo de fabrica no puede tenerla
#: (RN-CAT-11): asi una lectura identifica siempre a un solo producto.
PATRON_INTERNO = re.compile(r"^20[0-9]{11}$")


def calcular_digito_control(doce_cifras):
    """Digito de control EAN-13 de las 12 primeras cifras.

    Suma ponderada alternando 1 y 3 desde la izquierda, y complemento a
    10 de esa suma.
    """
    if len(doce_cifras) != 12 or not doce_cifras.isdigit() or not doce_cifras.isascii():
        raise ValueError(f"Se esperaban 12 cifras, no {doce_cifras!r}.")
    suma = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(doce_cifras))
    return (10 - suma % 10) % 10


def es_ean13_valido(codigo):
    """13 cifras con el digito de control correcto."""
    return (
        isinstance(codigo, str)
        and len(codigo) == 13
        and codigo.isascii()
        and codigo.isdigit()
        and calcular_digito_control(codigo[:12]) == int(codigo[12])
    )


def codigo_para(numero):
    """El codigo interno que corresponde al numero n de la secuencia."""
    if not 1 <= numero < 10**CIFRAS_DE_SECUENCIA:
        raise ValueError(f"Numero de secuencia fuera de rango: {numero}.")
    doce = f"{PREFIJO_INTERNO}{numero:0{CIFRAS_DE_SECUENCIA}d}"
    return doce + str(calcular_digito_control(doce))


def siguiente_numero(connection):
    """Pide el siguiente numero a la secuencia de la base."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s)", [SECUENCIA])
        return cursor.fetchone()[0]


def generar_codigo(connection=None):
    """RF-69 — un codigo nuevo, nunca usado antes."""
    if connection is None:
        from django.db import connection
    return codigo_para(siguiente_numero(connection))
