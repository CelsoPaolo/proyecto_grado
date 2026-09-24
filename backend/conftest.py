"""Configuracion comun de las pruebas.

Se aplica a toda la suite, de ambas aplicaciones.
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
