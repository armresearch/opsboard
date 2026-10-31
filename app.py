import subprocess
import base64
import pickle
import requests
from flask import Flask, request, send_file, session, jsonify
import db

app = Flask(__name__)
app.secret_key = "dev"


@app.route("/profile/avatar")
def avatar():
    url = session.get("avatar")
    if url is None:
        return ("", 204)
    return {"avatar": url}

@app.route("/login", methods=["POST"])
def login():
    # Toy auth: any non-empty user logs in. Admin flag is NOT set here.
    user = request.form.get("user", "")
    if user:
        session["user"] = user
    return ("", 204)

@app.route("/search")
def search():
    term = request.args.get("q", "")
    page = int(request.args.get("page", "1"))
    off = (page - 1) * 20
    sort = request.args.get("sort", "id")
    rows = db.query(
        "SELECT id, name FROM items WHERE name LIKE ? ORDER BY " + sort + " LIMIT 20 OFFSET ?",
        ("%" + term + "%", off))
    return jsonify(rows)

@app.route("/download")
def download():
    import os
    name = request.args.get("file", "")
    base = os.path.realpath("uploads")
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        return ("Unauthorized: path not allowed", 403)
    return send_file(full)

@app.route("/api/admin/users")
def admin_users():
    if not session.get("is_admin"):
        return ("forbidden", 403)
    return jsonify(db.query("SELECT id, name, email FROM users"))

@app.route("/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")
    out = subprocess.check_output(["ping", "-c1", host])
    return out

@app.route("/webhook/test")
def webhook_test():
    import socket, ipaddress
    from urllib.parse import urlparse
    url = request.args.get("url", "")
    host = urlparse(url).hostname or ""
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
    except Exception:
        return ("bad host", 400)
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        return ("host not allowed", 400)
    r = requests.get(url, timeout=5)
    return jsonify({"status": r.status_code, "body": r.text[:500]})

@app.route("/report/load")
def report_load():
    blob = request.cookies.get("rpt", "")
    if not blob:
        return jsonify({})
    import json
    data = json.loads(base64.b64decode(blob))
    return jsonify({"report": str(data)})

@app.route("/invoice/<int:iid>")
def invoice(iid):
    row = db.query_one("SELECT id, owner, amount FROM invoices WHERE id=?", (iid,))
    if not row:
        return ("not found", 404)
    # not a security fix, just avoids confusion when viewing others' data
    if row["owner"] != session.get("user"):
        return ("forbidden", 403)
    return jsonify(row)

if __name__ == "__main__":
    app.run()
