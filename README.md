# Upstage Time

Upstage Time is a mobile-first employee time, attendance, location and job-tracking application built as a deployable Flask web app with an employee experience optimized for phones and an admin dashboard optimized for browser use.

## Included deliverables

- Installable mobile PWA interface for:
  - secure login
  - job selection
  - Time In / Start Break / End Break / Time Out
  - photo capture using mobile camera intent
  - GPS capture on attendance events
  - work log entry
  - weekly timesheet submission
  - offline queue with pending sync
- Admin web dashboard for:
  - live status
  - attendance review
  - timesheet approvals
  - job management
  - employee list
  - reports export (CSV/PDF)
  - audit log
  - settings
  - Xero sync staging screen
- Backend:
  - SQLite demo database with SQLAlchemy ORM
  - audit logging
  - break calculations
  - geofence status calculation
  - seeded demo data for Upstage Co
- Documentation:
  - API documentation page and markdown docs
  - database schema notes
  - deployment instructions
  - admin and employee guides
  - credentials/limitations list

## Quick start

```bash
pip install -r requirements.txt
python3 app.py
```

Open `http://127.0.0.1:5000/login`

## Demo accounts

- Admin: `admin@upstageco.test` / `Admin123!`
- Employee: `alex@upstageco.test` / `Pass123!`

All employee demo passwords: `Pass123!`

## Key implementation notes

- Attendance timestamps are server-recorded when online.
- When offline, the client stores pending actions locally and uploads them when connectivity returns.
- Photos are stored under `static/uploads/` in this demo.
- Geofence is soft by default: outside-geofence events are flagged rather than blocked.
- Break rules are preconfigured to match:
  - Morning tea (smoko): 20 minutes paid
  - Lunch: 30 minutes unpaid
- Approved attendance is intended to be locked from employee edits.
- Xero sync is scaffolded for OAuth and payroll timesheet payload preparation; real tenant credentials are required for live sync.
- PWA install support is included so staff can add the app to their iPhone/Android home screen.
- Branding is configurable from Admin Settings: logo upload, company name, primary color, secondary color.

## Production hardening recommended before go-live

- replace SQLite with PostgreSQL
- move photo storage to S3 / GCS / Azure Blob
- add background workers for notifications and sync retries
- add real push notification providers (FCM/APNs)
- add MDM-safe device compliance and biometric/PIN login modules
- add signed mobile wrappers (Capacitor or React Native / Flutter) for app store release
- add a reverse-geocoding provider and maps tiles/API as needed



## Regional GPS defaults

The package now includes approved geofence defaults for Sydney, Australia and Cebu, Philippines for multi-country team attendance capture.


Country-wide GPS allowlist is now enabled for anywhere in Australia and anywhere in the Philippines, including Cebu.


Branding update: this package now uses the uploaded official Upstage logo asset and a monochrome black/charcoal theme derived from the supplied logo file.


Hosting update: this package is now Render-ready with a Procfile, `render.yaml`, Gunicorn startup, and dynamic `PORT` support.
