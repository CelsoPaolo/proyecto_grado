"""T-OP.2 — Comando importar_catalogo (plan.md 11.3, PT-05).

CSV de muestra con el mismo formato que los exportados (UTF-8 con BOM),
imagenes generadas con Pillow y MEDIA_ROOT temporal: la prueba no lee
nada fuera de su carpeta temporal.
"""

import csv
from io import StringIO
from unittest import mock

import pytest
from django.core.management import CommandError, call_command
from PIL import Image

from catalogo import importacion
from catalogo.codigos import PATRON_INTERNO, es_ean13_valido
from catalogo.models import Categoria, Producto
from catalogo.tests.factories import CategoriaFactory, ProductoFactory
from inventario.models import MovimientoStock, TipoMovimiento
from inventario.verificacion import libros_descuadrados
from usuarios.tests.factories import AdministradorFactory, VendedorFactory

pytestmark = pytest.mark.django_db

CAB_PRODUCTOS = ["id", "categoria_id", "nombre", "slug", "descripcion", "precio", "stock", "marca",
                 "imagen", "destacado", "activo", "created_at", "updated_at", "deleted_at"]


def _escribir(ruta, cabecera, filas):
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(cabecera)
        escritor.writerows(filas)
    return str(ruta)


def _producto(id_, cat, nombre, precio="100.00", imagen=""):
    return [id_, cat, nombre, "slug", f"Descripción de {nombre}", precio, "7", "Marca", imagen, "0", "1", "", "", ""]


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def origen(tmp_path):
    """Seis filas: tres buenas (una sin imagen en disco) y tres problemáticas."""
    imagenes = tmp_path / "laravel_storage"
    (imagenes / "productos").mkdir(parents=True)
    Image.new("RGB", (20, 20), "purple").save(imagenes / "productos" / "camara.png")
    Image.new("RGB", (20, 20), "black").save(imagenes / "productos" / "router.jpg", "JPEG")
    (imagenes / "productos" / "roto.png").write_bytes(b"esto no es una imagen")

    productos = _escribir(tmp_path / "productos.csv", CAB_PRODUCTOS, [
        _producto("1", "1", "Cámara Bullet Dahua 2MP", "320.00", "productos/camara.png"),
        _producto("2", "2", "Router TP-Link AC1200", "250.50", "productos/router.jpg"),
        _producto("3", "2", "Switch PoE 8 puertos", "410.00", "productos/no_existe.png"),
        _producto("4", "2", "   ", "10.00"),
        _producto("5", "9", "Producto de categoría fantasma", "10.00"),
        _producto("6", "1", "Cámara gratis", "0.00"),
        _producto("7", "1", "cámara bullet dahua 2mp", "300.00"),
        _producto("8", "2", "Cable UTP", "5.00", "productos/roto.png"),
    ])
    categorias = _escribir(tmp_path / "categorias.csv", ["id", "nombre", "slug", "descripcion", "activa", "created_at", "updated_at"], [
        ["1", "Cámaras y Videovigilancia", "c", "", "1", "", ""],
        ["2", "Redes y Conectividad", "r", "", "1", "", ""],
    ])
    diferencias = _escribir(tmp_path / "diferencias.csv",
                            ["id_antiguo", "nombre", "campo", "base_antigua", "seeder", "modificado_en_base_antigua", "valor_que_se_importaria", "motivo"],
                            [["2", "Router TP-Link AC1200", "precio", "250.50", "280.00", "2026-08-20", "250.50", "Editado a mano"]])
    return {"productos": productos, "categorias": categorias, "imagenes": str(imagenes),
            "diferencias": diferencias, "tmp": tmp_path}


@pytest.fixture
def admin():
    return AdministradorFactory(username="importador")


def _plan(origen, **extra):
    return importacion.construir_plan(
        origen["productos"], origen["categorias"], imagenes=origen["imagenes"],
        diferencias_csv=origen["diferencias"], **extra,
    )


def _comando(origen, *args):
    salida = StringIO()
    call_command("importar_catalogo", "--productos", origen["productos"], "--categorias", origen["categorias"],
                 "--imagenes", origen["imagenes"], "--diferencias", origen["diferencias"], *args, stdout=salida)
    return salida.getvalue()


# ─────────────────────────────────────────────────────────────────────
# Informe
# ─────────────────────────────────────────────────────────────────────
def test_el_informe_no_escribe_nada_en_la_base(origen):
    antes = (Producto.objects.count(), Categoria.objects.count(), MovimientoStock.objects.count())

    salida = _comando(origen)

    assert "no se escribió nada" in salida
    assert (Producto.objects.count(), Categoria.objects.count(), MovimientoStock.objects.count()) == antes


def test_los_problematicos_no_se_importan_y_aparecen_con_su_motivo(origen):
    plan = _plan(origen)

    motivos = {i: m for i, _, m in plan.problematicos}
    assert motivos == {
        "4": "nombre vacío",
        "5": "su categoría no existe en categorias.csv",
        "6": "precio no positivo",
        "7": "nombre repetido dentro del CSV",
    }
    assert [p["id_antiguo"] for p in plan.a_importar] == ["1", "2", "3", "8"]
    texto = importacion.informe(plan)
    assert "Problemáticos, NO se importan: 4" in texto and "precio no positivo" in texto


def test_un_nombre_que_ya_existe_en_el_sistema_es_problematico(origen):
    ProductoFactory(nombre="Router TP-Link AC1200")

    motivos = {i: m for i, _, m in _plan(origen).problematicos}

    assert motivos["2"] == "ya existe un producto con ese nombre"


def test_una_imagen_faltante_o_invalida_deja_el_producto_sin_imagen_y_en_el_informe(origen):
    plan = _plan(origen)

    sin = {i: m for i, _, m in plan.sin_imagen}
    assert "no existe" in sin["3"] and "no es una imagen válida" in sin["8"]
    assert {p["id_antiguo"] for p in plan.a_importar if p["imagen"]} == {"1", "2"}


def test_las_categorias_parecidas_a_una_existente_se_senalan(origen):
    CategoriaFactory(nombre="Redes")

    plan = _plan(origen)

    assert plan.categorias_parecidas["Redes y Conectividad"] == ["Redes"]
    assert "PARECIDA a: Redes" in importacion.informe(plan)


def test_el_mapa_de_categorias_fusiona_en_una_existente(origen):
    CategoriaFactory(nombre="Redes")
    mapa = _escribir(origen["tmp"] / "mapa.csv", ["origen", "destino"], [["Redes y Conectividad", "redes"]])

    plan = _plan(origen, mapa_categorias=mapa)

    assert {p["categoria"] for p in plan.a_importar if p["id_antiguo"] == "2"} == {"Redes"}
    assert "Redes" in plan.categorias_existentes and "Redes y Conectividad" not in plan.categorias_nuevas


def test_las_diferencias_con_el_seeder_se_marcan_sin_cambiar_que_se_importa(origen):
    con, sin = _plan(origen), importacion.construir_plan(origen["productos"], origen["categorias"], imagenes=origen["imagenes"])

    texto = importacion.informe(con)
    assert "base antigua 250.50, seeder 280.00, se importaría 250.50" in texto
    assert "CONFIRMAR CON LA EMPRESA" in texto
    assert con.a_importar == sin.a_importar and con.huella == sin.huella


# ─────────────────────────────────────────────────────────────────────
# Aplicar
# ─────────────────────────────────────────────────────────────────────
def test_cada_producto_importado_nace_como_uno_creado_a_mano(origen, admin):
    plan = _plan(origen)

    importacion.aplicar(plan, huella=plan.huella, usuario=admin)

    importados = Producto.objects.filter(nombre__in=[p["nombre"] for p in plan.a_importar])
    assert importados.count() == 4
    for producto in importados:
        assert es_ean13_valido(producto.codigo) and PATRON_INTERNO.match(producto.codigo)
        assert (producto.stock, producto.meses_garantia) == (0, 0)
        [alta] = MovimientoStock.objects.filter(producto=producto)
        assert (alta.tipo, alta.cantidad, alta.usuario) == (TipoMovimiento.ALTA, 0, admin)
    assert Producto.objects.get(nombre="Router TP-Link AC1200").precio == pytest.approx(250.50)
    assert Producto.objects.get(nombre="Cámara Bullet Dahua 2MP").imagen
    assert not Producto.objects.get(nombre="Switch PoE 8 puertos").imagen
    assert set(Categoria.objects.values_list("nombre", flat=True)) >= {"Cámaras y Videovigilancia", "Redes y Conectividad"}


def test_una_huella_distinta_no_importa_nada(origen, admin):
    plan = _plan(origen)

    with pytest.raises(importacion.HuellaNoCoincide):
        importacion.aplicar(plan, huella="0000000000000000", usuario=admin)

    assert not Producto.objects.exists()


def test_un_fallo_a_mitad_no_deja_ningun_producto(origen, admin):
    plan = _plan(origen)
    real = importacion.crear_producto
    llamadas = []

    def falla_en_la_tercera(**datos):
        llamadas.append(1)
        if len(llamadas) == 3:
            raise RuntimeError("fallo simulado")
        return real(**datos)

    with mock.patch.object(importacion, "crear_producto", side_effect=falla_en_la_tercera):
        with pytest.raises(RuntimeError):
            importacion.aplicar(plan, huella=plan.huella, usuario=admin)

    assert not Producto.objects.exists() and not Categoria.objects.exists()


def test_ejecutarlo_dos_veces_no_duplica_nada(origen, admin):
    plan = _plan(origen)
    importacion.aplicar(plan, huella=plan.huella, usuario=admin)

    segundo = _plan(origen)
    importacion.aplicar(segundo, huella=segundo.huella, usuario=admin)

    assert segundo.a_importar == []
    assert Producto.objects.count() == 4


def test_el_comando_aplica_solo_con_la_huella_y_un_administrador(origen, admin):
    huella = _plan(origen).huella

    with pytest.raises(CommandError):
        _comando(origen, "--aplicar", "--huella", huella, "--usuario", VendedorFactory().username)
    assert not Producto.objects.exists()

    salida = _comando(origen, "--aplicar", "--huella", huella, "--usuario", "importador")
    assert "Importados 4 productos" in salida


# ─────────────────────────────────────────────────────────────────────
# Recuento (opcional)
# ─────────────────────────────────────────────────────────────────────
def _planilla_rellena(origen, cantidades, fecha="2026-10-12", nombres=None):
    """Genera la planilla con el comando y la rellena como lo haria el
    personal: `cantidades` {id: texto}; `nombres` {id: otro nombre} para
    simular una planilla desordenada."""
    ruta = origen["tmp"] / "planilla.csv"
    importacion.escribir_planilla(_plan(origen), ruta)
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.reader(archivo))
    filas[0][1] = fecha
    for fila in filas[2:]:
        fila[3] = cantidades.get(fila[0], "")
        fila[1] = (nombres or {}).get(fila[0], fila[1])
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        csv.writer(archivo).writerows(filas)
    return str(ruta)


def test_la_planilla_tiene_un_producto_por_fila_sin_problematicos_y_sin_cifras(origen):
    ruta = origen["tmp"] / "planilla.csv"

    importacion.escribir_planilla(_plan(origen), ruta)

    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.reader(archivo))
    assert filas[0] == ["fecha_del_recuento", ""]
    assert filas[1] == importacion.CABECERA_PLANILLA
    assert [f[0] for f in filas[2:]] == ["1", "2", "3", "8"]
    assert all(f[3] == "" for f in filas[2:])


def test_con_existencias_cada_contado_queda_con_alta_cero_y_ajuste_carga_inicial(origen, admin):
    planilla = _planilla_rellena(origen, {"1": "12", "2": "0", "8": "-3"})
    plan = _plan(origen, existencias_csv=planilla)

    importacion.aplicar(plan, huella=plan.huella, usuario=admin)

    camara = Producto.objects.get(nombre="Cámara Bullet Dahua 2MP")
    libro = list(MovimientoStock.objects.filter(producto=camara).order_by("id").values_list("tipo", "cantidad", "motivo", "usuario"))
    assert libro == [(TipoMovimiento.ALTA, 0, "", admin.pk), (TipoMovimiento.AJUSTE, 12, "Carga inicial", admin.pk)]
    assert camara.stock == 12
    # Contado en cero, no contado y fila invalida: en 0 y sin ajuste.
    for nombre in ("Router TP-Link AC1200", "Switch PoE 8 puertos", "Cable UTP"):
        producto = Producto.objects.get(nombre=nombre)
        assert producto.stock == 0
        assert not MovimientoStock.objects.filter(producto=producto, tipo=TipoMovimiento.AJUSTE).exists()
    assert libros_descuadrados() == []

    r = plan.recuento
    assert r["fecha"] == "2026-10-12"
    assert [i for i, *_ in r["cargados"]] == ["1"]
    assert [i for i, *_ in r["en_cero"]] == ["2"]
    assert [i for i, *_ in r["sin_contar"]] == ["3"]
    assert [i for i, *_ in r["invalidas"]] == ["8"]


def test_una_fila_cuyo_nombre_no_corresponde_a_su_id_no_se_carga(origen, admin):
    planilla = _planilla_rellena(origen, {"1": "5"}, nombres={"1": "Router TP-Link AC1200"})

    plan = _plan(origen, existencias_csv=planilla)

    assert [i for i, *_ in plan.recuento["invalidas"]] == ["1"]
    assert "planilla desordenada" in importacion.informe(plan)
    assert all(p["existencias"] == 0 for p in plan.a_importar)


def test_cambiar_una_cifra_despues_del_informe_cambia_la_huella(origen, admin):
    aprobado = _plan(origen, existencias_csv=_planilla_rellena(origen, {"1": "12"}))
    cambiado = _plan(origen, existencias_csv=_planilla_rellena(origen, {"1": "13"}))

    assert aprobado.huella != cambiado.huella
    with pytest.raises(importacion.HuellaNoCoincide):
        importacion.aplicar(cambiado, huella=aprobado.huella, usuario=admin)
    assert not Producto.objects.exists()


def test_un_ajuste_que_falla_revierte_tambien_la_importacion(origen, admin):
    plan = _plan(origen, existencias_csv=_planilla_rellena(origen, {"2": "4"}))

    with mock.patch.object(importacion, "ajustar_existencias", side_effect=RuntimeError("fallo en el ajuste")):
        with pytest.raises(RuntimeError):
            importacion.aplicar(plan, huella=plan.huella, usuario=admin)

    assert not Producto.objects.exists()
    assert not MovimientoStock.objects.exists()
