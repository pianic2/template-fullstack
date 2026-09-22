# Production deployment

Build `infra/docker/Dockerfile.backend` and `infra/docker/Dockerfile.web` as separate images. Backend starts Gunicorn as UID 10001; static web is served by unprivileged Nginx on port 8080. Build the web image with a public, HTTPS `VITE_API_BASE_URL` pointing to the versioned API.

Provision managed PostgreSQL, inject `DJANGO_SECRET_KEY` from a secret manager, set `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS` and `DJANGO_CSRF_TRUSTED_ORIGINS` explicitly, then terminate TLS at a trusted proxy and configure forwarded-proto handling. Run `python manage.py migrate` as a release job before deploying backend workers. Do not run migrations at startup.

Run `python manage.py check --deploy --settings=config.settings.production` in CI with production-shaped placeholder values. The service must have a readiness probe against `/api/v1/health/ready`. Configure backups, restore tests, log retention, upload scanning and provider-specific resource limits outside this template. No cloud credentials are required for development.
