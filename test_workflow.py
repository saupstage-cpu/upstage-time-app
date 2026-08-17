import base64
from io import BytesIO
from PIL import Image
from app import app, db, Attendance, TimesheetApproval


def tiny_image_data_url(color=(0, 128, 255)):
    img = Image.new('RGB', (8, 8), color)
    buf = BytesIO()
    img.save(buf, format='JPEG')
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def run():
    client = app.test_client()
    client.post('/login', data={'email': 'alex@upstageco.test', 'password': 'Pass123!'}, follow_redirects=True)
    job_id = 1
    photo = tiny_image_data_url()
    res = client.post('/api/attendance/time-in', json={'job_id': job_id, 'photo_data': photo, 'lat': -37.8136, 'lng': 144.9631, 'address': 'Melbourne VIC', 'client_time': '2026-08-17T08:02:00+00:00'})
    print('time-in', res.status_code, res.json)
    res = client.post('/api/attendance/start-break', json={'lat': -37.8136, 'lng': 144.9631, 'address': 'Melbourne VIC'})
    print('start-break', res.status_code, res.json)
    res = client.post('/api/attendance/end-break', json={'lat': -37.8136, 'lng': 144.9631, 'address': 'Melbourne VIC'})
    print('end-break', res.status_code, res.json)
    res = client.post('/api/worklogs', json={'task': 'Built stage decks', 'start_at': '2026-08-17T08:00:00+00:00', 'end_at': '2026-08-17T10:30:00+00:00', 'notes': 'Completed 6 units'})
    print('worklog', res.status_code, res.json)
    res = client.post('/api/attendance/time-out', json={'photo_data': photo, 'final_photo_data': photo, 'summary': 'Completed installation and pack down prep', 'lat': -37.8136, 'lng': 144.9631, 'address': 'Melbourne VIC', 'client_time': '2026-08-17T16:15:00+00:00'})
    print('time-out', res.status_code, res.json)
    res = client.post('/api/timesheet/submit')
    print('submit-timesheet', res.status_code, res.json)
    client.get('/logout')

    client.post('/login', data={'email': 'admin@upstageco.test', 'password': 'Admin123!'}, follow_redirects=True)
    with app.app_context():
        latest = Attendance.query.order_by(Attendance.id.desc()).first()
        approval = TimesheetApproval.query.filter_by(user_id=latest.user_id).order_by(TimesheetApproval.id.desc()).first()
        aid = latest.id
        tid = approval.id
    res = client.post(f'/api/admin/attendance/{aid}/approve', json={'note': 'Approved in automated test'})
    print('approve-attendance', res.status_code, res.json)
    res = client.post(f'/api/admin/timesheets/{tid}/review', json={'status': 'approved', 'note': 'Payroll ready'})
    print('approve-timesheet', res.status_code, res.json)
    res = client.post('/api/admin/xero/sync')
    print('xero-sync', res.status_code, res.json)


if __name__ == '__main__':
    run()
