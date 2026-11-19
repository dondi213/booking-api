# Guía rápida: Booking API (Proyecto 5, el integrador)

Este es el proyecto que vas a presumir en entrevistas: **tiene que estar desplegado** con una URL pública.

## Correrlo

```bash
docker compose up --build
docker compose exec api python -m app.create_admin admin@example.com "admin12345"
```

En http://localhost:8000/docs:
1. Inicia sesión como admin (botón **Authorize**) y crea un recurso con `POST /resources`.
2. Registra otro usuario, inicia sesión con él y crea una reserva.
3. Intenta reservar el mismo horario con otro usuario: debe responder **409**.

Las fechas deben llevar zona horaria. Para Ciudad de México usa `-06:00`, por ejemplo `2026-12-01T16:00:00-06:00`.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Desplegarlo en Render (gratis)

Sigue la sección **Deployment** del README. Resumen:
1. Sube el repo a GitHub.
2. En render.com: **New → Blueprint** → elige el repo.
3. Copia el **Deploy Hook** del servicio y guárdalo en GitHub como secret `RENDER_DEPLOY_HOOK_URL`.
4. Haz un push a `main`: GitHub Actions corre las pruebas y, si pasan, despliega.
5. Pon la URL pública en el README y en tu CV.

Nota: en el plan gratuito, el servicio "se duerme" tras un rato sin uso; la primera petición tarda ~1 minuto en despertar. La base de datos gratuita de Render puede expirar después de un tiempo: revisa los términos vigentes en su sitio.

## Qué debes poder explicar en una entrevista

- **Solapamiento de horarios:** por qué la condición es `inicio_existente < fin_nuevo AND fin_existente > inicio_nuevo`.
- **Condición de carrera:** por qué revisar en el código no basta y qué hace la restricción `EXCLUDE` de PostgreSQL.
- **Zonas horarias:** por qué se guarda todo en UTC y se rechazan fechas sin zona horaria.
- **Migraciones:** qué hace `alembic upgrade head` y por qué el CI prueba también el `downgrade`.
- **CI/CD:** qué jobs corre GitHub Actions y por qué el deploy solo ocurre si todo pasa.
- **Configuración:** por qué los secretos van en variables de entorno y nunca en el código.

## Retos para hacerlo tuyo

1. **Fácil:** horario de apertura por recurso (por ejemplo, solo de 8:00 a 22:00).
2. **Fácil:** que el admin pueda desactivar recursos (`PATCH /resources/{id}`).
3. **Medio:** endpoint que devuelva los **huecos libres** del día, no solo los ocupados.
4. **Medio:** límite de reservas activas por usuario (por ejemplo, máximo 3).
5. **Avanzado:** enviar un correo de confirmación usando tu `notifications-service` (proyecto 4).
