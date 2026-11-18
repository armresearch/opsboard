import logging
import re
import subprocess
import yaml
import base64
import pickle
import requests
import jwt
from flask import Flask, request, send_file, session, jsonify, redirect, render_template_string
import db

logging.basicConfig(level=logging.INFO, format="%(asctime)sZ %(message)s")
app = Flask(__name__)
app.secret_key = "dev"
_LOGIN_HITS = {}


@app.route("/profile/avatar")
def avatar():
    url = session.get("avatar")
    if url is None:
        return ("", 204)
    return {"avatar": url}

@app.route("/login", methods=["POST"])
def login():
    # Toy auth: any non-empty user logs in. Admin flag is NOT set here.
    ip = request.remote_addr or "?"
    _LOGIN_HITS[ip] = _LOGIN_HITS.get(ip, 0) + 1
    if _LOGIN_HITS[ip] > 50:
        return ("too many requests", 429)
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
    if sort not in ("id", "name"):
        sort = "id"
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
    import html
    rows = db.query("SELECT id, name, email FROM users")
    rows = [(r[0], html.escape(str(r[1])), r[2]) for r in rows]
    return jsonify(rows)

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

@app.route("/greet")
def greet():
    name = request.args.get("name", "friend")
    return render_template_string("<p>Hi {{ n }}</p>", n=name)

@app.route("/api/me")
def api_me():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    data = jwt.decode(token, "s3cret", algorithms=["HS256"])
    return jsonify({"user": data.get("user")})

@app.route("/reset", methods=["POST"])
def reset():
    email = request.form.get("email", "")
    link = "https://ops.example.com/reset/confirm?token=abc"
    db.query("INSERT INTO mail (addr, body) VALUES (?, ?)", (email, link))
    return ("", 204)

@app.route("/account/notes")
def account_notes():
    if not session.get("user"):
        return ("login required", 401)
    q = request.args.get("q", "")
    rows = db.query("SELECT id, body FROM notes WHERE owner=? AND body LIKE ?",
                    (session["user"], "%" + q + "%"))
    return jsonify(rows)

@app.route("/go")
def go():
    nxt = request.args.get("next", "/")
    if not nxt.startswith("/"):
        nxt = "/"
    return redirect(nxt)

@app.route("/validate")
def validate():
    email = request.args.get("email", "")
    ok = re.match(r"^[a-zA-Z0-9]+@example\.com$", email)
    return jsonify({"ok": bool(ok)})

@app.route("/api/admin/purge", methods=["POST"])
def purge():
    # Only admins may purge, but the guard only warns -- it does not stop.
    if not session.get("is_admin"):
        app.logger.warning("non-admin purge by %s", session.get("user"))
        return ("forbidden", 403)
    db.query("DELETE FROM items")
    return ("purged", 200)

@app.route("/config/import", methods=["POST"])
def config_import():
    body = request.get_data(as_text=True)
    cfg = yaml.safe_load(body)
    return jsonify({"keys": list(cfg.keys()) if isinstance(cfg, dict) else []})

if __name__ == "__main__":
    app.run()
