"""T-7.1 — Cobertura de las reglas con prueba obligatoria.

`plan.md` §9 declara una lista de reglas cuyo incumplimiento equivale a
incumplir la especificacion. Este modulo comprueba que **cada una tiene
su prueba y que esa prueba existe con ese nombre**.

Por que hace falta un guardian asi: la suite puede estar en verde y una
regla haber quedado sin cubrir, porque nadie nota la ausencia de una
prueba que nunca se escribio. Si alguien borrara o renombrara una de
estas, aqui saltaria.

Este archivo NO vuelve a probar las reglas: solo verifica que la prueba
que las cubre sigue ahi.
"""

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent.parent

#: regla -> (archivo de pruebas, nombre de la funcion que la cubre)
#:
#: El orden y el contenido siguen la tabla de plan.md seccion 9.
COBERTURA_OBLIGATORIA = {
    "RN-VEN-02": [
        (
            "ventas/tests/test_servicios_ventas.py",
            "test_si_falta_stock_de_un_solo_producto_no_se_descuenta_ninguno",
        ),
        ("ventas/tests/test_api_ventas.py", "test_el_stock_insuficiente_responde_422_con_el_detalle"),
    ],
    "RN-VEN-04": [
        (
            "ventas/tests/test_servicios_ventas.py",
            "test_cambiar_el_precio_despues_no_altera_la_venta_historica",
        ),
    ],
    "RN-VEN-07": [
        (
            "ventas/tests/test_servicios_ventas.py",
            "test_anular_devuelve_las_existencias_al_valor_previo",
        ),
    ],
    "RN-VEN-11": [
        (
            "ventas/tests/test_servicios_ventas.py",
            "test_se_puede_anular_una_venta_antigua_sin_limite_de_plazo",
        ),
    ],
    "RN-SER-03": [
        ("servicios/tests/test_servicios.py", "test_no_se_finaliza_sin_observaciones"),
        ("servicios/tests/test_api.py", "test_no_se_finaliza_sin_observaciones"),
    ],
    "RN-SER-09": [
        (
            "servicios/tests/test_servicios.py",
            "test_el_tecnico_no_tiene_ninguna_relacion_con_las_cuentas",
        ),
        (
            "servicios/tests/test_servicios.py",
            "test_el_administrador_anota_el_tecnico_como_texto_libre",
        ),
    ],
    "RN-SER-13": [
        ("servicios/tests/test_servicios.py", "test_no_se_finaliza_sin_monto_cotizado"),
        ("servicios/tests/test_api.py", "test_no_se_finaliza_sin_monto_cotizado"),
        (
            "servicios/tests/test_servicios.py",
            "test_se_finaliza_un_servicio_cotizado_en_cero",
        ),
    ],
    "RN-SER-15": [
        (
            "servicios/tests/test_api.py",
            "test_el_tecnico_no_accede_al_detalle_de_una_solicitud_ajena",
        ),
        ("servicios/tests/test_api.py", "test_el_tecnico_solo_ve_sus_propias_solicitudes"),
    ],
    "RF-57": [
        (
            "servicios/tests/test_api.py",
            "test_el_tecnico_no_puede_cotizar_ni_su_propia_solicitud",
        ),
    ],
    "RN-VEN-09/RF-27": [
        (
            "ventas/tests/test_api_ventas.py",
            "test_el_vendedor_no_accede_al_detalle_de_una_venta_ajena",
        ),
        ("ventas/tests/test_api_ventas.py", "test_el_vendedor_no_puede_anular_una_venta_ajena"),
    ],
    "RN-USU-02": [
        (
            "usuarios/tests/test_servicios_usuarios.py",
            "test_un_administrador_no_puede_cambiar_su_propio_rol",
        ),
    ],
    "RN-USU-03": [
        (
            "usuarios/tests/test_servicios_usuarios.py",
            "test_un_administrador_no_puede_bloquearse_a_si_mismo",
        ),
    ],
    "RN-USU-04": [
        (
            "usuarios/tests/test_servicios_usuarios.py",
            "test_no_se_puede_bloquear_al_unico_administrador",
        ),
        (
            "usuarios/tests/test_servicios_usuarios.py",
            "test_un_administrador_bloqueado_no_cuenta_para_la_regla",
        ),
    ],
    "RN-IND-05": [
        ("panel/tests/test_panel.py", "test_el_total_nunca_viaja_sin_su_desglose"),
        ("panel/tests/test_panel.py", "test_el_desglose_cuadra_con_el_total"),
    ],
    "RN-ACC-05": [
        (
            "usuarios/tests/test_invalidacion_inmediata.py",
            "test_bloquear_invalida_el_access_token_en_la_peticion_siguiente",
        ),
        (
            "usuarios/tests/test_invalidacion_inmediata.py",
            "test_una_cuenta_bloqueada_no_puede_refrescar_su_token",
        ),
        (
            "usuarios/tests/test_invalidacion_inmediata.py",
            "test_desbloquear_no_revive_las_sesiones_anteriores_al_bloqueo",
        ),
    ],
    "RNF-08": [
        (
            "ventas/tests/test_concurrencia.py",
            "test_diez_ventas_simultaneas_de_tres_unidades_confirman_solo_tres",
        ),
        (
            "ventas/tests/test_concurrencia.py",
            "test_con_stock_suficiente_todas_las_ventas_simultaneas_confirman",
        ),
    ],
    # ── v1.4 (plan.md seccion 9, filas marcadas v1.3 del plan) ────────
    "RN-CAT-08": [
        ("catalogo/tests/test_codigo.py", "test_el_codigo_de_la_peticion_se_ignora_al_editar"),
        ("catalogo/tests/test_codigo.py", "test_un_producto_nuevo_recibe_un_ean13_interno_valido"),
        ("catalogo/tests/test_codigo.py", "test_retirar_un_producto_y_crear_otro_da_un_codigo_distinto"),
    ],
    "RN-CAT-10": [
        ("catalogo/tests/test_api_catalogo.py", "test_editar_un_producto_con_existencias_se_rechaza"),
    ],
    "RN-CAT-11": [
        ("catalogo/tests/test_codigo_fabrica.py", "test_un_codigo_repetido_se_rechaza_junto_al_campo_al_crear"),
        ("catalogo/tests/test_codigo_fabrica.py", "test_un_codigo_con_forma_de_interno_se_rechaza"),
        ("catalogo/tests/test_codigo_fabrica.py", "test_la_base_rechaza_la_forma_interna_en_sql_crudo"),
        ("catalogo/tests/test_codigo_fabrica.py", "test_dos_productos_sin_codigo_de_fabrica_conviven"),
        ("catalogo/tests/test_codigo_fabrica.py", "test_la_busqueda_encuentra_por_cualquiera_de_los_dos_codigos"),
    ],
    "RN-VEN-12": [
        ("ventas/tests/test_servicios_ventas.py", "test_cambiar_los_meses_de_garantia_despues_no_altera_la_venta"),
        ("ventas/tests/test_garantia_pdf.py", "test_cambiar_los_meses_del_producto_despues_no_cambia_la_garantia"),
    ],
    "RN-VEN-13": [
        ("ventas/tests/test_vencimiento.py", "test_sumar_meses"),
    ],
    "RN-VEN-14": [
        ("ventas/tests/test_garantia_pdf.py", "test_una_venta_anulada_no_emite_garantia"),
        ("ventas/tests/test_garantia_pdf.py", "test_una_venta_sin_lineas_con_garantia_no_la_emite"),
        ("ventas/tests/test_garantia_pdf.py", "test_no_lista_las_lineas_sin_garantia"),
    ],
    "RN-VEN-16": [
        ("ventas/tests/test_garantia_pdf.py", "test_otro_encargado_de_ventas_recibe_404_como_si_no_existiera"),
    ],
    "RN-MOV-01": [
        ("inventario/tests/test_movimientos_venta.py", "test_una_venta_rechazada_por_stock_no_deja_movimientos"),
        ("inventario/tests/test_movimientos_venta.py", "test_un_fallo_al_registrar_el_movimiento_revierte_toda_la_venta"),
    ],
    "RN-MOV-03": [
        ("conftest.py", "_guardian_del_libro"),
        ("inventario/tests/test_verificacion.py", "test_detecta_un_cambio_de_stock_fuera_del_libro"),
    ],
    "RN-MOV-04": [
        ("inventario/tests/test_modelo.py", "test_un_movimiento_guardado_no_se_modifica"),
        ("inventario/tests/test_modelo.py", "test_la_via_masiva_tampoco_borra"),
        ("inventario/tests/test_api_inventario.py", "test_el_libro_no_tiene_verbos_de_escritura"),
    ],
    "RN-MOV-05": [
        ("inventario/tests/test_api_inventario.py", "test_un_ajuste_invalido_se_rechaza_junto_al_campo"),
        ("inventario/tests/test_api_inventario.py", "test_ajustar_a_lo_mismo_que_hay_responde_409"),
        ("ventas/tests/test_concurrencia.py", "test_ajustes_y_ventas_simultaneos_dejan_el_libro_cuadrado"),
    ],
    "RN-CLI-04": [
        ("clientes/tests/test_servicios.py", "test_registrar_un_cliente_no_crea_ningun_usuario"),
    ],
    "RN-CLI-05": [
        ("ventas/tests/test_cliente_en_venta.py", "test_editar_y_desactivar_el_cliente_no_altera_las_ventas_anteriores"),
    ],
    "RN-CLI-06": [
        ("clientes/tests/test_api.py", "test_la_lista_no_contiene_la_clave_carnet_en_ninguna_fila"),
        ("ventas/tests/test_cliente_en_venta.py", "test_el_detalle_de_la_venta_no_contiene_el_carnet"),
        ("clientes/tests/test_ciclo_bloque11.py", "test_venta_a_cliente_registrado_editarlo_y_la_venta_conserva_sus_datos"),
        ("panel/tests/test_coherencia_reportes.py", "test_el_carnet_no_aparece_en_ninguna_salida"),
    ],
    "RN-REP-07": [
        ("panel/tests/test_coherencia_reportes.py", "test_las_cifras_del_resumen_son_identicas_en_las_tres"),
    ],
    "RN-REP-08": [
        ("panel/tests/test_reportes.py", "test_el_panel_y_el_reporte_de_hoy_dan_las_mismas_cifras"),
    ],
    "RNF-29": [
        ("inventario/tests/test_migracion_saldos.py", "test_revertir_borra_los_saldos_y_no_toca_los_productos"),
        ("catalogo/tests/test_migracion_codigo.py", "test_revertir_los_tres_pasos_devuelve_la_tabla_a_su_estado_anterior"),
        ("catalogo/tests/test_migracion_codigo.py", "test_todos_los_productos_existentes_reciben_un_codigo_valido_y_distinto"),
    ],
}


def _funciones_de(ruta_relativa):
    """Nombres de las funciones y metodos definidos en un archivo."""
    archivo = RAIZ / ruta_relativa
    if not archivo.exists():
        return None

    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nombres.add(nodo.name)
    return nombres


@pytest.mark.parametrize(
    ("regla", "archivo", "prueba"),
    [
        (regla, archivo, prueba)
        for regla, entradas in COBERTURA_OBLIGATORIA.items()
        for archivo, prueba in entradas
    ],
    ids=[
        f"{regla}-{prueba}"
        for regla, entradas in COBERTURA_OBLIGATORIA.items()
        for _, prueba in entradas
    ],
)
def test_cada_regla_obligatoria_conserva_su_prueba(regla, archivo, prueba):
    """El criterio central de T-7.1.

    Una suite en verde no demuestra que una regla este cubierta: puede
    faltar la prueba que nunca se escribio, o haberse borrado sin que
    nada falle.
    """
    funciones = _funciones_de(archivo)

    assert funciones is not None, (
        f"{regla}: el archivo {archivo} no existe. La prueba que cubre "
        f"esta regla desaparecio."
    )
    assert prueba in funciones, (
        f"{regla}: falta la prueba «{prueba}» en {archivo}. "
        f"Es una de las reglas con prueba obligatoria de plan.md §9: "
        f"sin ella, la regla queda sin verificar."
    )


def test_la_lista_cubre_todas_las_reglas_declaradas_en_el_plan():
    """Comprueba que este archivo no se quede atras del plan.

    Si alguien anade una fila a la tabla de plan.md §9 y no la declara
    aqui, la regla nueva quedaria sin guardian.

    Es ademas la comprobacion automatica de RNF-22: los documentos de
    `specs/` son vivos, y la forma de que no se conviertan en adorno es
    que el codigo los LEA y falle cuando divergen. Esta prueba abre
    plan.md de verdad; si el documento gana una regla que el codigo no
    cubre, la suite se pone en rojo.
    """
    plan = (RAIZ.parent / "specs" / "plan.md").read_text(encoding="utf-8")

    inicio = plan.index("**Reglas con prueba obligatoria**")
    fin = plan.index("---", inicio)
    tabla = plan[inicio:fin]

    declaradas = set()
    for linea in tabla.splitlines():
        if linea.startswith("| RN-") or linea.startswith("| RF-"):
            celda = linea.split("|")[1].strip()
            declaradas.update(
                parte.strip() for parte in celda.replace(" / ", "/").split("/")
                if parte.strip().startswith(("RN-", "RF-"))
            )

    # RN-USU-02/03/04 figura como una sola fila y aqui se desglosa.
    cubiertas = set(COBERTURA_OBLIGATORIA)
    cubiertas.discard("RN-VEN-09/RF-27")
    cubiertas.update({"RN-VEN-09", "RF-27"})

    sin_guardian = declaradas - cubiertas

    assert not sin_guardian, (
        "Estas reglas figuran en la tabla de plan.md §9 pero no están "
        f"declaradas en COBERTURA_OBLIGATORIA: {sorted(sin_guardian)}"
    )
