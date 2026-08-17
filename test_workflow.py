import base64
from io import BytesIO
from PIL import Image
from app import app, Attendance, TimesheetApproval, User, Job, JobAssignment


def tiny_image_data_url(color=(0, 128, 255)):
    img = Image.new('RGB', (8, 8), color)
    buf = BytesIO()
    img.save(buf, format='JPEG')
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def run():
    client = app.test_client()
    # employee attendance flow
    client.post('/login', data={'email': 'alex@upstageco.test', 'password': 'Pass123!'}, follow_redirects=True)
    job_id = 1
    photo = tiny_image_data_url()
    print('time-in', client.post('/api/attendance/time-in', json={'job_id': job_id, 'photo_data': photo, 'lat': -33.8688, 'lng': 151.2093, 'address': 'Sydney NSW', 'client_time': '2026-08-17T08:02:00+00:00'}).status_code)
    print('start-break', client.post('/api/attendance/start-break', json={'lat': -33.8688, 'lng': 151.2093, 'address': 'Sydney NSW'}).status_code)
    print('end-break', client.post('/api/attendance/end-break', json={'lat': -33.8688, 'lng': 151.2093, 'address': 'Sydney NSW'}).status_code)
    print('worklog', client.post('/api/worklogs', json={'task': 'Built stage decks', 'start_at': '2026-08-17T08:00:00+00:00', 'end_at': '2026-08-17T10:30:00+00:00', 'notes': 'Completed 6 units'}).status_code)
    print('time-out', client.post('/api/attendance/time-out', json={'photo_data': photo, 'final_photo_data': photo, 'summary': 'Completed installation and pack down prep', 'lat': -33.8688, 'lng': 151.2093, 'address': 'Sydney NSW', 'client_time': '2026-08-17T16:15:00+00:00'}).status_code)
    print('submit-timesheet', client.post('/api/timesheet/submit').status_code)
    client.get('/logout')

    # admin management flow
    client.post('/login', data={'email': 'admin@upstageco.test', 'password': 'Admin123!'}, follow_redirects=True)
    create_emp = client.post('/api/admin/employees', json={
        'full_name': 'Test Crew',
        'email': 'testcrew@upstageco.test',
        'password': 'Crew123!',
        'department': 'Workshop',
        'pay_category': 'Ordinary Hours',
        'job_ids': [1, 2]
    })
    print('create-employee', create_emp.status_code)
    emp_id = create_emp.get_json()['id']
    print('update-employee', client.post(f'/api/admin/employees/{emp_id}/update', json={'full_name': 'Test Crew Updated', 'email': 'testcrew@upstageco.test', 'department': 'Events', 'pay_category': 'Overtime Eligible', 'active': True}).status_code)
    print('reset-password', client.post(f'/api/admin/employees/{emp_id}/reset-password', json={'password': 'NewPass123!'}).status_code)
    print('employee-assignments', client.post(f'/api/admin/employees/{emp_id}/assignments', json={'job_ids': [3]}).status_code)
    create_job = client.post('/api/admin/jobs', json={
        'job_number': '2026-999',
        'name': 'Billboard Simple Test Job',
        'client': 'Upstage Client',
        'venue': 'Main Venue',
        'location': 'Cebu',
        'manager_name': 'Alex Rosemont',
        'start_date': '2026-08-17',
        'end_date': '2026-08-18',
        'status': 'Active',
        'notes': 'Test notes',
        'employee_ids': [emp_id]
    })
    print('create-job', create_job.status_code)
    job_id_new = create_job.get_json()['id']
    print('update-job', client.post(f'/api/admin/jobs/{job_id_new}/update', json={'job_number': '2026-999', 'name': 'Billboard Simple Test Job 2', 'client': 'Upstage Client', 'venue': 'Main Venue', 'location': 'Anywhere Australia', 'manager_name': 'Alex Rosemont', 'start_date': '2026-08-17', 'end_date': '2026-08-20', 'status': 'Planned', 'notes': 'Updated'}).status_code)
    print('job-assignments', client.post(f'/api/admin/jobs/{job_id_new}/assignments', json={'employee_ids': [emp_id, 1]}).status_code)

    with app.app_context():
        latest = Attendance.query.order_by(Attendance.id.desc()).first()
        approval = TimesheetApproval.query.filter_by(user_id=latest.user_id).order_by(TimesheetApproval.id.desc()).first()
        aid = latest.id
        tid = approval.id
        assert User.query.filter_by(id=emp_id).first().full_name == 'Test Crew Updated'
        assert Job.query.filter_by(id=job_id_new).first().name == 'Billboard Simple Test Job 2'
        assert JobAssignment.query.filter_by(user_id=emp_id, job_id=job_id_new).first() is not None
    print('approve-attendance', client.post(f'/api/admin/attendance/{aid}/approve', json={'note': 'Approved in automated test'}).status_code)
    print('approve-timesheet', client.post(f'/api/admin/timesheets/{tid}/review', json={'status': 'approved', 'note': 'Payroll ready'}).status_code)
    print('xero-sync', client.post('/api/admin/xero/sync').status_code)


if __name__ == '__main__':
    run()
