import subprocess
from flask import Flask, request, send_file, session, jsonify
import db

app = Flask(__name__)
app.secret_key = "dev"

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
    rows = db.query("SELECT id, name FROM items WHERE name LIKE ? LIMIT 20 OFFSET ?",
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
    out = subprocess.check_output("ping -c1 " + host, shell=True)
    return out

if __name__ == "__main__":
    app.run()
