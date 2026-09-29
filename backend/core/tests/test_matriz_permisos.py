"""T-1.8 — Matriz de permisos automatizada (RNF-02).

Recorre **cada endpoint existente × cada rol** y compara el resultado
contra la matriz de `spec.md` seccion 4.4.

Esta prueba se amplia en cada bloque posterior al anadir endpoints. El
guardian `test_ningun_endpoint_queda_fuera_de_la_matriz` es lo que hace
que esa ampliacion no se olvide: si alguien publica una ruta nueva y no
la declara aqui, la prueba falla y obliga a decidir explicitamente quien
puede usarla.
"""

import pytest
from django.urls import get_resolver
from rest_framework import status
from rest_framework.test import APIClient

from usuarios.models import Rol
from usuarios.tests.factories import (
    AdministradorFactory,
    TecnicoFactory,
    VendedorFactory,
)

pytestmark = pytest.mark.django_db

#: Quien puede llegar a cada endpoint, segun spec.md seccion 4.4.
#:
#: `None` en lugar de una tupla significa endpoint publico.
#: Se declara el acceso, no el resultado: un rol autorizado que envia
#: datos invalidos recibira 400, y eso cuenta como "pudo entrar".
MATRIZ = {
    # ── Autenticacion ────────────────────────────────────────────────
    ("POST", "/api/v1/auth/login"): None,
    ("POST", "/api/v1/auth/refresh"): None,
    ("POST", "/api/v1/auth/logout"): (Rol.ADMINISTRADOR, Rol.VENTAS, Rol.SERVICIOS),
    ("GET", "/api/v1/auth/me"): (Rol.ADMINISTRADOR, Rol.VENTAS, Rol.SERVICIOS),
    ("POST", "/api/v1/auth/me/password"): (
        Rol.ADMINISTRADOR,
        Rol.VENTAS,
        Rol.SERVICIOS,
    ),
    # ── Catalogo: gestion solo Administrador, consulta tambien Ventas ─
    ("GET", "/api/v1/categorias"): (Rol.ADMINISTRADOR, Rol.VENTAS),
    ("POST", "/api/v1/categorias"): (Rol.ADMINISTRADOR,),
    ("GET", "/api/v1/categorias/{id}"): (Rol.ADMINISTRADOR, Rol.VENTAS),
    ("PATCH", "/api/v1/categorias/{id}"): (Rol.ADMINISTRADOR,),
    ("PUT", "/api/v1/categorias/{id}"): (Rol.ADMINISTRADOR,),
    ("DELETE", "/api/v1/categorias/{id}"): (Rol.ADMINISTRADOR,),
    ("GET", "/api/v1/productos"): (Rol.ADMINISTRADOR, Rol.VENTAS),
    ("POST", "/api/v1/productos"): (Rol.ADMINISTRADOR,),
    ("GET", "/api/v1/productos/{id}"): (Rol.ADMINISTRADOR, Rol.VENTAS),
    ("PATCH", "/api/v1/productos/{id}"): (Rol.ADMINISTRADOR,),
    ("PUT", "/api/v1/productos/{id}"): (Rol.ADMINISTRADOR,),
    ("DELETE", "/api/v1/productos/{id}"): (Rol.ADMINISTRADOR,),
    # ── Ventas: Administrador y Ventas ───────────────────────────────
    # El alcance dentro del rol (propias frente a todas) lo controla
    # get_queryset, no el permiso de entrada: se verifica en
    # ventas/tests/test_api_ventas.py.
    ("GET", "/api/v1/ventas"): (Rol.ADMINISTRADOR, Rol.VENTAS),
    ("POST", "/api/v1/ventas"): (Rol.ADMINISTRADOR, Rol.VENTAS),
    ("GET", "/api/v1/ventas/{id}"): (Rol.ADMINISTRADOR, Rol.VENTAS),
    ("POST", "/api/v1/ventas/{id}/anular"): (Rol.ADMINISTRADOR, Rol.VENTAS),
    # ── Servicios: Administrador y Servicios ─────────────────────────
    # Salvo COTIZAR, que es solo del Administrador (RF-56, RF-57): es
    # la unica accion del modulo con permiso mas estrecho que el resto.
    ("GET", "/api/v1/solicitudes"): (Rol.ADMINISTRADOR, Rol.SERVICIOS),
    ("POST", "/api/v1/solicitudes"): (Rol.ADMINISTRADOR, Rol.SERVICIOS),
    ("GET", "/api/v1/solicitudes/{id}"): (Rol.ADMINISTRADOR, Rol.SERVICIOS),
    ("POST", "/api/v1/solicitudes/{id}/iniciar"): (
        Rol.ADMINISTRADOR,
        Rol.SERVICIOS,
    ),
    ("POST", "/api/v1/solicitudes/{id}/finalizar"): (
        Rol.ADMINISTRADOR,
        Rol.SERVICIOS,
    ),
    ("POST", "/api/v1/solicitudes/{id}/cancelar"): (
        Rol.ADMINISTRADOR,
        Rol.SERVICIOS,
    ),
    ("POST", "/api/v1/solicitudes/{id}/cotizar"): (Rol.ADMINISTRADOR,),
    # ── Configuracion del sistema: solo Administrador ────────────────
    ("GET", "/api/v1/configuracion"): (Rol.ADMINISTRADOR,),
    ("PATCH", "/api/v1/configuracion"): (Rol.ADMINISTRADOR,),
    # ── Gestion de usuarios: solo Administrador ──────────────────────
    ("GET", "/api/v1/usuarios"): (Rol.ADMINISTRADOR,),
    ("POST", "/api/v1/usuarios"): (Rol.ADMINISTRADOR,),
    ("GET", "/api/v1/usuarios/{id}"): (Rol.ADMINISTRADOR,),
    ("PATCH", "/api/v1/usuarios/{id}"): (Rol.ADMINISTRADOR,),
    ("POST", "/api/v1/usuarios/{id}/bloquear"): (Rol.ADMINISTRADOR,),
    ("POST", "/api/v1/usuarios/{id}/desbloquear"): (Rol.ADMINISTRADOR,),
    ("POST", "/api/v1/usuarios/{id}/restablecer-password"): (Rol.ADMINISTRADOR,),
}

FABRICAS = {
    Rol.ADMINISTRADOR: AdministradorFactory,
    Rol.VENTAS: VendedorFactory,
    Rol.SERVICIOS: TecnicoFactory,
}


def _cliente_con_rol(rol, objetivo_id):
    """Cliente autenticado con el rol pedido.

    El usuario objetivo de las rutas de detalle se crea aparte, para
    que las protecciones de RN-USU-02 y RN-USU-03 (que prohiben operar
    sobre la cuenta propia) no se confundan con una falta de permiso.
    """
    usuario = FABRICAS[rol](username=f"prueba_{rol.lower()}")
    # Siempre debe quedar otro administrador activo, para que RN-USU-04
    # no interfiera con lo que aqui se mide, que es el acceso.
    AdministradorFactory(username="admin_de_reserva")

    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


def _ejecutar(cliente, metodo, url):
    return getattr(cliente, metodo.lower())(url, {}, format="json")


@pytest.mark.parametrize(
    ("metodo", "plantilla", "roles"),
    [(m, u, r) for (m, u), r in MATRIZ.items()],
    ids=[f"{m}_{u}" for m, u in MATRIZ],
)
@pytest.mark.parametrize("rol", list(Rol), ids=lambda r: r.lower())
def test_cada_endpoint_admite_solo_los_roles_de_la_matriz(
    metodo, plantilla, roles, rol
):
    """El criterio central de T-1.8.

    Se comprueba el **acceso**, no el exito: a un rol autorizado que
    envia un cuerpo vacio le corresponde un 400, y eso significa que
    paso el control de permisos. Lo que nunca debe ocurrir es un 403
    para un rol autorizado, ni un 2xx/400 para uno que no lo esta.
    """
    if roles is None:
        pytest.skip("Endpoint publico; se cubre en test_endpoints_publicos.")

    objetivo = VendedorFactory(username="objetivo")
    cliente = _cliente_con_rol(rol, objetivo.id)
    url = plantilla.format(id=objetivo.id)

    respuesta = _ejecutar(cliente, metodo, url)

    if rol in roles:
        assert respuesta.status_code != status.HTTP_403_FORBIDDEN, (
            f"{rol} deberia poder acceder a {metodo} {plantilla} "
            f"segun spec.md 4.4, y recibio 403."
        )
    else:
        assert respuesta.status_code == status.HTTP_403_FORBIDDEN, (
            f"{rol} NO deberia acceder a {metodo} {plantilla} "
            f"segun spec.md 4.4, y recibio {respuesta.status_code}."
        )


@pytest.mark.parametrize(
    ("metodo", "plantilla"),
    [(m, u) for (m, u), r in MATRIZ.items() if r is not None],
    ids=[f"{m}_{u}" for (m, u), r in MATRIZ.items() if r is not None],
)
def test_ningun_endpoint_protegido_responde_sin_autenticacion(metodo, plantilla):
    """RNF-01: ninguna funcionalidad accesible sin autenticar."""
    url = plantilla.format(id=1)

    respuesta = _ejecutar(APIClient(), metodo, url)

    assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED


def test_los_unicos_endpoints_publicos_son_los_de_token():
    """RNF-01: la lista de excepciones se declara explicitamente.

    login y refresh son publicos por necesidad: quien aun no tiene
    token no puede presentar ninguno.
    """
    publicos = {url for (_, url), roles in MATRIZ.items() if roles is None}

    assert publicos == {"/api/v1/auth/login", "/api/v1/auth/refresh"}


# ─────────────────────────────────────────────────────────────────────
# El guardian: la matriz no puede quedarse atras
# ─────────────────────────────────────────────────────────────────────
def _rutas_publicadas():
    """Todas las rutas de /api/v1/ que expone el proyecto."""
    rutas = set()

    def recorrer(patrones, prefijo=""):
        for patron in patrones:
            if hasattr(patron, "url_patterns"):
                recorrer(patron.url_patterns, prefijo + str(patron.pattern))
            else:
                rutas.add(prefijo + str(patron.pattern))

    recorrer(get_resolver().url_patterns)
    return {r for r in rutas if r.startswith("api/v1/")}


def _normalizar(ruta):
    """Reduce una ruta de Django a la forma usada en la matriz."""
    import re

    ruta = "/" + ruta.lstrip("/")
    ruta = re.sub(r"\(\?P<pk>[^)]+\)", "{id}", ruta)
    ruta = re.sub(r"<[^>]+>", "{id}", ruta)
    return ruta.rstrip("/").replace("\\.", ".").rstrip("$").replace("^", "")


def test_ningun_endpoint_queda_fuera_de_la_matriz():
    """El guardian que mantiene viva esta prueba.

    Sin el, anadir un endpoint en un bloque posterior no rompería
    nada: la matriz seguiria pasando mientras describiera solo los
    endpoints antiguos, y un endpoint nuevo podria quedar sin que
    nadie decidiera quien puede usarlo.
    """
    declaradas = {url for _, url in MATRIZ}

    # Se descartan antes de normalizar: los sufijos de formato de DRF
    # llevan su propio parametro y se confundirian con un identificador.
    publicadas = {
        _normalizar(r) for r in _rutas_publicadas() if "format" not in r
    }
    publicadas -= {"/api/v1", "/api/v1/"}

    sin_declarar = publicadas - declaradas

    assert not sin_declarar, (
        "Estos endpoints existen pero no estan en la matriz de permisos. "
        "Anadalos a MATRIZ declarando que roles pueden usarlos, segun "
        f"spec.md seccion 4.4: {sorted(sin_declarar)}"
    )
