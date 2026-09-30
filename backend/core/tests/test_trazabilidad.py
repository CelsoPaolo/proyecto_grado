"""T-7.5 — Coherencia entre la especificacion y lo construido.

Recorre los requerimientos declarados en `spec.md` y comprueba que cada
uno esta **citado** en algun punto del codigo o de las pruebas.

Que un RF este citado no demuestra que funcione —eso lo demuestran las
pruebas de cada modulo—, pero sí detecta el caso contrario, que es el
que pasa inadvertido: un requerimiento que nadie implemento y del que
nadie se acordo. Una suite en verde no dice nada sobre lo que falta.
"""

import re
from pathlib import Path

import pytest

RAIZ_BACKEND = Path(__file__).resolve().parent.parent.parent
RAIZ_PROYECTO = RAIZ_BACKEND.parent
SPEC = RAIZ_PROYECTO / "specs" / "spec.md"


def _requerimientos_declarados(prefijo):
    """Lee los IDs de las tablas de requerimientos de spec.md."""
    texto = SPEC.read_text(encoding="utf-8")
    return sorted(
        set(re.findall(rf"^\| ({prefijo}-\d+) \|", texto, re.M)),
        key=lambda x: int(x.split("-")[1]),
    )


def _texto_del_proyecto():
    """Todo el codigo y las pruebas, de ambos lados."""
    piezas = []

    for patron in ("**/*.py",):
        for archivo in RAIZ_BACKEND.glob(patron):
            if ".venv" in archivo.parts or "migrations" in archivo.parts:
                continue
            # Este mismo archivo queda fuera: sus ejemplos citan
            # identificadores inventados a proposito, y contarlos daria
            # falsos positivos en ambas direcciones.
            if archivo.name == Path(__file__).name:
                continue
            piezas.append(archivo.read_text(encoding="utf-8", errors="ignore"))

    frontend = RAIZ_PROYECTO / "frontend" / "src"
    for patron in ("**/*.js", "**/*.vue"):
        for archivo in frontend.glob(patron):
            piezas.append(archivo.read_text(encoding="utf-8", errors="ignore"))

    return "\n".join(piezas)


TEXTO = _texto_del_proyecto()
FUNCIONALES = _requerimientos_declarados("RF")
NO_FUNCIONALES = _requerimientos_declarados("RNF")


def test_la_especificacion_declara_los_requerimientos_esperados():
    """Cifra de control: si cambia, es que se anadio o quito alguno."""
    # 66 hasta spec.md v1.2; 68 desde la v1.3, que anade el informe en
    # PDF de la solicitud de servicio (RF-67, RF-68).
    assert len(FUNCIONALES) == 68, f"RF declarados: {len(FUNCIONALES)}"
    assert len(NO_FUNCIONALES) == 23, f"RNF declarados: {len(NO_FUNCIONALES)}"


@pytest.mark.parametrize("requerimiento", FUNCIONALES)
def test_cada_requerimiento_funcional_esta_citado_en_el_codigo(requerimiento):
    """RNF-22: la especificacion y el codigo no deben divergir."""
    assert requerimiento in TEXTO, (
        f"{requerimiento} está declarado en spec.md pero no se cita en "
        f"ninguna parte del código ni de las pruebas. O falta "
        f"implementarlo, o falta anotar dónde quedó."
    )


@pytest.mark.parametrize("requerimiento", NO_FUNCIONALES)
def test_cada_requerimiento_no_funcional_esta_citado_en_el_codigo(requerimiento):
    assert requerimiento in TEXTO, (
        f"{requerimiento} está declarado en spec.md pero no se cita en "
        f"ninguna parte del código ni de las pruebas."
    )


def test_no_se_citan_requerimientos_que_la_especificacion_no_declara():
    """El error inverso, y más sutil.

    Un RF-99 citado en un comentario significa que alguien implementó
    algo creyendo que estaba en la especificación, o que el requisito
    se eliminó de spec.md y quedó la referencia huérfana. Las dos cosas
    son señales de divergencia.
    """
    citados = set(re.findall(r"\bRF-(\d+)\b", TEXTO))
    declarados = {r.split("-")[1] for r in FUNCIONALES}

    inventados = {f"RF-{n}" for n in citados - declarados}

    assert not inventados, (
        f"El código cita requerimientos que spec.md no declara: "
        f"{sorted(inventados)}"
    )


def test_las_reglas_de_negocio_citadas_existen_en_la_especificacion():
    """Lo mismo para las RN, que son las que más se citan en el código."""
    spec = SPEC.read_text(encoding="utf-8")
    declaradas = set(re.findall(r"\*\*(RN-[A-Z]+-\d+)\*\*", spec))
    citadas = set(re.findall(r"\bRN-[A-Z]+-\d+\b", TEXTO))

    huerfanas = citadas - declaradas

    assert not huerfanas, (
        f"El código cita reglas que spec.md ya no declara: "
        f"{sorted(huerfanas)}. Probablemente se eliminaron en una "
        f"revisión y quedó la referencia."
    )
