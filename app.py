import base64
import csv
import io
import json
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
DB_PATH = BASE_DIR / "upstage.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JSON_SORT_KEYS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")
    active = db.Column(db.Boolean, default=True)
    department = db.Column(db.String(100), default="Operations")
    pay_category = db.Column(db.String(100), default="Ordinary Hours")
    xero_employee_id = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class CompanySettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(120), default="Upstage Co")
    logo_path = db.Column(db.String(255), default="branding/upstage-company-logo.jpg")
    primary_color = db.Column(db.String(20), default="#111111")
    secondary_color = db.Column(db.String(20), default="#444444")
    timezone = db.Column(db.String(50), default="Australia/Melbourne")
    work_week = db.Column(db.String(50), default="Mon-Fri")
    standard_daily_hours = db.Column(db.Float, default=8.0)
    required_photo = db.Column(db.Boolean, default=True)
    required_gps = db.Column(db.Boolean, default=True)
    geofence_enabled = db.Column(db.Boolean, default=True)
    strict_geofence = db.Column(db.Boolean, default=False)
    geofence_name = db.Column(db.String(120), default="Upstage Workshop")
    geofence_lat = db.Column(db.Float, default=-37.8136)
    geofence_lng = db.Column(db.Float, default=144.9631)
    geofence_radius_m = db.Column(db.Float, default=200.0)
    late_threshold_minutes = db.Column(db.Integer, default=10)
    overtime_threshold_hours = db.Column(db.Float, default=8.0)
    paid_break_minutes = db.Column(db.Integer, default=20)
    unpaid_break_minutes = db.Column(db.Integer, default=30)
    allow_gallery_upload = db.Column(db.Boolean, default=False)
    retention_days = db.Column(db.Integer, default=365)
    enable_break_photo = db.Column(db.Boolean, default=False)


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    client = db.Column(db.String(120), nullable=False)
    venue = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    manager_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default="Active")
    notes = db.Column(db.Text, default="")


class JobAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)


class GeofenceSite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    country = db.Column(db.String(80), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    timezone_name = db.Column(db.String(80), nullable=False, default="Australia/Sydney")
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    radius_m = db.Column(db.Float, nullable=False, default=300.0)
    active = db.Column(db.Boolean, default=True)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attendance_uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    status = db.Column(db.String(50), default="working")
    date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    time_in_at = db.Column(db.DateTime, nullable=False)
    time_out_at = db.Column(db.DateTime, nullable=True)
    time_in_device_at = db.Column(db.DateTime, nullable=True)
    time_out_device_at = db.Column(db.DateTime, nullable=True)
    offline_time_in = db.Column(db.Boolean, default=False)
    offline_time_out = db.Column(db.Boolean, default=False)
    time_in_photo = db.Column(db.String(255), nullable=True)
    time_out_photo = db.Column(db.String(255), nullable=True)
    time_in_lat = db.Column(db.Float, nullable=True)
    time_in_lng = db.Column(db.Float, nullable=True)
    time_out_lat = db.Column(db.Float, nullable=True)
    time_out_lng = db.Column(db.Float, nullable=True)
    time_in_address = db.Column(db.String(255), nullable=True)
    time_out_address = db.Column(db.String(255), nullable=True)
    time_in_device = db.Column(db.String(255), nullable=True)
    time_out_device = db.Column(db.String(255), nullable=True)
    work_summary = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")
    final_job_photo = db.Column(db.String(255), nullable=True)
    total_break_minutes = db.Column(db.Integer, default=0)
    paid_break_minutes = db.Column(db.Integer, default=0)
    unpaid_break_minutes = db.Column(db.Integer, default=0)
    net_minutes = db.Column(db.Integer, default=0)
    approval_status = db.Column(db.String(50), default="draft")
    approver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    approval_note = db.Column(db.Text, default="")
    approved_at = db.Column(db.DateTime, nullable=True)
    geofence_status = db.Column(db.String(30), default="unknown")
    last_synced_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    edited_after_approval = db.Column(db.Boolean, default=False)


class BreakEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey("attendance.id"), nullable=False)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=True)
    start_lat = db.Column(db.Float, nullable=True)
    start_lng = db.Column(db.Float, nullable=True)
    end_lat = db.Column(db.Float, nullable=True)
    end_lng = db.Column(db.Float, nullable=True)
    start_address = db.Column(db.String(255), nullable=True)
    end_address = db.Column(db.String(255), nullable=True)
    photo_path = db.Column(db.String(255), nullable=True)
    duration_minutes = db.Column(db.Integer, default=0)


class WorkLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey("attendance.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    task = db.Column(db.String(255), nullable=False)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, default="")
    photos_json = db.Column(db.Text, default="[]")


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.String(255), nullable=False)
    kind = db.Column(db.String(50), default="info")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(120), nullable=False)
    entity_type = db.Column(db.String(120), nullable=False)
    entity_id = db.Column(db.String(120), nullable=False)
    details_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class XeroSyncLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timesheet_week = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(50), default="pending")
    payload_json = db.Column(db.Text, default="{}")
    response_json = db.Column(db.Text, default="{}")
    synced_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class TimesheetApproval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(50), default="submitted")
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    note = db.Column(db.Text, default="")


def ensure_utc_naive(value):
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def parse_client_dt(value):
    if not value:
        return None
    return ensure_utc_naive(datetime.fromisoformat(value))


def utcnow():
    return datetime.utcnow()


def dtfmt(value):
    if not value:
        return "-"
    value = ensure_utc_naive(value)
    return value.strftime("%Y-%m-%d %H:%M UTC")


app.jinja_env.filters["dtfmt"] = dtfmt


@app.context_processor
def inject_helpers():
    settings = CompanySettings.query.first()
    return {"current_user": current_user, "company_settings": settings}


def save_base64_image(data_url: str, prefix: str) -> str | None:
    if not data_url:
        return None
    try:
        _, encoded = data_url.split(",", 1)
        raw = base64.b64decode(encoded)
        filename = f"{prefix}_{uuid.uuid4().hex}.jpg"
        path = UPLOAD_DIR / filename
        with open(path, "wb") as f:
            f.write(raw)
        return f"uploads/{filename}"
    except Exception:
        return None


def distance_m(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]:
        return None
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def in_country_allowlist(lat, lng):
    if lat is None or lng is None:
        return None
    # Broad country envelopes for mobile attendance validation.
    # Australia includes mainland + Tasmania. Philippines covers the national archipelago.
    if -44.5 <= lat <= -10.0 and 112.0 <= lng <= 154.5:
        return "Australia"
    if 4.0 <= lat <= 22.7 and 116.0 <= lng <= 127.5:
        return "Philippines"
    return None


def geofence_state(lat, lng):
    settings = CompanySettings.query.first()
    if not settings or not settings.geofence_enabled:
        return "not-configured"
    if lat is None or lng is None:
        return "unknown"

    allowed_country = in_country_allowlist(lat, lng)
    if allowed_country:
        if allowed_country == "Philippines":
            return "inside: Philippines (country-wide allowlist, including Cebu)"
        if allowed_country == "Australia":
            return "inside: Australia (country-wide allowlist)"

    sites = GeofenceSite.query.filter_by(active=True).all()
    if sites:
        best = None
        for site in sites:
            dist = distance_m(lat, lng, site.lat, site.lng)
            if dist is None:
                continue
            if best is None or dist < best[0]:
                best = (dist, site)
        if best is None:
            return "outside: not in approved countries or configured sites"
        dist, site = best
        if dist <= site.radius_m:
            return f"inside: {site.name} ({site.city}, {site.country})"
        return f"outside: nearest {site.name} ({site.city}, {site.country})"
    dist = distance_m(lat, lng, settings.geofence_lat, settings.geofence_lng)
    if dist is None:
        return "unknown"
    return "inside" if dist <= settings.geofence_radius_m else "outside"


def log_audit(actor_id, action, entity_type, entity_id, details):
    row = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details_json=json.dumps(details, default=str),
    )
    db.session.add(row)
    db.session.commit()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login"))
            if role and user.role != role:
                return redirect(url_for("index"))
            return fn(*args, **kwargs)
        return wrapped
    return deco


def api_login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            if role and user.role != role:
                return jsonify({"error": "Forbidden"}), 403
            return fn(*args, **kwargs)
        return wrapped
    return deco


def active_shift_for_user(user_id):
    return Attendance.query.filter_by(user_id=user_id).filter(Attendance.time_out_at.is_(None)).order_by(Attendance.time_in_at.desc()).first()


def breaks_for_shift(attendance_id):
    return BreakEntry.query.filter_by(attendance_id=attendance_id).order_by(BreakEntry.start_at.asc()).all()


def recalc_shift(att):
    settings = CompanySettings.query.first()
    brs = breaks_for_shift(att.id)
    total_break = sum(b.duration_minutes or 0 for b in brs)
    paid_allowance = settings.paid_break_minutes if settings else 20
    unpaid_allowance = settings.unpaid_break_minutes if settings else 30
    paid_break = min(total_break, paid_allowance)
    unpaid_break = max(0, total_break - paid_allowance)
    if total_break > paid_allowance + unpaid_allowance:
        unpaid_break = total_break - paid_allowance
    att.total_break_minutes = total_break
    att.paid_break_minutes = paid_break
    att.unpaid_break_minutes = min(unpaid_break, total_break)
    if att.time_out_at:
        gross = int((ensure_utc_naive(att.time_out_at) - ensure_utc_naive(att.time_in_at)).total_seconds() / 60)
        att.net_minutes = max(0, gross - att.unpaid_break_minutes)
    db.session.commit()


def attendance_to_dict(att):
    user = User.query.get(att.user_id)
    job = Job.query.get(att.job_id)
    brs = breaks_for_shift(att.id)
    return {
        "id": att.id,
        "uuid": att.attendance_uuid,
        "employee": user.full_name,
        "job": job.name,
        "job_number": job.job_number,
        "date": str(att.date),
        "status": att.status,
        "time_in": dtfmt(att.time_in_at),
        "time_out": dtfmt(att.time_out_at),
        "time_in_photo": f"/static/{att.time_in_photo}" if att.time_in_photo else None,
        "time_out_photo": f"/static/{att.time_out_photo}" if att.time_out_photo else None,
        "time_in_address": att.time_in_address,
        "time_out_address": att.time_out_address,
        "time_in_lat": att.time_in_lat,
        "time_in_lng": att.time_in_lng,
        "time_out_lat": att.time_out_lat,
        "time_out_lng": att.time_out_lng,
        "breaks": [
            {
                "start": dtfmt(b.start_at),
                "end": dtfmt(b.end_at),
                "minutes": b.duration_minutes,
                "start_address": b.start_address,
                "end_address": b.end_address,
            }
            for b in brs
        ],
        "summary": att.work_summary,
        "approval_status": att.approval_status,
        "net_minutes": att.net_minutes,
        "total_break_minutes": att.total_break_minutes,
        "geofence_status": att.geofence_status,
        "offline_time_in": att.offline_time_in,
        "offline_time_out": att.offline_time_out,
    }


def week_bounds(day=None):
    day = day or utcnow().date()
    start = day - timedelta(days=day.weekday())
    end = start + timedelta(days=6)
    return start, end


def get_today_metrics():
    today = utcnow().date()
    shifts = Attendance.query.filter_by(date=today).all()
    working = len([s for s in shifts if s.time_out_at is None and s.status == "working"])
    on_break = len([s for s in shifts if s.time_out_at is None and s.status == "on_break"])
    clocked_out = len([s for s in shifts if s.time_out_at is not None])
    users = User.query.filter_by(role="employee").all()
    not_clocked = max(0, len(users) - len({s.user_id for s in shifts}))
    missing_time_out = len([s for s in shifts if s.time_out_at is None and s.date < today])
    late = len([s for s in shifts if s.time_in_at.hour > 8 or (s.time_in_at.hour == 8 and s.time_in_at.minute > 10)])
    return {
        "working": working,
        "on_break": on_break,
        "clocked_out": clocked_out,
        "not_clocked": not_clocked,
        "late": late,
        "missing_time_out": missing_time_out,
    }


def serialize_worklogs(attendance_id):
    logs = WorkLog.query.filter_by(attendance_id=attendance_id).order_by(WorkLog.start_at.asc()).all()
    data = []
    for log in logs:
        job = Job.query.get(log.job_id)
        data.append({
            "job": job.name if job else "-",
            "task": log.task,
            "start": dtfmt(log.start_at),
            "finish": dtfmt(log.end_at),
            "notes": log.notes,
            "photos": json.loads(log.photos_json or "[]"),
        })
    return data


def seed_demo_data():
    if User.query.first():
        return
    settings = CompanySettings(logo_path="branding/upstage-company-logo.jpg", primary_color="#111111", secondary_color="#444444", timezone="Australia/Sydney")
    db.session.add(settings)
    db.session.flush()
    db.session.add_all([
        GeofenceSite(name="Upstage Sydney Hub", country="Australia", city="Sydney", timezone_name="Australia/Sydney", lat=-33.8688, lng=151.2093, radius_m=800.0),
        GeofenceSite(name="Upstage Cebu Team", country="Philippines", city="Cebu", timezone_name="Asia/Manila", lat=10.3157, lng=123.8854, radius_m=1500.0),
    ])

    admin = User(full_name="Alex Rosemont", email="admin@upstageco.test", role="admin", department="Management")
    admin.set_password("Admin123!")
    db.session.add(admin)

    employees = []
    for name in ["Alex", "Shadelle", "Chris", "Julia", "Bodhi", "Joel", "Will"]:
        u = User(full_name=name, email=f"{name.lower()}@upstageco.test", role="employee")
        u.set_password("Pass123!")
        u.department = "Events" if name not in ["Julia", "Will"] else "Workshop"
        employees.append(u)
        db.session.add(u)

    jobs = [
        Job(job_number="2026-001", name="ATEEZ Tour", client="Live Nation", venue="Rod Laver Arena", location="Melbourne, VIC", start_date=datetime(2026, 8, 15).date(), end_date=datetime(2026, 8, 30).date(), manager_name="Alex Rosemont", notes="Arena load in and stage deck build"),
        Job(job_number="2026-002", name="Foo Fighters Australia", client="Live Nation", venue="Accor Stadium", location="Sydney, NSW", start_date=datetime(2026, 8, 16).date(), end_date=datetime(2026, 8, 28).date(), manager_name="Shadelle Kemp", notes="Concert staging and pack down"),
        Job(job_number="2026-003", name="Workshop", client="Internal", venue="Upstage Workshop", location="Melbourne, VIC", start_date=datetime(2026, 8, 1).date(), end_date=datetime(2026, 12, 31).date(), manager_name="Julia Park", notes="Fabrication and maintenance"),
        Job(job_number="2026-004", name="Accor Stadium", client="Venue Ops", venue="Accor Stadium", location="Sydney, NSW", start_date=datetime(2026, 8, 10).date(), end_date=datetime(2026, 9, 10).date(), manager_name="Joel Grant", notes="Venue setup"),
        Job(job_number="2026-005", name="General Office", client="Internal", venue="Head Office", location="Melbourne, VIC", start_date=datetime(2026, 1, 1).date(), end_date=datetime(2026, 12, 31).date(), manager_name="Will Hart", notes="CAD drawings and admin"),
    ]
    for job in jobs:
        db.session.add(job)
    db.session.commit()

    for employee in employees:
        for job in jobs[:3]:
            db.session.add(JobAssignment(user_id=employee.id, job_id=job.id))
    db.session.commit()

    placeholder = "uploads/demo_photo.svg"
    demo_svg = UPLOAD_DIR / "demo_photo.svg"
    if not demo_svg.exists():
        demo_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480"><rect width="100%" height="100%" fill="#0f172a"/><circle cx="320" cy="170" r="70" fill="#94a3b8"/><rect x="170" y="260" width="300" height="140" rx="40" fill="#cbd5e1"/><text x="320" y="445" text-anchor="middle" font-family="Arial" font-size="28" fill="#f8fafc">Demo Photo</text></svg>', encoding="utf-8")

    base_day = utcnow().date() - timedelta(days=1)
    for idx, employee in enumerate(employees[:4]):
        shift = Attendance(
            user_id=employee.id,
            job_id=jobs[idx % len(jobs)].id,
            status="clocked_out",
            date=base_day,
            time_in_at=datetime.combine(base_day, datetime.min.time()).replace(hour=22) + timedelta(hours=idx),
            time_out_at=datetime.combine(base_day + timedelta(days=1), datetime.min.time()).replace(hour=6) + timedelta(hours=idx),
            time_in_photo=placeholder,
            time_out_photo=placeholder,
            time_in_lat=-37.8136,
            time_in_lng=144.9631,
            time_out_lat=-37.8136,
            time_out_lng=144.9631,
            time_in_address="Melbourne VIC",
            time_out_address="Melbourne VIC",
            work_summary="Completed stage deck assembly and load-out preparation.",
            geofence_status="inside",
            approval_status="submitted",
        )
        db.session.add(shift)
        db.session.commit()
        b = BreakEntry(attendance_id=shift.id, start_at=shift.time_in_at + timedelta(hours=3), end_at=shift.time_in_at + timedelta(hours=3, minutes=50), duration_minutes=50, start_address="Melbourne VIC", end_address="Melbourne VIC")
        db.session.add(b)
        db.session.commit()
        recalc_shift(shift)
        wl = WorkLog(attendance_id=shift.id, user_id=employee.id, job_id=shift.job_id, task="Built stage decks", start_at=shift.time_in_at, end_at=shift.time_in_at + timedelta(hours=2, minutes=30), notes="Completed 6 riser units", photos_json=json.dumps([f"/static/{placeholder}"]))
        db.session.add(wl)
        db.session.commit()

    ts_start, ts_end = week_bounds(base_day)
    for employee in employees[:4]:
        db.session.add(TimesheetApproval(week_start=ts_start, week_end=ts_end, user_id=employee.id, status="submitted"))
    db.session.commit()

    n = Notification(user_id=employees[0].id, title="Timesheet requires correction", body="Please review Tuesday break records.", kind="warning")
    db.session.add(n)
    db.session.commit()
    log_audit(admin.id, "seed_demo_data", "system", "bootstrap", {"company": "Upstage Co"})


@app.route("/")
def index():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    return redirect(url_for("admin_dashboard" if user.role == "admin" else "employee_dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.active and user.check_password(password):
            session["user_id"] = user.id
            return redirect(url_for("admin_dashboard" if user.role == "admin" else "employee_dashboard"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/employee")
@login_required(role="employee")
def employee_dashboard():
    user = current_user()
    jobs = Job.query.join(JobAssignment, JobAssignment.job_id == Job.id).filter(JobAssignment.user_id == user.id).all()
    active = active_shift_for_user(user.id)
    week_start, week_end = week_bounds()
    week_shifts = Attendance.query.filter_by(user_id=user.id).filter(Attendance.date.between(week_start, week_end)).all()
    week_minutes = sum(s.net_minutes for s in week_shifts)
    today = utcnow().date()
    today_shift = Attendance.query.filter_by(user_id=user.id, date=today).order_by(Attendance.time_in_at.desc()).first()
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(5).all()
    return render_template(
        "employee_dashboard.html",
        user=user,
        jobs=jobs,
        active=active,
        today_shift=today_shift,
        week_minutes=week_minutes,
        notifications=notifications,
        worklogs=serialize_worklogs(active.id) if active else (serialize_worklogs(today_shift.id) if today_shift else []),
    )


@app.route("/employee/history")
@login_required(role="employee")
def employee_history_page():
    user = current_user()
    rows = Attendance.query.filter_by(user_id=user.id).order_by(Attendance.time_in_at.desc()).all()
    return render_template("employee_history.html", rows=rows, serialize=attendance_to_dict)


@app.route("/employee/timesheet")
@login_required(role="employee")
def employee_timesheet_page():
    user = current_user()
    ws, we = week_bounds()
    rows = Attendance.query.filter_by(user_id=user.id).filter(Attendance.date.between(ws, we)).all()
    approvals = TimesheetApproval.query.filter_by(user_id=user.id).order_by(TimesheetApproval.submitted_at.desc()).all()
    return render_template("employee_timesheet.html", rows=rows, approvals=approvals)


@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    metrics = get_today_metrics()
    live = Attendance.query.filter(Attendance.time_out_at.is_(None)).order_by(Attendance.time_in_at.asc()).all()
    return render_template("admin_dashboard.html", metrics=metrics, live=live, users=User, jobs=Job)


@app.route("/admin/employees")
@login_required(role="admin")
def admin_employees_page():
    rows = User.query.filter_by(role="employee").order_by(User.full_name.asc()).all()
    return render_template("admin_employees.html", rows=rows)


@app.route("/admin/jobs")
@login_required(role="admin")
def admin_jobs_page():
    rows = Job.query.order_by(Job.start_date.desc()).all()
    return render_template("admin_jobs.html", rows=rows)


@app.route("/admin/attendance")
@login_required(role="admin")
def admin_attendance_page():
    rows = Attendance.query.order_by(Attendance.time_in_at.desc()).limit(100).all()
    return render_template("admin_attendance.html", rows=rows, serialize=attendance_to_dict)


@app.route("/admin/reports")
@login_required(role="admin")
def admin_reports_page():
    rows = Attendance.query.order_by(Attendance.time_in_at.desc()).limit(100).all()
    return render_template("admin_reports.html", rows=rows)


@app.route("/admin/approvals")
@login_required(role="admin")
def admin_approvals_page():
    rows = TimesheetApproval.query.order_by(TimesheetApproval.submitted_at.desc()).all()
    return render_template("admin_approvals.html", rows=rows, users=User)


@app.route("/admin/audit")
@login_required(role="admin")
def admin_audit_page():
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("admin_audit.html", rows=rows, users=User)


@app.route("/admin/xero")
@login_required(role="admin")
def admin_xero_page():
    logs = XeroSyncLog.query.order_by(XeroSyncLog.synced_at.desc()).limit(20).all()
    return render_template("admin_xero.html", logs=logs)


@app.route("/admin/settings")
@login_required(role="admin")
def admin_settings_page():
    settings = CompanySettings.query.first()
    sites = GeofenceSite.query.filter_by(active=True).all()
    return render_template("admin_settings.html", settings=settings, sites=sites)


@app.route("/privacy")
def privacy_page():
    settings = CompanySettings.query.first()
    return render_template("privacy.html", settings=settings)


@app.route('/manifest.json')
def manifest_json():
    settings = CompanySettings.query.first()
    return jsonify({
        "name": settings.company_name if settings else "Upstage Time",
        "short_name": settings.company_name if settings else "Upstage",
        "start_url": "/login",
        "display": "standalone",
        "background_color": "#0b1220",
        "theme_color": settings.primary_color if settings else "#2563eb",
        "icons": [
            {"src": "/static/branding/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/branding/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/branding/apple-touch-icon.png", "sizes": "180x180", "type": "image/png"}
        ]
    })


@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')


@app.route("/api/session")
def api_session():
    user = current_user()
    if not user:
        return jsonify({"authenticated": False})
    return jsonify({"authenticated": True, "role": user.role, "name": user.full_name})


@app.route("/api/jobs/my")
@api_login_required(role="employee")
def api_jobs_my():
    user = current_user()
    jobs = Job.query.join(JobAssignment, JobAssignment.job_id == Job.id).filter(JobAssignment.user_id == user.id).all()
    return jsonify([{"id": j.id, "name": j.name, "job_number": j.job_number, "client": j.client} for j in jobs])


@app.route("/api/employee/dashboard")
@api_login_required(role="employee")
def api_employee_dashboard():
    user = current_user()
    active = active_shift_for_user(user.id)
    week_start, week_end = week_bounds()
    week_shifts = Attendance.query.filter_by(user_id=user.id).filter(Attendance.date.between(week_start, week_end)).all()
    week_minutes = sum(s.net_minutes for s in week_shifts)
    today = utcnow().date()
    today_shift = Attendance.query.filter_by(user_id=user.id, date=today).order_by(Attendance.time_in_at.desc()).first()
    status = "not_working"
    if active:
        status = active.status
    return jsonify({
        "employee": user.full_name,
        "status": status,
        "today_hours": today_shift.net_minutes if today_shift else 0,
        "week_hours": week_minutes,
        "active_shift": attendance_to_dict(active) if active else None,
        "today_shift": attendance_to_dict(today_shift) if today_shift else None,
    })


@app.route("/api/attendance/time-in", methods=["POST"])
@api_login_required(role="employee")
def api_time_in():
    user = current_user()
    if active_shift_for_user(user.id):
        return jsonify({"error": "Duplicate Time In prevented. You already have an open shift."}), 400
    payload = request.get_json() or {}
    now = utcnow()
    job_id = payload.get("job_id")
    job = Job.query.get(job_id)
    if not job:
        return jsonify({"error": "Valid job is required."}), 400
    photo_path = save_base64_image(payload.get("photo_data"), "timein")
    settings = CompanySettings.query.first()
    if settings.required_photo and not photo_path:
        return jsonify({"error": "Live camera photo is required."}), 400
    lat = payload.get("lat")
    lng = payload.get("lng")
    if settings.required_gps and (lat is None or lng is None):
        return jsonify({"error": "GPS location is required."}), 400
    geofence = geofence_state(lat, lng)
    if settings.strict_geofence and geofence.startswith("outside"):
        return jsonify({"error": "Outside approved geofence."}), 400
    device_time = payload.get("client_time")
    shift = Attendance(
        user_id=user.id,
        job_id=job.id,
        status="working",
        date=now.date(),
        time_in_at=now,
        time_in_device_at=parse_client_dt(device_time),
        offline_time_in=bool(payload.get("offline")),
        time_in_photo=photo_path,
        time_in_lat=lat,
        time_in_lng=lng,
        time_in_address=payload.get("address") or f"{lat}, {lng}",
        time_in_device=payload.get("device_info", "unknown device"),
        geofence_status=geofence,
        notes=payload.get("notes", ""),
    )
    db.session.add(shift)
    db.session.commit()
    log_audit(user.id, "time_in", "attendance", shift.id, {"job": job.name, "lat": lat, "lng": lng, "offline": shift.offline_time_in})
    return jsonify({
        "message": "TIME IN RECORDED",
        "time": now.strftime("%I:%M %p"),
        "job": job.name,
        "location": shift.time_in_address,
        "attendance_id": shift.id,
    })


@app.route("/api/attendance/start-break", methods=["POST"])
@api_login_required(role="employee")
def api_start_break():
    user = current_user()
    shift = active_shift_for_user(user.id)
    if not shift:
        return jsonify({"error": "You must time in first."}), 400
    if shift.status == "on_break":
        return jsonify({"error": "Break already in progress."}), 400
    payload = request.get_json() or {}
    photo_path = save_base64_image(payload.get("photo_data"), "break") if CompanySettings.query.first().enable_break_photo else None
    entry = BreakEntry(
        attendance_id=shift.id,
        start_at=utcnow(),
        start_lat=payload.get("lat"),
        start_lng=payload.get("lng"),
        start_address=payload.get("address") or f"{payload.get('lat')}, {payload.get('lng')}",
        photo_path=photo_path,
    )
    db.session.add(entry)
    shift.status = "on_break"
    db.session.commit()
    log_audit(user.id, "start_break", "attendance", shift.id, {"break_id": entry.id})
    return jsonify({"message": "BREAK STARTED", "time": entry.start_at.strftime("%I:%M %p")})


@app.route("/api/attendance/end-break", methods=["POST"])
@api_login_required(role="employee")
def api_end_break():
    user = current_user()
    shift = active_shift_for_user(user.id)
    if not shift or shift.status != "on_break":
        return jsonify({"error": "No active break found."}), 400
    payload = request.get_json() or {}
    br = BreakEntry.query.filter_by(attendance_id=shift.id, end_at=None).order_by(BreakEntry.start_at.desc()).first()
    if not br:
        return jsonify({"error": "No active break found."}), 400
    br.end_at = utcnow()
    br.end_lat = payload.get("lat")
    br.end_lng = payload.get("lng")
    br.end_address = payload.get("address") or f"{payload.get('lat')}, {payload.get('lng')}"
    br.duration_minutes = max(0, int((ensure_utc_naive(br.end_at) - ensure_utc_naive(br.start_at)).total_seconds() / 60))
    shift.status = "working"
    db.session.commit()
    recalc_shift(shift)
    log_audit(user.id, "end_break", "attendance", shift.id, {"break_id": br.id, "duration_minutes": br.duration_minutes})
    return jsonify({"message": "BREAK ENDED", "duration_minutes": br.duration_minutes})


@app.route("/api/attendance/time-out", methods=["POST"])
@api_login_required(role="employee")
def api_time_out():
    user = current_user()
    shift = active_shift_for_user(user.id)
    if not shift:
        return jsonify({"error": "No active shift to time out."}), 400
    if shift.status == "on_break":
        return jsonify({"error": "End break before timing out."}), 400
    payload = request.get_json() or {}
    photo_path = save_base64_image(payload.get("photo_data"), "timeout")
    settings = CompanySettings.query.first()
    if settings.required_photo and not photo_path:
        return jsonify({"error": "Time out photo required."}), 400
    shift.time_out_at = utcnow()
    shift.time_out_device_at = parse_client_dt(payload.get("client_time"))
    shift.offline_time_out = bool(payload.get("offline"))
    shift.time_out_photo = photo_path
    shift.time_out_lat = payload.get("lat")
    shift.time_out_lng = payload.get("lng")
    shift.time_out_address = payload.get("address") or f"{payload.get('lat')}, {payload.get('lng')}"
    shift.time_out_device = payload.get("device_info", "unknown device")
    shift.work_summary = payload.get("summary", "")
    shift.notes = (shift.notes or "") + (f"\n{payload.get('notes')}" if payload.get("notes") else "")
    shift.final_job_photo = save_base64_image(payload.get("final_photo_data"), "jobfinal")
    shift.status = "clocked_out"
    recalc_shift(shift)
    db.session.commit()
    log_audit(user.id, "time_out", "attendance", shift.id, {"net_minutes": shift.net_minutes, "offline": shift.offline_time_out})
    return jsonify({
        "message": "TIME OUT RECORDED",
        "worked_today": shift.net_minutes,
        "break_minutes": shift.total_break_minutes,
        "job": Job.query.get(shift.job_id).name,
    })


@app.route("/api/worklogs", methods=["POST"])
@api_login_required(role="employee")
def api_add_worklog():
    user = current_user()
    payload = request.get_json() or {}
    shift = active_shift_for_user(user.id) or Attendance.query.get(payload.get("attendance_id"))
    if not shift or shift.user_id != user.id:
        return jsonify({"error": "Valid shift required."}), 400
    log = WorkLog(
        attendance_id=shift.id,
        user_id=user.id,
        job_id=shift.job_id,
        task=payload.get("task", "Untitled task"),
        start_at=datetime.fromisoformat(payload.get("start_at")),
        end_at=datetime.fromisoformat(payload.get("end_at")),
        notes=payload.get("notes", ""),
        photos_json=json.dumps([]),
    )
    db.session.add(log)
    db.session.commit()
    log_audit(user.id, "add_worklog", "attendance", shift.id, {"task": log.task})
    return jsonify({"message": "Work log saved."})


@app.route("/api/employee/history")
@api_login_required(role="employee")
def api_employee_history():
    user = current_user()
    rows = Attendance.query.filter_by(user_id=user.id).order_by(Attendance.time_in_at.desc()).all()
    return jsonify([attendance_to_dict(r) for r in rows])


@app.route("/api/timesheet/submit", methods=["POST"])
@api_login_required(role="employee")
def api_submit_timesheet():
    user = current_user()
    ws, we = week_bounds()
    record = TimesheetApproval.query.filter_by(user_id=user.id, week_start=ws, week_end=we).first()
    if not record:
        record = TimesheetApproval(user_id=user.id, week_start=ws, week_end=we, status="submitted")
        db.session.add(record)
    else:
        record.status = "submitted"
        record.submitted_at = utcnow()
    db.session.commit()
    log_audit(user.id, "submit_timesheet", "timesheet", record.id, {"week_start": str(ws), "week_end": str(we)})
    return jsonify({"message": "Timesheet submitted for approval."})


@app.route("/api/admin/dashboard")
@api_login_required(role="admin")
def api_admin_dashboard():
    metrics = get_today_metrics()
    live_rows = [attendance_to_dict(r) for r in Attendance.query.filter(Attendance.time_out_at.is_(None)).all()]
    return jsonify({"today": metrics, "live": live_rows})


@app.route("/api/admin/employees", methods=["POST"])
@api_login_required(role="admin")
def api_admin_create_employee():
    user = current_user()
    payload = request.get_json() or {}
    employee = User(full_name=payload["full_name"], email=payload["email"].lower(), role="employee", department=payload.get("department", "Operations"), pay_category=payload.get("pay_category", "Ordinary Hours"))
    employee.set_password(payload.get("password", "Pass123!"))
    db.session.add(employee)
    db.session.commit()
    log_audit(user.id, "create_employee", "user", employee.id, {"employee": employee.full_name})
    return jsonify({"message": "Employee created.", "id": employee.id})


@app.route("/api/admin/attendance/<int:attendance_id>/approve", methods=["POST"])
@api_login_required(role="admin")
def api_approve_attendance(attendance_id):
    admin = current_user()
    att = Attendance.query.get_or_404(attendance_id)
    att.approval_status = "approved"
    att.approver_id = admin.id
    att.approved_at = utcnow()
    att.approval_note = (request.get_json() or {}).get("note", "Approved")
    db.session.commit()
    log_audit(admin.id, "approve_attendance", "attendance", att.id, {"status": "approved"})
    return jsonify({"message": "Attendance approved."})


@app.route("/api/admin/attendance/<int:attendance_id>/reject", methods=["POST"])
@api_login_required(role="admin")
def api_reject_attendance(attendance_id):
    admin = current_user()
    att = Attendance.query.get_or_404(attendance_id)
    att.approval_status = "rejected"
    att.approver_id = admin.id
    att.approved_at = utcnow()
    att.approval_note = (request.get_json() or {}).get("note", "Rejected")
    db.session.commit()
    log_audit(admin.id, "reject_attendance", "attendance", att.id, {"status": "rejected"})
    return jsonify({"message": "Attendance rejected."})


@app.route("/api/admin/attendance/<int:attendance_id>/correct", methods=["POST"])
@api_login_required(role="admin")
def api_correct_attendance(attendance_id):
    admin = current_user()
    att = Attendance.query.get_or_404(attendance_id)
    original = {"time_out_at": dtfmt(att.time_out_at), "summary": att.work_summary}
    payload = request.get_json() or {}
    if payload.get("time_out_at"):
        att.time_out_at = datetime.fromisoformat(payload.get("time_out_at"))
    if payload.get("summary"):
        att.work_summary = payload.get("summary")
    if att.approval_status == "approved":
        att.edited_after_approval = True
    db.session.commit()
    recalc_shift(att)
    log_audit(admin.id, "correct_attendance", "attendance", att.id, {
        "original": original,
        "new": {"time_out_at": dtfmt(att.time_out_at), "summary": att.work_summary},
        "reason": payload.get("reason", "Admin correction"),
    })
    return jsonify({"message": "Attendance corrected."})


@app.route("/api/admin/timesheets/<int:approval_id>/review", methods=["POST"])
@api_login_required(role="admin")
def api_review_timesheet(approval_id):
    admin = current_user()
    payload = request.get_json() or {}
    row = TimesheetApproval.query.get_or_404(approval_id)
    row.status = payload.get("status", row.status)
    row.note = payload.get("note", "")
    row.reviewer_id = admin.id
    row.reviewed_at = utcnow()
    db.session.commit()
    log_audit(admin.id, f"timesheet_{row.status}", "timesheet", row.id, {"note": row.note})
    return jsonify({"message": f"Timesheet {row.status}."})


@app.route("/api/admin/reports.csv")
@api_login_required(role="admin")
def api_export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Employee", "Job", "Time In", "Time Out", "Break Minutes", "Net Minutes", "Approval", "Geofence"])
    rows = Attendance.query.order_by(Attendance.time_in_at.desc()).all()
    for r in rows:
        user = User.query.get(r.user_id)
        job = Job.query.get(r.job_id)
        writer.writerow([r.date, user.full_name, job.name, dtfmt(r.time_in_at), dtfmt(r.time_out_at), r.total_break_minutes, r.net_minutes, r.approval_status, r.geofence_status])
    data = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(data, mimetype="text/csv", as_attachment=True, download_name="upstage_attendance.csv")


@app.route("/api/admin/reports.pdf")
@api_login_required(role="admin")
def api_export_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = [Paragraph("Upstage Co Attendance Report", styles["Title"]), Spacer(1, 12)]
    data = [["Date", "Employee", "Job", "Time In", "Time Out", "Net Hrs", "Approval"]]
    rows = Attendance.query.order_by(Attendance.time_in_at.desc()).limit(30).all()
    for r in rows:
        user = User.query.get(r.user_id)
        job = Job.query.get(r.job_id)
        data.append([str(r.date), user.full_name, job.name, dtfmt(r.time_in_at), dtfmt(r.time_out_at), f"{round(r.net_minutes/60, 2)}", r.approval_status])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="upstage_attendance.pdf")


@app.route("/api/admin/xero/sync", methods=["POST"])
@api_login_required(role="admin")
def api_xero_sync():
    ws, we = week_bounds()
    approved = Attendance.query.filter_by(approval_status="approved").filter(Attendance.date.between(ws, we)).all()
    payload = {
        "oauth": "PKCE/OAuth2 ready; client_id, client_secret (server flow), redirect_uri, scopes required.",
        "timesheets": [attendance_to_dict(a) for a in approved],
        "mapping_required": True,
    }
    response = {
        "note": "Demo sync only. Connect real Xero credentials to send to Payroll AU API.",
        "supported": ["employee mapping", "timesheet creation", "approval transition"],
        "limitations": ["Requires Xero payroll-enabled AU tenant", "Historical timesheet creation is restricted by Xero API rules"],
    }
    log = XeroSyncLog(timesheet_week=f"{ws} to {we}", status="ready_for_credentials", payload_json=json.dumps(payload), response_json=json.dumps(response))
    db.session.add(log)
    db.session.commit()
    log_audit(current_user().id, "xero_sync_attempt", "xero", log.id, response)
    return jsonify({"message": "Xero sync package prepared.", "status": log.status})


@app.route('/api/admin/logo-upload', methods=['POST'])
@api_login_required(role='admin')
def api_logo_upload():
    admin = current_user()
    settings = CompanySettings.query.first()
    file = request.files.get('logo')
    if not file or not file.filename:
        return jsonify({"error": "Logo file is required."}), 400
    ext = os.path.splitext(file.filename)[1].lower() or '.png'
    filename = f"logo_{uuid.uuid4().hex}{ext}"
    target = BASE_DIR / 'static' / 'branding' / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    file.save(target)
    settings.logo_path = f"branding/{filename}"
    db.session.commit()
    log_audit(admin.id, 'upload_logo', 'settings', settings.id, {"logo_path": settings.logo_path})
    return jsonify({"message": "Logo uploaded.", "logo_url": f"/static/{settings.logo_path}"})


@app.route("/api/admin/settings", methods=["POST"])
@api_login_required(role="admin")
def api_update_settings():
    admin = current_user()
    settings = CompanySettings.query.first()
    payload = request.get_json() or {}
    for field in [
        "company_name", "logo_path", "primary_color", "secondary_color", "timezone", "work_week", "required_photo", "required_gps", "geofence_enabled",
        "strict_geofence", "geofence_name", "geofence_lat", "geofence_lng", "geofence_radius_m",
        "late_threshold_minutes", "overtime_threshold_hours", "paid_break_minutes", "unpaid_break_minutes",
        "allow_gallery_upload", "retention_days", "enable_break_photo"
    ]:
        if field in payload:
            setattr(settings, field, payload[field])
    db.session.commit()
    log_audit(admin.id, "update_settings", "settings", settings.id, payload)
    return jsonify({"message": "Settings updated."})


@app.route("/api/admin/manual-entry", methods=["POST"])
@api_login_required(role="admin")
def api_manual_entry():
    admin = current_user()
    payload = request.get_json() or {}
    att = Attendance(
        user_id=payload["user_id"],
        job_id=payload["job_id"],
        status="clocked_out",
        date=parse_client_dt(payload["time_in_at"]).date(),
        time_in_at=parse_client_dt(payload["time_in_at"]),
        time_out_at=parse_client_dt(payload["time_out_at"]),
        time_in_address=payload.get("address", "Manual Entry"),
        time_out_address=payload.get("address", "Manual Entry"),
        approval_status="draft",
        notes=payload.get("reason", "Manual entry by admin"),
        geofence_status="manual",
    )
    db.session.add(att)
    db.session.commit()
    recalc_shift(att)
    log_audit(admin.id, "manual_attendance_entry", "attendance", att.id, payload)
    return jsonify({"message": "Manual attendance added."})


@app.route("/docs/api")
def api_docs_page():
    return render_template("api_docs.html")


with app.app_context():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / 'static' / 'branding').mkdir(parents=True, exist_ok=True)
    db.create_all()
    seed_demo_data()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
