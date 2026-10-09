"""Configuracion comun de las pruebas.

Se aplica a toda la suite, de ambas aplicaciones, que conviven en un
unico repositorio propio e independiente de cualquier otro proyecto
(RNF-21).
"""

import pytest


@pytest.fixture(autouse=True)
def _hasher_rapido_en_pruebas(settings):
    """Acelera la suite sustituyendo el hash de contrasenas.

    PBKDF2 es deliberadamente lento (unos 330 ms por operacion en este
    equipo): esa lentitud es exactamente lo que lo hace seguro frente a
    un ataque por fuerza bruta. Pero la suite crea usuarios e inicia
    sesion continuamente, asi que ese coste dominaba el tiempo total y
    la ejecucion completa pasaba de diez minutos.

    Una suite que nadie corre por lenta deja de proteger, que es lo
    contrario de lo que RNF-23 busca. Aqui se usa MD5 **solo durante
    las pruebas**: no toca la configuracion real, que sigue usando
    PBKDF2, y hay una prueba que lo verifica (test_modelo.py).
    """
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def _guardian_del_libro(request):
    """T-8.5 — tras cada prueba con base de datos, el libro cuadra.

    RN-MOV-03 dice que la suma de los movimientos de un producto es
    siempre su stock. La prueba de concurrencia lo demuestra para las
    carreras conocidas; este guardian lo vigila en TODAS las pruebas: si
    algun camino futuro cambia el stock sin pasar por
    inventario.services, la prueba que lo ejerza fallara aqui, aunque
    no estuviera pensada para el libro. Es del mismo tipo que la matriz
    de permisos: no prueba una funcionalidad, impide que se rompa una
    garantia sin que nadie lo note.

    Solo juzga productos con punto de partida en el libro (ALTA o
    SALDO_INICIAL); los que crean las fabricas escribiendo el stock
    directamente no tienen un libro completo que comparar.

    Las pruebas que escriben movimientos sueltos o descuadran el libro a
    proposito se excluyen con `@pytest.mark.libro_libre`.
    """
    marcador = request.node.get_closest_marker("django_db")
    if marcador is None or request.node.get_closest_marker("libro_libre"):
        yield
        return

    # Se pide aqui el acceso a la base para que este guardian se cierre
    # ANTES que ella: si no, al comprobar el libro la prueba ya habria
    # revertido sus datos y siempre cuadraria.
    transaccional = marcador.kwargs.get(
        "transaction", bool(marcador.args and marcador.args[0])
    )
    request.getfixturevalue("transactional_db" if transaccional else "db")

    yield

    from inventario.verificacion import libros_descuadrados

    descuadrados = libros_descuadrados()
    if descuadrados:
        pytest.fail(
            "El libro de movimientos no cuadra al terminar la prueba "
            f"(RN-MOV-03): {descuadrados}",
            pytrace=False,
        )
