"""T-9.1 — Codigo EAN-13 interno (RN-CAT-08, RF-69).

Tres propiedades que una prueba puede romper:
  - el digito de control es el de EAN-13: se compara con codigos reales
    de cajas reales, no con valores calculados por el propio codigo;
  - el codigo no se edita: ni al crear ni al editar puede imponerlo la
    peticion, y guardar de nuevo un producto no lo cambia;
  - el codigo no se reutiliza: ni al retirar un producto ni cuando la
    transaccion que lo pidio se revierte.
"""

import pytest
from django.db import transaction
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.codigos import (
    PATRON_INTERNO,
    calcular_digito_control,
    codigo_para,
    es_ean13_valido,
)
from catalogo.models import Producto
from catalogo.services import crear_producto, retirar_producto
from catalogo.tests.factories import CategoriaFactory, ProductoFactory
from usuarios.tests.factories import AdministradorFactory

PRODUCTOS = "/api/v1/productos"


# ─────────────────────────────────────────────────────────────────────
# Digito de control (funcion pura)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "codigo_real",
    [
        "4006381333931",  # Stabilo, el ejemplo clasico de EAN-13
        "5901234123457",  # ejemplo de la especificacion GS1
        "9780306406157",  # ISBN-13
        "7501031311309",  # producto de Mexico
        "0012345678905",  # UPC-A 012345678905 como EAN-13
    ],
)
def test_el_digito_de_control_coincide_con_codigos_reales(codigo_real):
    assert calcular_digito_control(codigo_real[:12]) == int(codigo_real[12])
    assert es_ean13_valido(codigo_real)


@pytest.mark.parametrize("invalido", ["4006381333932", "400638133393", "40063813339311", "40063813339a1", ""])
def test_un_codigo_con_otro_control_o_longitud_no_es_valido(invalido):
    assert not es_ean13_valido(invalido)


@pytest.mark.parametrize("entrada", ["12345", "1234567890123", "12345678901a", "１２３４５６７８９０１２"])
def test_el_calculo_exige_doce_cifras_ascii(entrada):
    with pytest.raises(ValueError):
        calcular_digito_control(entrada)


def test_el_ejemplo_del_plan():
    """plan.md 3.5: el producto n.o 147."""
    assert codigo_para(147) == "2000000001470"


@pytest.mark.parametrize("numero", [0, -1, 10**10])
def test_fuera_del_rango_de_la_secuencia_es_un_error(numero):
    with pytest.raises(ValueError):
        codigo_para(numero)


# ─────────────────────────────────────────────────────────────────────
# Asignacion al crear
# ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def admin():
    return AdministradorFactory()


@pytest.fixture
def cliente(admin):
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": admin.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


def _alta(cliente, **extra):
    return cliente.post(
        PRODUCTOS,
        {
            "nombre": "Mouse inalámbrico",
            "descripcion": "",
            "precio": "85.00",
            "stock": 5,
            "categoria": CategoriaFactory().pk,
            **extra,
        },
        format="json",
    )


@pytest.mark.django_db
def test_un_producto_nuevo_recibe_un_ean13_interno_valido(cliente):
    respuesta = _alta(cliente)

    assert respuesta.status_code == status.HTTP_201_CREATED
    codigo = respuesta.data["codigo"]
    assert PATRON_INTERNO.match(codigo)
    assert es_ean13_valido(codigo)
    assert Producto.objects.get(pk=respuesta.data["id"]).codigo == codigo


@pytest.mark.django_db
def test_el_codigo_de_la_peticion_se_ignora_al_crear(cliente):
    respuesta = _alta(cliente, codigo="4006381333931")

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["codigo"] != "4006381333931"
    assert PATRON_INTERNO.match(respuesta.data["codigo"])


@pytest.mark.django_db
def test_el_codigo_de_la_peticion_se_ignora_al_editar(cliente):
    producto = ProductoFactory()
    original = producto.codigo

    respuesta = cliente.patch(
        f"{PRODUCTOS}/{producto.pk}",
        {"codigo": "2000000001470", "nombre": "Nombre corregido"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_200_OK
    producto.refresh_from_db()
    assert producto.nombre == "Nombre corregido"
    assert producto.codigo == original


@pytest.mark.django_db
def test_guardar_de_nuevo_un_producto_no_cambia_su_codigo():
    producto = ProductoFactory()
    original = producto.codigo

    producto.precio = 999
    producto.save()

    producto.refresh_from_db()
    assert producto.codigo == original


@pytest.mark.django_db
def test_retirar_un_producto_y_crear_otro_da_un_codigo_distinto(admin):
    viejo = ProductoFactory()
    retirar_producto(producto=viejo)

    nuevo = crear_producto(
        usuario=admin,
        nombre="Sucesor",
        descripcion="",
        precio=10,
        stock=0,
        categoria=viejo.categoria,
    )

    assert nuevo.codigo != viejo.codigo
    viejo.refresh_from_db()
    assert viejo.codigo  # el retirado conserva el suyo


@pytest.mark.django_db
def test_un_codigo_pedido_en_una_transaccion_revertida_no_se_reutiliza():
    """La secuencia de PostgreSQL no retrocede con el ROLLBACK. Un
    contador calculado desde la tabla (MAX + 1, COUNT + 1) si lo haria,
    y el siguiente producto heredaria el codigo de uno que llego a
    existir, por ejemplo, en una etiqueta impresa."""
    categoria = CategoriaFactory()

    class Revertir(Exception):
        pass

    with pytest.raises(Revertir):
        with transaction.atomic():
            perdido = ProductoFactory(categoria=categoria).codigo
            raise Revertir

    siguiente = ProductoFactory(categoria=categoria).codigo

    assert siguiente != perdido
    assert not Producto.objects.filter(codigo=perdido).exists()


@pytest.mark.django_db
def test_cien_productos_tienen_cien_codigos_distintos_y_validos():
    categoria = CategoriaFactory()
    codigos = [ProductoFactory(categoria=categoria).codigo for _ in range(100)]

    assert len(set(codigos)) == 100
    assert all(es_ean13_valido(c) and PATRON_INTERNO.match(c) for c in codigos)
