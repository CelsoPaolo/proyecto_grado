"""T-9.7 — Codigo de fabrica opcional (RN-CAT-11, RF-97, PA-07).

Opcional, editable, unico si se informa y fuera del espacio de los
codigos internos. Las dos restricciones viven en la base y en el
serializer: la base para que nada las salte, el serializer para que el
error llegue junto al campo (RNF-15).
"""

import pytest
from django.db import IntegrityError, connection, transaction
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.models import Producto
from catalogo.tests.factories import CategoriaFactory, ProductoFactory
from usuarios.tests.factories import AdministradorFactory, VendedorFactory

pytestmark = pytest.mark.django_db

PRODUCTOS = "/api/v1/productos"


def _autenticar(usuario):
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


@pytest.fixture
def admin():
    return _autenticar(AdministradorFactory())


@pytest.fixture
def categoria():
    return CategoriaFactory()


def _alta(cliente, categoria, nombre="Mouse óptico", **extra):
    return cliente.post(
        PRODUCTOS,
        {
            "nombre": nombre,
            "descripcion": "",
            "precio": "45.00",
            "stock": 3,
            "categoria": categoria.pk,
            **extra,
        },
        format="json",
    )


# ─────────────────────────────────────────────────────────────────────
# Registrar, corregir y quitar (RF-97)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "codigo",
    ["7501031311309", "012345678905", "96385074", "ABC-123/X"],
    ids=["ean13", "upc-a", "ean8", "code128"],
)
def test_se_acepta_cualquier_formato_de_fabrica(admin, categoria, codigo):
    """plan.md 3.5: validar un solo formato dejaria fuera mercaderia real."""
    respuesta = _alta(admin, categoria, codigo_fabrica=codigo)

    assert respuesta.status_code == status.HTTP_201_CREATED, respuesta.data
    assert respuesta.data["codigo_fabrica"] == codigo


def test_se_normaliza_sin_espacios_y_en_mayusculas(admin, categoria):
    respuesta = _alta(admin, categoria, codigo_fabrica="  abc 123 x ")

    assert respuesta.data["codigo_fabrica"] == "ABC123X"


def test_dos_productos_sin_codigo_de_fabrica_conviven(admin, categoria):
    assert _alta(admin, categoria, nombre="Uno").status_code == 201
    assert _alta(admin, categoria, nombre="Dos", codigo_fabrica="").status_code == 201

    assert Producto.objects.filter(codigo_fabrica="").count() == 2


def test_se_puede_corregir_y_quitar(admin):
    producto = ProductoFactory(codigo_fabrica="7501031311309")

    corregido = admin.patch(f"{PRODUCTOS}/{producto.pk}", {"codigo_fabrica": "7501031311316"}, format="json")
    assert corregido.status_code == 200
    assert corregido.data["codigo_fabrica"] == "7501031311316"

    quitado = admin.patch(f"{PRODUCTOS}/{producto.pk}", {"codigo_fabrica": ""}, format="json")
    assert quitado.status_code == 200
    producto.refresh_from_db()
    assert producto.codigo_fabrica == ""


def test_guardar_un_producto_con_su_propio_codigo_no_es_un_duplicado(admin):
    producto = ProductoFactory(codigo_fabrica="7501031311309")

    respuesta = admin.patch(
        f"{PRODUCTOS}/{producto.pk}", {"codigo_fabrica": "7501031311309", "nombre": "Otro nombre"}, format="json"
    )

    assert respuesta.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# Rechazos junto al campo (RN-CAT-11)
# ─────────────────────────────────────────────────────────────────────
def test_un_codigo_repetido_se_rechaza_junto_al_campo_al_crear(admin, categoria):
    ProductoFactory(nombre="Teclado USB", codigo_fabrica="7501031311309")

    respuesta = _alta(admin, categoria, codigo_fabrica="7501031311309")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "Teclado USB" in respuesta.data["errores"]["codigo_fabrica"][0]


def test_un_codigo_repetido_se_rechaza_al_editar(admin):
    ProductoFactory(codigo_fabrica="ABC123")
    otro = ProductoFactory()

    respuesta = admin.patch(f"{PRODUCTOS}/{otro.pk}", {"codigo_fabrica": "abc 123"}, format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "codigo_fabrica" in respuesta.data["errores"]


def test_lo_repite_aunque_el_otro_producto_este_retirado(admin, categoria):
    """RN-CAT-11: unico entre activos y retirados."""
    ProductoFactory(codigo_fabrica="7501031311309", activo=False)

    respuesta = _alta(admin, categoria, codigo_fabrica="7501031311309")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize("codigo", ["2000000000015", "2012345678903", " 2000000000015 "])
def test_un_codigo_con_forma_de_interno_se_rechaza(admin, categoria, codigo):
    respuesta = _alta(admin, categoria, codigo_fabrica=codigo)

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "código interno" in respuesta.data["errores"]["codigo_fabrica"][0]


@pytest.mark.parametrize("codigo", ["200000000001", "20000000000155", "2100000000010"])
def test_lo_que_solo_se_parece_a_un_interno_se_acepta(admin, categoria, codigo):
    """Solo se prohibe exactamente la forma interna: 13 cifras que
    empiezan por 20. Doce cifras, catorce, o el prefijo 21, no."""
    assert _alta(admin, categoria, codigo_fabrica=codigo).status_code == 201


def test_el_encargado_de_ventas_no_lo_edita():
    producto = ProductoFactory()
    ventas = _autenticar(VendedorFactory())

    respuesta = ventas.patch(f"{PRODUCTOS}/{producto.pk}", {"codigo_fabrica": "X1"}, format="json")

    assert respuesta.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────────
# La base lo impide aunque se salte Django
# ─────────────────────────────────────────────────────────────────────
def test_la_base_rechaza_la_forma_interna_en_sql_crudo():
    producto = ProductoFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "UPDATE catalogo_producto SET codigo_fabrica = %s WHERE id = %s",
                ["2000000000015", producto.pk],
            )


def test_la_base_rechaza_un_duplicado_en_sql_crudo():
    ProductoFactory(codigo_fabrica="ABC123")
    otro = ProductoFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "UPDATE catalogo_producto SET codigo_fabrica = 'ABC123' WHERE id = %s", [otro.pk]
            )


# ─────────────────────────────────────────────────────────────────────
# ?codigo= encuentra por cualquiera de los dos (RF-70)
# ─────────────────────────────────────────────────────────────────────
def test_la_busqueda_encuentra_por_cualquiera_de_los_dos_codigos():
    con_fabrica = ProductoFactory(codigo_fabrica="7501031311309")
    ProductoFactory()  # sin codigo de fabrica: no debe colarse
    ventas = _autenticar(VendedorFactory())

    por_interno = ventas.get(PRODUCTOS, {"codigo": con_fabrica.codigo}).data["results"]
    por_fabrica = ventas.get(PRODUCTOS, {"codigo": "7501031311309"}).data["results"]
    alfanumerico = ProductoFactory(codigo_fabrica="ABC123X")
    en_minusculas = ventas.get(PRODUCTOS, {"codigo": "abc123x"}).data["results"]

    assert [p["id"] for p in por_interno] == [con_fabrica.pk]
    assert [p["id"] for p in por_fabrica] == [con_fabrica.pk]
    assert [p["id"] for p in en_minusculas] == [alfanumerico.pk]


def test_un_codigo_de_fabrica_parcial_no_encuentra_nada():
    ProductoFactory(codigo_fabrica="7501031311309")
    ventas = _autenticar(VendedorFactory())

    assert ventas.get(PRODUCTOS, {"codigo": "750103131130"}).data["results"] == []


def test_un_codigo_vacio_no_trae_los_productos_sin_codigo_de_fabrica():
    """Con la busqueda en los dos campos, codigo_fabrica = '' coincidiria
    con todos los que no tienen uno."""
    ProductoFactory()
    ProductoFactory()
    ventas = _autenticar(VendedorFactory())

    assert ventas.get(PRODUCTOS, {"codigo": "   "}).data["results"] == []
