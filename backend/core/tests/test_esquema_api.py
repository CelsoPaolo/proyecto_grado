"""T-13.3 — La documentacion de la API se genera sin avisos (T-7.4).

drf-spectacular avisa cuando no puede describir bien un endpoint o
cuando dos enumeraciones chocan de nombre. Un aviso no rompe nada, y
por eso pasa desapercibido: el esquema sale igual, pero con nombres como
`TipoF98Enum` o con respuestas sin tipo. Esta prueba lo convierte en un
fallo, para que la documentacion de /api/docs no se degrade en silencio
al anadir endpoints.
"""

import pytest
from django.core.management import call_command


def test_el_esquema_openapi_se_genera_sin_avisos(tmp_path):
    destino = tmp_path / "esquema.yml"

    try:
        call_command("spectacular", "--fail-on-warn", "--file", str(destino))
    except SystemExit as salida:
        pytest.fail(f"drf-spectacular emitió avisos o errores (salida {salida.code}).")

    texto = destino.read_text(encoding="utf-8")
    assert "TipoMovimientoEnum" in texto and "TipoServicioEnum" in texto
    assert "/api/v1/reportes/xlsx" in texto and "/api/v1/clientes" in texto
