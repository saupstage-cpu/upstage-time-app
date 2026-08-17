# Database schema

Core tables implemented in the demo application:

- `user`
  - role-based access (`employee`, `admin`)
  - department, pay category, Xero employee mapping
- `company_settings`
  - timezone, geofence, break rules, retention rules
- `job`
  - job number, client, venue, location, manager, dates, status
- `job_assignment`
  - employee-to-job assignment bridge
- `attendance`
  - time in/out, photos, device/server timestamps, GPS, addresses, job link, approval state, geofence flag, net minutes
- `break_entry`
  - multiple breaks per attendance record
- `work_log`
  - employee task notes, start/finish, photos JSON
- `timesheet_approval`
  - weekly submission and review state
- `notification`
  - user-specific messages and status indicators
- `audit_log`
  - actor, action, entity, before/after detail JSON
- `xero_sync_log`
  - outbound sync packaging and response trace

Recommended production additions:

- normalized `photo` table
- normalized `location_event` table
- `password_reset_token`
- `session` or refresh-token table
- `device_registration` for push and biometrics
- `pay_category`, `department`, `leave_type` reference tables
- `webhook_delivery_log`

