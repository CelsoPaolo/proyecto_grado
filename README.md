# PC-Solution ERP

Sistema ERP interno para **PC-Solution** (Sucre, Bolivia). Proyecto de
grado.

Centraliza la operación interna de la empresa: catálogo e inventario,
registro de ventas, seguimiento de servicios técnicos, gestión de las
cuentas del personal y un panel de indicadores.

> **Uso exclusivamente interno.** Solo el personal de PC-Solution accede
> al sistema, siempre con una cuenta creada por un administrador. No hay
> portal de clientes, ni registro público, ni carrito de compras, ni
> checkout. Los clientes se registran únicamente como datos de contacto
> (nombre y teléfono) dentro de una venta o de una solicitud de servicio.

---

## Metodología: Spec-Driven Development

La especificación escrita es la **fuente de verdad** del proyecto; el
código es un artefacto que se genera a partir de ella, no al revés.

| Documento | Etapa | Contenido |
|---|---|---|
| [`specs/spec.md`](specs/spec.md) | 1 — Especificación | Actores, casos de uso, requerimientos y reglas de negocio. Sin detalles de implementación. |
| [`specs/plan.md`](specs/plan.md) | 2 — Plan técnico | Arquitectura, modelo de datos, diseño de la API, decisiones tecnológicas. |
| [`specs/tasks.md`](specs/tasks.md) | 3 — Tareas | 73 tareas atómicas ordenadas por dependencia, con sus criterios de verificación. |

Son **documentos vivos**: si algo cambia, se edita primero la
especificación correspondiente y luego se ajusta el código. Cada commit
cita el identificador de la tarea que implementa (`T-4.3`), de modo que
el historial de Git sea trazable contra la especificación.

---

## Stack técnico

| Ámbito | Tecnología |
|---|---|
| Backend | Python 3.13 · Django 5.1 · Django REST Framework 3.15 |
| Base de datos | PostgreSQL 18 |
| Autenticación | JWT (`djangorestframework-simplejwt`) con revocación inmediata |
| Frontend | Vue 3 · Vite 5 · Pinia · Vue Router · PrimeVue 4 |
| Pruebas | pytest + pytest-django (backend) · Vitest (frontend) |

Frontend y backend son **aplicaciones separadas** que se comunican
exclusivamente por la API REST. El frontend nunca accede a la base de
datos directamente.

---

## Estructura del repositorio

```
proyecto_grado_definitivo/
├── specs/            # Especificación, plan técnico y tareas
├── backend/          # API REST (Django + DRF)
└── frontend/         # SPA (Vue 3 + Vite)
```

---

## Puesta en marcha

### Requisitos previos

- Python 3.12 o superior
- Node.js 20 o superior
- PostgreSQL 16 o superior, corriendo localmente

### 1. Base de datos

El proyecto espera una base PostgreSQL y un usuario propios. Ver
[`backend/.env.example`](backend/.env.example) para los valores que
utiliza.

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash)
# source .venv/bin/activate        # Linux / macOS

pip install -r requirements/dev.txt

cp .env.example .env               # y completar los valores
python manage.py migrate
python manage.py createsuperuser   # crea el primer administrador
python manage.py runserver
```

La API queda en `http://localhost:8000/api/v1/`.

> **El primer administrador.** El sistema recién instalado está vacío, y
> solo un administrador puede crear cuentas. `createsuperuser` resuelve
> ese arranque asignando el rol de administrador automáticamente; es un
> comando de consola que se ejecuta una sola vez al preparar el equipo.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

La aplicación queda en `http://localhost:5173`.

---

## Pruebas

```bash
cd backend  && pytest              # incluye la prueba de concurrencia
cd frontend && npm run test
```

La prueba de concurrencia de existencias requiere **PostgreSQL real**: es
la evidencia de que dos ventas simultáneas nunca dejan el stock en
negativo, y no puede demostrarse contra SQLite.

---

## Alcance de esta entrega

Este proyecto está preparado para ejecutarse en **entorno de
desarrollo**, que es lo requerido para la defensa del proyecto de grado.

Para un despliegue real en la empresa harían falta, al menos:

- `DEBUG = False` y `ALLOWED_HOSTS` explícito
- Servidor WSGI (Gunicorn o similar) detrás de un servidor web
- HTTPS con `SECURE_SSL_REDIRECT` y cookies `Secure`
- Recolección y servido de archivos estáticos y de `media/`
- Copias de seguridad programadas de la base de datos

Nada de esto está implementado ni configurado.
