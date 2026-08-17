# Deployment instructions

## Recommended production stack

- App server: Gunicorn + Nginx
- Database: PostgreSQL
- File storage: S3-compatible object storage
- Reverse proxy TLS: Nginx / Cloudflare
- Background jobs: Celery / RQ
- Observability: Sentry + structured logs

## Environment variables

- `SECRET_KEY`
- `DATABASE_URL` (if moving from SQLite)
- `XERO_CLIENT_ID`
- `XERO_CLIENT_SECRET` (server-side only)
- `XERO_REDIRECT_URI`
- `MAPS_API_KEY` (if using Google Maps or Mapbox)
- `PUSH_FCM_SERVER_KEY`
- `APNS_KEY_ID`
- `APNS_TEAM_ID`
- `APNS_PRIVATE_KEY`
- `STORAGE_BUCKET`
- `STORAGE_ACCESS_KEY`
- `STORAGE_SECRET_KEY`

## Minimal production changes

1. swap SQLite to PostgreSQL
2. disable Flask debug mode
3. serve uploads from private object storage via signed URLs
4. add CSRF protection and rate limiting
5. add password reset email provider
6. add HTTPS-only cookie configuration
7. add worker for reminder notifications and sync monitoring
8. package as a PWA or native wrapper for app stores

