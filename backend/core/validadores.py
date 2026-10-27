"""Formato de los datos de contacto (spec.md v1.5, plan.md 7.14).

Un solo lugar para la regla, que se aplica en tres sitios: el registro
de clientes, el cliente ocasional de una venta y el contacto de una
solicitud de servicio. Si cada uno escribiera su propia expresion
regular, bastaria con cambiar una para que dejaran de coincidir.
"""

import re

#: RN-CLI-09 y RF-100: exactamente 8 digitos, solo numeros.
PATRON_TELEFONO = re.compile(r"^[0-9]{8}$")
MENSAJE_TELEFONO = "El teléfono debe tener exactamente 8 dígitos, solo números."


def telefono_valido(valor):
    """RN-CLI-09 — 8 digitos ASCII, sin espacios ni separadores.

    `[0-9]` y no `\\d`: en Python, `\\d` acepta tambien digitos de otros
    alfabetos (arabigos, devanagari...), que la base de datos rechazaria.
    """
    return bool(PATRON_TELEFONO.fullmatch(valor or ""))
