from datetime import date, datetime, timedelta

from flask import (
    Flask, abort, jsonify, redirect, render_template, request, url_for
)

from flask_cors import CORS

from database import get_connection, init_db

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",
    "http://localhost:5173",
]}})

init_db()

VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"open", "in_progress", "resolved", "closed"}

PRIORITY_CHOICES = ["High", "Medium", "Low"]
DUE_DAYS_BY_PRIORITY = {"high": 3, "medium": 7, "low": 14}


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Grievance Tracking backend is running"
    }), 200


@app.route("/api/grievances", methods=["POST"])
def create_grievance():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be valid JSON"}), 400

    errors = []

    title = str(data.get("title") or "").strip()
    description = str(data.get("description") or "").strip()
    complainant_name = str(data.get("complainant_name") or "").strip()
    for field, value in [("title", title),
                         ("description", description),
                         ("complainant_name", complainant_name)]:
        if not value:
            errors.append(f"{field} is required")

    department = str(data.get("department") or "").strip() or None

    priority = data.get("priority", "medium")
    if priority not in VALID_PRIORITIES:
        errors.append("priority must be one of: low, medium, high")

    status = data.get("status", "open")
    if status not in VALID_STATUSES:
        errors.append("status must be one of: open, in_progress, resolved, closed")

    due_date = data.get("due_date")
    if due_date:
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            errors.append("due_date must be in YYYY-MM-DD format")
    else:
        due_date = None

    if errors:
        return jsonify({"errors": errors}), 400

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO grievances
                (title, description, complainant_name, department,
                 priority, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, complainant_name, department,
             priority, status, due_date),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM grievances WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    finally:
        conn.close()

    return jsonify(dict(row)), 201


@app.route("/api/grievances", methods=["GET"])
def list_grievances():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM grievances ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()

    return jsonify([dict(row) for row in rows]), 200

UPDATABLE_FIELDS = {
    "title", "description", "complainant_name",
    "department", "priority", "status", "due_date",
}


def fetch_grievance(grievance_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM grievances WHERE id = ?", (grievance_id,)
        ).fetchone()
    finally:
        conn.close()


@app.route("/api/grievances/<int:grievance_id>", methods=["GET"])
def get_grievance(grievance_id):
    row = fetch_grievance(grievance_id)
    if row is None:
        return jsonify({"error": "Grievance not found"}), 404
    return jsonify(dict(row)), 200


@app.route("/api/grievances/<int:grievance_id>", methods=["PATCH"])
def update_grievance(grievance_id):
    if fetch_grievance(grievance_id) is None:
        return jsonify({"error": "Grievance not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Send at least one field to update"}), 400

    errors = []
    updates = {}

    unknown = set(data) - UPDATABLE_FIELDS
    if unknown:
        errors.append(
            "Unknown or non-editable fields: " + ", ".join(sorted(unknown))
        )

    for field in UPDATABLE_FIELDS:
        if field not in data:
            continue
        value = data[field]

        if field in ("title", "description", "complainant_name"):
            value = str(value or "").strip()
            if not value:
                errors.append(f"{field} cannot be empty")
        elif field == "department":
            value = str(value or "").strip() or None
        elif field == "priority":
            if not isinstance(value, str) or value not in VALID_PRIORITIES:
                errors.append("priority must be one of: low, medium, high")
        elif field == "status":
            if not isinstance(value, str) or value not in VALID_STATUSES:
                errors.append(
                    "status must be one of: open, in_progress, resolved, closed"
                )
        elif field == "due_date":
            if value:
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except (ValueError, TypeError):
                    errors.append("due_date must be in YYYY-MM-DD format")
            else:
                value = None

        updates[field] = value

        if errors:
            return jsonify({"errors": errors}), 400

    set_clause = ", ".join(f"{field} = ?" for field in updates)
    values = list(updates.values()) + [grievance_id]

    if "status" in updates:
        label = STATUS_LABELS.get(updates["status"], updates["status"])
        action = f"Status changed to {label}"
        others = sorted(set(updates) - {"status"})
        if others:
            action += "; updated " + ", ".join(others)
    else:
        action = "Updated " + ", ".join(sorted(updates))

    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE grievances SET {set_clause}, "
            "updated_at = datetime('now') WHERE id = ?",
            values,
        )
        conn.execute(
            "INSERT INTO grievance_history (grievance_id, action) VALUES (?, ?)",
            (grievance_id, action),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify(dict(fetch_grievance(grievance_id))), 200

DUE_SOON_DAYS = 2


@app.route("/api/reminders/due", methods=["GET"])
def due_reminders():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT *,
                   due_date < date('now', 'localtime') AS overdue
            FROM grievances
            WHERE status IN ('open', 'in_progress')
              AND due_date IS NOT NULL
              AND due_date <= date('now', 'localtime', ?)
              AND (last_reminded_at IS NULL
                   OR date(last_reminded_at, 'localtime') < date('now', 'localtime'))
            ORDER BY due_date ASC
            """,
            (f"+{DUE_SOON_DAYS} days",),
        ).fetchall()
    finally:
        conn.close()

    reminders = []
    for row in rows:
        item = dict(row)
        item["overdue"] = bool(item["overdue"])
        reminders.append(item)

    return jsonify(reminders), 200


@app.route("/api/reminders/<int:grievance_id>/sent", methods=["POST"])
def mark_reminder_sent(grievance_id):
    if fetch_grievance(grievance_id) is None:
        return jsonify({"error": "Grievance not found"}), 404

    conn = get_connection()
    try:
        conn.execute(
            "UPDATE grievances SET last_reminded_at = datetime('now') WHERE id = ?",
            (grievance_id,),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify(dict(fetch_grievance(grievance_id))), 200

STATUS_LABELS = {
    "open": "Pending",
    "in_progress": "In Progress",
    "resolved": "Resolved",
    "closed": "Resolved",
}

LABEL_TO_STATUS = {
    "Pending": "open",
    "In Progress": "in_progress",
    "Resolved": "resolved",
}


ESCALATION_RULES = [(7, 3), (3, 2), (1, 1)]


def escalation_level(status, due_date):
    if status not in ("open", "in_progress") or not due_date:
        return 0
    try:
        due = date.fromisoformat(due_date)
    except ValueError:
        return 0
    days_overdue = (date.today() - due).days
    for min_days, level in ESCALATION_RULES:
        if days_overdue >= min_days:
            return level
    return 0


def to_page_item(row):
    g = dict(row)
    is_open = g["status"] in ("open", "in_progress")
    g["escalation_level"] = escalation_level(g["status"], g["due_date"])
    g["is_overdue"] = bool(
        is_open and g["due_date"] and g["due_date"] < date.today().isoformat()
    )
    g["ticket_id"] = f"GRV-{g['id']:04d}"
    g["priority"] = g["priority"].capitalize()
    g["status"] = STATUS_LABELS.get(g["status"], g["status"])
    g["due_date"] = g["due_date"] or "-"
    return g

@app.route("/")
def dashboard():
    today = date.today().isoformat()

    conn = get_connection()
    try:
        counts = {
            row["status"]: row["n"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS n FROM grievances GROUP BY status"
            )
        }
        overdue = conn.execute(
            """
            SELECT COUNT(*) AS n FROM grievances
            WHERE status IN ('open', 'in_progress')
              AND due_date IS NOT NULL
              AND due_date < ?
            """,
            (today,),
        ).fetchone()["n"]
        open_rows = conn.execute(
            "SELECT status, due_date FROM grievances "
            "WHERE status IN ('open', 'in_progress') AND due_date IS NOT NULL"
        ).fetchall()
        escalated = sum(
            1 for r in open_rows
            if escalation_level(r["status"], r["due_date"]) > 0
        )
    finally:
        conn.close()

    stats = {
        "total": sum(counts.values()),
        "pending": counts.get("open", 0),
        "in_progress": counts.get("in_progress", 0),
        "resolved": counts.get("resolved", 0) + counts.get("closed", 0),
        "overdue": overdue,
        "escalated": escalated,
    }
    return render_template("dashboard.html", stats=stats)

@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "GET":
        return render_template("submit.html", priorities=PRIORITY_CHOICES)

    complainant_name = request.form.get("complainant_name", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    priority = request.form.get("priority", "medium").strip().lower()

    errors = []
    for field, value in [("complainant_name", complainant_name),
                         ("title", title),
                         ("description", description)]:
        if not value:
            errors.append(f"{field} is required")

    if priority not in VALID_PRIORITIES:
        priority = "medium"

    if errors:
        return jsonify({"errors": errors}), 400

    due_date = (
        date.today() + timedelta(days=DUE_DAYS_BY_PRIORITY[priority])
    ).isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO grievances
                (title, description, complainant_name, priority, due_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, description, complainant_name, priority, due_date),
        )
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("grievances"))

@app.route("/grievances")
def grievances():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM grievances ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()

    items = [to_page_item(row) for row in rows]
    return render_template("grievances.html", grievances=items)


@app.route("/grievances/<int:gid>")
def detail(gid):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM grievances WHERE id = ?", (gid,)
        ).fetchone()
        if row is None:
            abort(404)
        history_rows = conn.execute(
            "SELECT action, timestamp FROM grievance_history "
            "WHERE grievance_id = ? ORDER BY id",
            (gid,),
        ).fetchall()
        followup_rows = conn.execute(
            "SELECT id, note, remind_at, done FROM followups "
            "WHERE grievance_id = ? ORDER BY remind_at",
            (gid,),
        ).fetchall()
    finally:
        conn.close()

    item = to_page_item(row)
    item["updated_at"] = row["updated_at"] or row["created_at"]

    history = [{"timestamp": row["created_at"],
                "action": "Grievance submitted"}]
    history += [dict(h) for h in history_rows]
    followups = [dict(f) for f in followup_rows]

    return render_template(
        "detail.html", grievance=item, history=history, followups=followups
    )


@app.route("/status", methods=["POST"])
def update_status():
    gid = request.form.get("grievance_id", type=int)
    label = request.form.get("status", "")
    new_status = LABEL_TO_STATUS.get(label)
    if gid is None or new_status is None:
        abort(400)

    conn = get_connection()
    try:
        found = conn.execute(
            "SELECT id FROM grievances WHERE id = ?", (gid,)
        ).fetchone()
        if found is None:
            abort(404)
        conn.execute(
            "UPDATE grievances SET status = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (new_status, gid),
        )
        conn.execute(
            "INSERT INTO grievance_history (grievance_id, action) VALUES (?, ?)",
            (gid, f"Status changed to {label}"),
        )
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("detail", gid=gid))


@app.route("/followup", methods=["POST"])
def add_followup():
    gid = request.form.get("grievance_id", type=int)
    note = request.form.get("note", "").strip()
    remind_at = request.form.get("remind_at", "").strip()
    if gid is None:
        abort(400)

    try:
        datetime.strptime(remind_at, "%Y-%m-%d")
    except ValueError:
        return redirect(url_for("detail", gid=gid))
    if not note:
        return redirect(url_for("detail", gid=gid))

    conn = get_connection()
    try:
        found = conn.execute(
            "SELECT id FROM grievances WHERE id = ?", (gid,)
        ).fetchone()
        if found is None:
            abort(404)
        conn.execute(
            "INSERT INTO followups (grievance_id, note, remind_at) "
            "VALUES (?, ?, ?)",
            (gid, note, remind_at),
        )
        conn.execute(
            "INSERT INTO grievance_history (grievance_id, action) VALUES (?, ?)",
            (gid, "Follow-up added"),
        )
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("detail", gid=gid))


@app.route("/reminders")
def reminders():
    today = date.today().isoformat()

    conn = get_connection()
    try:
        followup_rows = conn.execute(
            """
            SELECT id, grievance_id, note, remind_at
            FROM followups
            WHERE done = 0 AND remind_at <= ?
            ORDER BY remind_at
            """,
            (today,),
        ).fetchall()
        overdue_rows = conn.execute(
            """
            SELECT * FROM grievances
            WHERE status IN ('open', 'in_progress')
              AND due_date IS NOT NULL
              AND due_date < ?
            ORDER BY due_date
            """,
            (today,),
        ).fetchall()
    finally:
        conn.close()

    today_followups = []
    for row in followup_rows:
        item = dict(row)
        item["ticket_id"] = f"GRV-{item['grievance_id']:04d}"
        today_followups.append(item)

    overdue_grievances = [to_page_item(row) for row in overdue_rows]

    return render_template(
        "reminders.html",
        today_followups=today_followups,
        overdue_grievances=overdue_grievances,
    )

@app.route("/api/stats", methods=["GET"])
def api_stats():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT priority, COUNT(*) AS n FROM grievances GROUP BY priority"
        ).fetchall()
    finally:
        conn.close()

    counts = {row["priority"]: row["n"] for row in rows}
    by_priority = {
        name: counts[key]
        for name, key in [("High", "high"), ("Medium", "medium"), ("Low", "low")]
        if counts.get(key)
    }
    return jsonify({"by_priority": by_priority}), 200

@app.route("/followup/done", methods=["POST"])
def mark_followup_done():
    followup_id = request.form.get("followup_id", type=int)
    next_page = request.form.get("next", "detail")
    if followup_id is None:
        abort(400)

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT grievance_id FROM followups WHERE id = ?", (followup_id,)
        ).fetchone()
        if row is None:
            abort(404)
        conn.execute(
            "UPDATE followups SET done = 1 WHERE id = ?", (followup_id,)
        )
        conn.execute(
            "INSERT INTO grievance_history (grievance_id, action) VALUES (?, ?)",
            (row["grievance_id"], "Follow-up marked done"),
        )
        conn.commit()
    finally:
        conn.close()

    if next_page == "reminders":
        return redirect(url_for("reminders"))
    return redirect(url_for("detail", gid=row["grievance_id"]))

@app.before_request
def sync_escalations():
    if request.endpoint in (None, "static"):
        return

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, status, due_date, escalation_level FROM grievances"
        ).fetchall()
        for row in rows:
            new_level = escalation_level(row["status"], row["due_date"])
            if new_level > row["escalation_level"]:
                conn.execute(
                    "UPDATE grievances SET escalation_level = ?, "
                    "updated_at = datetime('now') WHERE id = ?",
                    (new_level, row["id"]),
                )
                conn.execute(
                    "INSERT INTO grievance_history (grievance_id, action) "
                    "VALUES (?, ?)",
                    (row["id"], f"Escalated to Level {new_level}"),
                )
            elif new_level < row["escalation_level"]:
                conn.execute(
                    "UPDATE grievances SET escalation_level = ? WHERE id = ?",
                    (new_level, row["id"]),
                )
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)