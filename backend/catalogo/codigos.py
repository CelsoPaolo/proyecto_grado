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

Desde la v1.5 genera tambien los **codigos de unidad** (RN-VEN-18,
plan.md 3.6): el mismo formato con el prefijo 21 y su propia secuencia,
`unidad_codigo_seq`. Los dos prefijos son del rango 20-29 de GS1, asi
que ninguno coincide con un codigo de fabrica real, y entre ellos no se
confunden nunca.
"""

import re

PREFIJO_INTERNO = "20"
SECUENCIA = "producto_codigo_seq"
CIFRAS_DE_SECUENCIA = 10

#: Forma de un codigo interno. El codigo de fabrica no puede tenerla
#: (RN-CAT-11): asi una lectura identifica siempre a un solo producto.
PATRON_INTERNO = re.compile(r"^20[0-9]{11}$")

#: RN-VEN-18 y RF-102 (v1.5): el codigo de cada unidad vendida.
PREFIJO_UNIDAD = "21"
SECUENCIA_UNIDAD = "unidad_codigo_seq"
PATRON_UNIDAD = re.compile(r"^21[0-9]{11}$")


def normalizar_codigo_fabrica(texto):
    """RN-CAT-11 — sin espacios y en mayusculas.

    No se valida el formato: puede ser EAN-13, UPC-A de 12 cifras, EAN-8
    o un Code128 alfanumerico, y exigir uno solo dejaria fuera mercaderia
    real (plan.md 3.5). Normalizar si hace falta: el mismo codigo
    tecleado con un espacio o en minusculas debe ser el mismo codigo.
    """
    return "".join((texto or "").split()).upper()


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


def codigo_para(numero, prefijo=PREFIJO_INTERNO):
    """El codigo que corresponde al numero n de la secuencia.

    Por defecto, el interno de un producto; con `PREFIJO_UNIDAD`, el de
    una unidad vendida.
    """
    if not 1 <= numero < 10**CIFRAS_DE_SECUENCIA:
        raise ValueError(f"Numero de secuencia fuera de rango: {numero}.")
    doce = f"{prefijo}{numero:0{CIFRAS_DE_SECUENCIA}d}"
    return doce + str(calcular_digito_control(doce))


def siguiente_numero(connection, secuencia=SECUENCIA):
    """Pide el siguiente numero a la secuencia de la base."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s)", [secuencia])
        return cursor.fetchone()[0]


def generar_codigo(connection=None):
    """RF-69 — un codigo nuevo, nunca usado antes."""
    if connection is None:
        from django.db import connection
    return codigo_para(siguiente_numero(connection))


def generar_codigos_de_unidad(cantidad, connection=None):
    """RF-102 — `cantidad` codigos de unidad nuevos, en una sola consulta.

    Una venta de 7 unidades pide 7 numeros de una vez, no 7 viajes a la
    base. La secuencia los entrega distintos aunque dos ventas los pidan
    a la vez, y no los devuelve nunca otra vez, ni si la venta se
    revierte: un codigo de unidad no se reutiliza (RN-VEN-18).
    """
    if cantidad < 1:
        return []
    if connection is None:
        from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT nextval(%s) FROM generate_series(1, %s)",
            [SECUENCIA_UNIDAD, cantidad],
        )
        numeros = [fila[0] for fila in cursor.fetchall()]
    return [codigo_para(n, PREFIJO_UNIDAD) for n in numeros]
