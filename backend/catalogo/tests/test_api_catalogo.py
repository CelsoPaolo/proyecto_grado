"""T-2.2 a T-2.5 — API del catalogo (RF-07 a RF-14, RF-53)."""

import io

import pytest
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.models import Categoria, Producto
from core.exceptions import Codigo
from usuarios.tests.factories import (
    AdministradorFactory,
    TecnicoFactory,
    VendedorFactory,
)

from .factories import CategoriaFactory, ProductoFactory

pytestmark = pytest.mark.django_db

CATEGORIAS = "/api/v1/categorias"
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
def como_admin():
    return _autenticar(AdministradorFactory())


@pytest.fixture
def como_vendedor():
    return _autenticar(VendedorFactory())


def _imagen_de_prueba(formato="PNG", nombre="foto.png", tamano=(10, 10)):
    buffer = io.BytesIO()
    Image.new("RGB", tamano, color="red").save(buffer, format=formato)
    buffer.seek(0)
    buffer.name = nombre
    return buffer


# ═════════════════════════════════════════════════════════════════════
# T-2.2 — Categorias (RF-07, RF-08)
# ═════════════════════════════════════════════════════════════════════
def test_el_administrador_crea_una_categoria(como_admin):
    respuesta = como_admin.post(
        CATEGORIAS, {"nombre": "Laptops", "descripcion": "Equipos portátiles"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert Categoria.objects.filter(nombre="Laptops").exists()


def test_no_se_admite_una_categoria_con_nombre_repetido(como_admin):
    CategoriaFactory(nombre="Laptops")

    respuesta = como_admin.post(CATEGORIAS, {"nombre": "LAPTOPS"}, format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "nombre" in respuesta.data["errores"]


def test_eliminar_una_categoria_con_productos_responde_409(como_admin):
    """El criterio central de T-2.2 (RF-08)."""
    categoria = CategoriaFactory()
    ProductoFactory(categoria=categoria)

    respuesta = como_admin.delete(f"{CATEGORIAS}/{categoria.id}")

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.CATEGORIA_CON_PRODUCTOS
    assert Categoria.objects.filter(pk=categoria.pk).exists()


def test_una_categoria_sin_productos_si_se_elimina(como_admin):
    categoria = CategoriaFactory()

    respuesta = como_admin.delete(f"{CATEGORIAS}/{categoria.id}")

    assert respuesta.status_code == status.HTTP_204_NO_CONTENT
    assert not Categoria.objects.filter(pk=categoria.pk).exists()


def test_el_listado_de_categorias_informa_cuantos_productos_tiene_cada_una(
    como_admin,
):
    """Permite al Administrador saber de antemano cual podra eliminar."""
    categoria = CategoriaFactory()
    ProductoFactory.create_batch(3, categoria=categoria)

    respuesta = como_admin.get(CATEGORIAS)

    assert respuesta.data["results"][0]["cantidad_productos"] == 3


def test_el_vendedor_consulta_categorias_pero_no_las_modifica(como_vendedor):
    CategoriaFactory()

    assert como_vendedor.get(CATEGORIAS).status_code == status.HTTP_200_OK
    assert (
        como_vendedor.post(CATEGORIAS, {"nombre": "Nueva"}, format="json").status_code
        == status.HTTP_403_FORBIDDEN
    )


# ═════════════════════════════════════════════════════════════════════
# T-2.3 — Productos (RF-09, RF-10, RF-12, RF-14)
# ═════════════════════════════════════════════════════════════════════
def test_el_administrador_registra_un_producto(como_admin):
    categoria = CategoriaFactory()

    respuesta = como_admin.post(
        PRODUCTOS,
        {
            "nombre": "Teclado mecánico",
            "descripcion": "Switches azules",
            "precio": "350.00",
            "stock": 12,
            "categoria": categoria.id,
        },
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["categoria_nombre"] == categoria.nombre


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("precio", "0"), ("precio", "-10"), ("stock", -1)],
)
def test_se_rechazan_precio_no_positivo_y_stock_negativo(como_admin, campo, valor):
    """RF-14: la validacion responde con el campo, no con un 409 de la
    base, para que el formulario pueda senalarlo (RNF-15)."""
    categoria = CategoriaFactory()
    datos = {
        "nombre": "Producto X",
        "precio": "100.00",
        "stock": 5,
        "categoria": categoria.id,
    }
    datos[campo] = valor

    respuesta = como_admin.post(PRODUCTOS, datos, format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert campo in respuesta.data["errores"]


def test_el_administrador_edita_un_producto_incluidas_sus_existencias(como_admin):
    """RF-10: el ajuste de inventario es una edicion normal."""
    producto = ProductoFactory(stock=10)

    respuesta = como_admin.patch(
        f"{PRODUCTOS}/{producto.id}", {"stock": 25}, format="json"
    )

    assert respuesta.status_code == status.HTTP_200_OK
    producto.refresh_from_db()
    assert producto.stock == 25


def test_se_admite_una_imagen_valida(como_admin):
    categoria = CategoriaFactory()

    respuesta = como_admin.post(
        PRODUCTOS,
        {
            "nombre": "Monitor 24",
            "precio": "750.00",
            "stock": 4,
            "categoria": categoria.id,
            "imagen": _imagen_de_prueba(),
        },
        format="multipart",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["imagen"]


def test_un_archivo_que_no_es_imagen_se_rechaza_aunque_se_llame_jpg(como_admin):
    """El criterio de T-2.3.

    Comprobar solo la extension dejaria el catalogo mostrando un
    recurso roto. Se verifica el contenido.
    """
    categoria = CategoriaFactory()
    falsa = io.BytesIO(b"esto no es una imagen, solo texto")
    falsa.name = "trampa.jpg"

    respuesta = como_admin.post(
        PRODUCTOS,
        {
            "nombre": "Producto con trampa",
            "precio": "100.00",
            "stock": 1,
            "categoria": categoria.id,
            "imagen": falsa,
        },
        format="multipart",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "imagen" in respuesta.data["errores"]


def test_la_imagen_es_opcional(como_admin):
    """RN-CAT-06."""
    categoria = CategoriaFactory()

    respuesta = como_admin.post(
        PRODUCTOS,
        {"nombre": "Sin foto", "precio": "50.00", "stock": 3, "categoria": categoria.id},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["imagen"] is None


# ═════════════════════════════════════════════════════════════════════
# T-2.4 — Borrado suave (RF-11, CU-CAT-04)
# ═════════════════════════════════════════════════════════════════════
def test_eliminar_un_producto_lo_retira_sin_borrar_su_fila(como_admin):
    """El criterio central de T-2.4.

    Es lo que mantiene legible el historial de ventas (RN-VEN-04) y lo
    que permite que una anulacion siempre devuelva existencias
    (RN-VEN-07).
    """
    producto = ProductoFactory(activo=True)

    respuesta = como_admin.delete(f"{PRODUCTOS}/{producto.id}")

    assert respuesta.status_code == status.HTTP_200_OK
    producto.refresh_from_db()
    assert not producto.activo
    assert Producto.objects.filter(pk=producto.pk).exists()


def test_un_producto_retirado_desaparece_del_catalogo_de_trabajo(como_vendedor):
    vigente = ProductoFactory(activo=True)
    ProductoFactory(activo=False)

    respuesta = como_vendedor.get(PRODUCTOS)

    ids = [p["id"] for p in respuesta.data["results"]]
    assert ids == [vigente.id]


def test_el_administrador_puede_revisar_los_productos_retirados(como_admin):
    ProductoFactory(activo=True)
    retirado = ProductoFactory(activo=False)

    respuesta = como_admin.get(f"{PRODUCTOS}?activo=false")

    ids = [p["id"] for p in respuesta.data["results"]]
    assert ids == [retirado.id]


def test_un_producto_retirado_sigue_siendo_consultable_por_su_id(como_admin):
    """Su detalle debe seguir accesible: el historial lo referencia."""
    retirado = ProductoFactory(activo=False)

    respuesta = como_admin.get(f"{PRODUCTOS}/{retirado.id}")

    assert respuesta.status_code == status.HTTP_200_OK


# ═════════════════════════════════════════════════════════════════════
# T-2.5 — Busqueda y filtros (RF-13, RNF-18)
# ═════════════════════════════════════════════════════════════════════
def test_se_puede_buscar_por_nombre(como_vendedor):
    ProductoFactory(nombre="Teclado mecánico")
    ProductoFactory(nombre="Monitor curvo")

    respuesta = como_vendedor.get(f"{PRODUCTOS}?search=teclado")

    assert respuesta.data["count"] == 1
    assert respuesta.data["results"][0]["nombre"] == "Teclado mecánico"


def test_se_puede_filtrar_por_categoria(como_vendedor):
    perifericos = CategoriaFactory(nombre="Periféricos")
    ProductoFactory(categoria=perifericos)
    ProductoFactory(categoria=CategoriaFactory(nombre="Redes"))

    respuesta = como_vendedor.get(f"{PRODUCTOS}?categoria={perifericos.id}")

    assert respuesta.data["count"] == 1


def test_los_filtros_se_combinan(como_vendedor):
    categoria = CategoriaFactory()
    ProductoFactory(nombre="Teclado mecánico", categoria=categoria)
    ProductoFactory(nombre="Teclado membrana", categoria=CategoriaFactory())

    respuesta = como_vendedor.get(
        f"{PRODUCTOS}?search=teclado&categoria={categoria.id}"
    )

    assert respuesta.data["count"] == 1
    assert respuesta.data["results"][0]["nombre"] == "Teclado mecánico"


def test_el_listado_viene_paginado(como_vendedor):
    """RNF-18."""
    ProductoFactory.create_batch(25)

    respuesta = como_vendedor.get(PRODUCTOS)

    assert respuesta.data["count"] == 25
    assert len(respuesta.data["results"]) == 20
    assert respuesta.data["next"] is not None


def test_la_paginacion_de_categorias_es_estable(como_admin):
    """RNF-18.

    Una consulta sin orden hace que la paginacion repita o salte filas
    entre paginas: annotate() con agregacion descarta el orden por
    defecto del modelo, de ahi el order_by explicito en la vista.
    """
    CategoriaFactory.create_batch(25)

    pagina1 = como_admin.get(f"{CATEGORIAS}?page=1")
    pagina2 = como_admin.get(f"{CATEGORIAS}?page=2")

    ids1 = {c["id"] for c in pagina1.data["results"]}
    ids2 = {c["id"] for c in pagina2.data["results"]}

    assert len(ids1) == 20
    assert len(ids2) == 5
    assert ids1.isdisjoint(ids2)


# ═════════════════════════════════════════════════════════════════════
# RF-53 — marca de existencias bajas calculada en el servidor
# ═════════════════════════════════════════════════════════════════════
def test_cada_producto_informa_si_tiene_existencias_bajas(como_vendedor):
    """El frontend no conoce el umbral: recibe el veredicto tomado."""
    ProductoFactory(nombre="Escaso", stock=2)
    ProductoFactory(nombre="Abundante", stock=50)

    respuesta = como_vendedor.get(PRODUCTOS)
    por_nombre = {p["nombre"]: p for p in respuesta.data["results"]}

    assert por_nombre["Escaso"]["stock_bajo"] is True
    assert por_nombre["Abundante"]["stock_bajo"] is False


def test_se_pueden_listar_solo_los_productos_con_existencias_bajas(como_vendedor):
    ProductoFactory(nombre="Escaso", stock=1)
    ProductoFactory(nombre="Abundante", stock=99)

    respuesta = como_vendedor.get(f"{PRODUCTOS}?stock_bajo=true")

    assert respuesta.data["count"] == 1
    assert respuesta.data["results"][0]["nombre"] == "Escaso"


# ═════════════════════════════════════════════════════════════════════
# RNF-02 — el Encargado de Servicios no accede al catalogo
# ═════════════════════════════════════════════════════════════════════
def test_el_encargado_de_servicios_no_accede_al_catalogo():
    """spec.md matriz 4.4: no consulta el catalogo ni lo gestiona."""
    cliente = _autenticar(TecnicoFactory())

    assert cliente.get(PRODUCTOS).status_code == status.HTTP_403_FORBIDDEN
    assert cliente.get(CATEGORIAS).status_code == status.HTTP_403_FORBIDDEN
