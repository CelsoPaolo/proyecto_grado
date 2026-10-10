"""Importa una sola vez el catalogo del proyecto anterior (plan.md 11.3).

Por defecto solo INFORMA, sin escribir nada:

    python manage.py importar_catalogo \\
        --productos datos_importacion/catalogo_anterior/productos.csv \\
        --categorias datos_importacion/catalogo_anterior/categorias.csv \\
        --imagenes <carpeta con las imagenes> \\
        --diferencias datos_importacion/catalogo_anterior/diferencias_con_seeder.csv

Con --planilla-recuento <archivo> escribe, ademas, la planilla para el
recuento fisico. Con --existencias <planilla rellenada> incluye la
carga de existencias contadas en el informe y en la huella.

Para importar, la misma orden con --aplicar --huella <la del informe
aprobado> --usuario <administrador>. Si la huella no coincide, no se
importa nada.

Recuento posterior (T-OP.5): --planilla-importados <archivo> escribe la
planilla de los productos ya importados; --solo-existencias <planilla>
informa, y con --aplicar --huella --usuario carga los ajustes «Carga
inicial» y, si los trae, los meses de garantia.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from catalogo import importacion, recuento
from usuarios.models import Rol, Usuario


class Command(BaseCommand):
    help = "Importa una sola vez el catálogo del proyecto anterior (por defecto, solo informa)."

    def add_arguments(self, parser):
        parser.add_argument("--productos", required=True, help="productos.csv exportado")
        parser.add_argument("--categorias", help="categorias.csv exportado (obligatorio al importar)")
        parser.add_argument("--imagenes", help="carpeta base de las rutas de la columna imagen")
        parser.add_argument("--mapa-categorias", help="CSV origen,destino para fusionar categorías")
        parser.add_argument("--diferencias", help="diferencias_con_seeder.csv, para marcarlas en el informe")
        parser.add_argument(
            "--fusionar-categorias",
            help="CSV existente,nombre_final: renombra la categoría existente y fusiona en ella",
        )
        parser.add_argument("--planilla-recuento", help="escribe aquí la planilla para el recuento")
        parser.add_argument("--existencias", help="planilla de recuento rellenada")
        # T-OP.5: recuento de productos ya importados.
        parser.add_argument(
            "--planilla-importados", help="escribe la planilla de recuento de los productos ya importados"
        )
        parser.add_argument(
            "--solo-existencias", help="carga la planilla rellenada en productos ya importados"
        )
        parser.add_argument("--salida", help="guarda también el informe en este archivo")
        parser.add_argument("--aplicar", action="store_true", help="aplica (exige --huella y --usuario)")
        parser.add_argument("--huella", help="la huella del informe aprobado")
        parser.add_argument("--usuario", help="nombre de usuario del Administrador que aplica")

    def handle(self, *args, **opciones):
        if opciones["planilla_importados"]:
            n = recuento.escribir_planilla_importados(opciones["productos"], opciones["planilla_importados"])
            self.stdout.write(f"Planilla de {n} productos importados escrita en {opciones['planilla_importados']}")
            return
        if opciones["solo_existencias"]:
            return self._solo_existencias(opciones)
        return self._importar(opciones)

    # ── Comun ───────────────────────────────────────────────────────
    def _mostrar(self, texto, opciones):
        # El archivo primero: si la consola no pudiera mostrar algun
        # caracter, el informe ya estaria guardado.
        if opciones["salida"]:
            with open(opciones["salida"], "w", encoding="utf-8") as archivo:
                archivo.write(texto + "\n")
        self.stdout.write(texto)

    def _administrador(self, opciones):
        if not opciones["huella"] or not opciones["usuario"]:
            raise CommandError("--aplicar exige --huella y --usuario.")
        usuario = Usuario.objects.filter(username=opciones["usuario"], is_active=True).first()
        if usuario is None or usuario.rol != Rol.ADMINISTRADOR:
            raise CommandError("--usuario debe ser un Administrador activo.")
        return usuario

    # ── Importacion (T-OP.2) ────────────────────────────────────────
    def _importar(self, opciones):
        if not opciones["categorias"]:
            raise CommandError("Para importar hace falta --categorias.")
        try:
            plan = importacion.construir_plan(
                opciones["productos"],
                opciones["categorias"],
                imagenes=opciones["imagenes"],
                mapa_categorias=opciones["mapa_categorias"],
                diferencias_csv=opciones["diferencias"],
                existencias_csv=opciones["existencias"],
                fusiones_csv=opciones["fusionar_categorias"],
            )
        except (OSError, ValueError, KeyError) as error:
            raise CommandError(f"No se pudieron leer los datos de origen: {error}") from error

        self._mostrar(importacion.informe(plan, fecha_de_ejecucion=timezone.localdate().isoformat()), opciones)

        if opciones["planilla_recuento"]:
            importacion.escribir_planilla(plan, opciones["planilla_recuento"])
            self.stdout.write(f"\nPlanilla de recuento escrita en {opciones['planilla_recuento']}")

        if not opciones["aplicar"]:
            self.stdout.write("\nModo informe: no se escribió nada en la base.")
            return

        usuario = self._administrador(opciones)
        try:
            creados = importacion.aplicar(plan, huella=opciones["huella"], usuario=usuario)
        except importacion.HuellaNoCoincide as error:
            raise CommandError(str(error)) from error

        cargados = sum(1 for p in plan.a_importar if p["existencias"])
        self.stdout.write(self.style.SUCCESS(
            f"\nImportados {len(creados)} productos; existencias cargadas en {cargados}."
        ))

    # ── Recuento posterior (T-OP.5) ─────────────────────────────────
    def _solo_existencias(self, opciones):
        try:
            plan = recuento.construir_plan(opciones["productos"], opciones["solo_existencias"])
        except (OSError, ValueError, KeyError) as error:
            raise CommandError(f"No se pudo leer la planilla: {error}") from error

        self._mostrar(recuento.informe(plan, fecha_de_ejecucion=timezone.localdate().isoformat()), opciones)

        if not opciones["aplicar"]:
            self.stdout.write("\nModo informe: no se escribió nada en la base.")
            return

        usuario = self._administrador(opciones)
        try:
            recuento.aplicar(plan, huella=opciones["huella"], usuario=usuario)
        except importacion.HuellaNoCoincide as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(
            f"\nAjustes «Carga inicial»: {len(plan.ajustes)}; meses de garantía cambiados: {len(plan.meses)}."
        ))
