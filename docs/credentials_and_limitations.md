# External credentials required

- Xero OAuth application credentials for real payroll sync
- Maps / reverse-geocoding provider if readable addresses and maps should be production-grade
- Push notification credentials for FCM/APNs
- Cloud object storage credentials for secure photo storage
- SMTP / transactional email provider for password reset emails

# Current limitations / assumptions

- This deliverable is a deployable web application and mobile-first PWA demo, not a signed App Store / Play Store binary.
- Native Android/iOS store builds require Apple and Google developer accounts, signing assets and device testing.
- Offline mode stores pending actions in browser local storage for this demo. A production mobile shell should move this to an encrypted on-device store.
- Reverse geocoding currently falls back to latitude/longitude text unless an external geocoder is connected.
- Real push notifications are scaffolded conceptually but not wired to FCM/APNs in this demo.
- Xero sync is staged and documented, but live payroll transmission requires tenant-specific credentials and payroll setup.



Country-wide GPS allowlist is now enabled for anywhere in Australia and anywhere in the Philippines, including Cebu.
