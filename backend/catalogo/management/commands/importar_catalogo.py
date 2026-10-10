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
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from catalogo import importacion
from usuarios.models import Rol, Usuario


class Command(BaseCommand):
    help = "Importa una sola vez el catálogo del proyecto anterior (por defecto, solo informa)."

    def add_arguments(self, parser):
        parser.add_argument("--productos", required=True, help="productos.csv exportado")
        parser.add_argument("--categorias", required=True, help="categorias.csv exportado")
        parser.add_argument("--imagenes", help="carpeta base de las rutas de la columna imagen")
        parser.add_argument("--mapa-categorias", help="CSV origen,destino para fusionar categorías")
        parser.add_argument("--diferencias", help="diferencias_con_seeder.csv, para marcarlas en el informe")
        parser.add_argument("--planilla-recuento", help="escribe aquí la planilla para el recuento")
        parser.add_argument("--existencias", help="planilla de recuento rellenada")
        parser.add_argument("--salida", help="guarda también el informe en este archivo")
        parser.add_argument("--aplicar", action="store_true", help="importa (exige --huella y --usuario)")
        parser.add_argument("--huella", help="la huella del informe aprobado")
        parser.add_argument("--usuario", help="nombre de usuario del Administrador que importa")

    def handle(self, *args, **opciones):
        try:
            plan = importacion.construir_plan(
                opciones["productos"],
                opciones["categorias"],
                imagenes=opciones["imagenes"],
                mapa_categorias=opciones["mapa_categorias"],
                diferencias_csv=opciones["diferencias"],
                existencias_csv=opciones["existencias"],
            )
        except (OSError, ValueError, KeyError) as error:
            raise CommandError(f"No se pudieron leer los datos de origen: {error}") from error

        texto = importacion.informe(plan, fecha_de_ejecucion=timezone.localdate().isoformat())
        # El archivo primero: si la consola no pudiera mostrar algun
        # caracter, el informe ya estaria guardado.
        if opciones["salida"]:
            with open(opciones["salida"], "w", encoding="utf-8") as archivo:
                archivo.write(texto + "\n")
        self.stdout.write(texto)

        if opciones["planilla_recuento"]:
            importacion.escribir_planilla(plan, opciones["planilla_recuento"])
            self.stdout.write(f"\nPlanilla de recuento escrita en {opciones['planilla_recuento']}")

        if not opciones["aplicar"]:
            self.stdout.write("\nModo informe: no se escribió nada en la base.")
            return

        if not opciones["huella"] or not opciones["usuario"]:
            raise CommandError("--aplicar exige --huella y --usuario.")
        usuario = Usuario.objects.filter(username=opciones["usuario"], is_active=True).first()
        if usuario is None or usuario.rol != Rol.ADMINISTRADOR:
            raise CommandError("--usuario debe ser un Administrador activo.")

        try:
            creados = importacion.aplicar(plan, huella=opciones["huella"], usuario=usuario)
        except importacion.HuellaNoCoincide as error:
            raise CommandError(str(error)) from error

        cargados = sum(1 for p in plan.a_importar if p["existencias"])
        self.stdout.write(self.style.SUCCESS(
            f"\nImportados {len(creados)} productos; existencias cargadas en {cargados}."
        ))
