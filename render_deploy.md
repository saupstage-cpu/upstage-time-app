# Render deployment

## Ready-to-use settings

- Service type: Web Service
- Runtime: Python 3
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

## Click-by-click

1. Create a GitHub repository and upload all files from this package.
2. Sign in to Render.
3. Click **New** -> **Web Service**.
4. Connect the GitHub repository.
5. Confirm the runtime is Python.
6. Use the build and start commands above.
7. Click **Deploy Web Service**.
8. After deployment, open the generated `onrender.com` URL on desktop or mobile.

## Notes

- Render gives the service a public URL.
- This package uses Gunicorn for production startup.
- For persistent production data, attach PostgreSQL instead of relying on SQLite.
- Camera and location prompts work best from the live HTTPS site on a phone.
