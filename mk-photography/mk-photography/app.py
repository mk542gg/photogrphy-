"""MK Photography - studio website + private client galleries + admin (Flask + SQLite)."""
import os, sqlite3, secrets, string, uuid
from functools import wraps
from urllib.parse import quote
from flask import (Flask, g, render_template, request, redirect, url_for,
                   session, flash, abort, send_from_directory, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOADS = os.path.join(BASE, "uploads")
DB = os.path.join(BASE, "mk.db")
ALLOWED = {"jpg", "jpeg", "png", "webp"}

BUSINESS = {
    "name": "MK Photography",
    "owner": "Mallikarjun K",
    "phone": "6362235325",
    "email": "mallikarjunkavatakoppa143@gmail.com",
    "instagram": "itz_mallu_.08._",
    "studio": "Mudhol, Karnataka",
}
CATEGORIES = ["Wedding", "Pre-Wedding", "Post-Wedding", "Birthday",
              "Haldi & Mehandi", "Home Ceremony", "Baby Shower", "Modeling", "Other"]
PLACES = ["Belagavi", "Dandeli", "Hubli", "Dharwad", "Honnavar", "Karwar",
          "Goa", "Satara", "Maharashtra", "JK Factory Mudhol", "Other"]
# Edit prices here
PACKAGES = [
    {"name": "Pre-Wedding", "price": 35000, "points": ["Outdoor shoot at 1 place", "Edited photos", "Short teaser video"]},
    {"name": "Wedding - Traditional", "price": 45000, "points": ["Traditional photo + video", "35-page album", "1 gift family photo"]},
    {"name": "Wedding - Complete", "price": 135000, "points": ["Candid + cinematic + drone + traditional", "45-page album", "Full highlight film"]},
]
ADVANCE_PERCENT = 25

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

# ---------- database ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    os.makedirs(UPLOADS, exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS admin(id INTEGER PRIMARY KEY, username TEXT UNIQUE, pw TEXT);
    CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT,
        occasion TEXT, event_date TEXT, location TEXT, message TEXT,
        status TEXT DEFAULT 'New', created TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS portfolio(id INTEGER PRIMARY KEY, category TEXT, filename TEXT,
        created TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS galleries(id INTEGER PRIMARY KEY, title TEXT, client_name TEXT,
        code TEXT UNIQUE, pin TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS photos(id INTEGER PRIMARY KEY, gallery_id INTEGER, filename TEXT,
        favorite INTEGER DEFAULT 0);
    """)
    user = os.environ.get("ADMIN_USER", "admin")
    pw = os.environ.get("ADMIN_PASSWORD", "ChangeMe@123")
    if not c.execute("SELECT 1 FROM admin").fetchone():
        c.execute("INSERT INTO admin(username,pw) VALUES(?,?)", (user, generate_password_hash(pw)))
    c.commit(); c.close()

def allowed(fn): return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED

def save_upload(f):
    if not f or not f.filename or not allowed(f.filename): return None
    name = uuid.uuid4().hex + "." + secure_filename(f.filename).rsplit(".", 1)[1].lower()
    f.save(os.path.join(UPLOADS, name))
    return name

def admin_required(fn):
    @wraps(fn)
    def w(*a, **k):
        if not session.get("admin"): return redirect(url_for("admin_login"))
        return fn(*a, **k)
    return w

@app.context_processor
def inject():
    return dict(B=BUSINESS, inr=lambda n: "₹{:,}".format(int(n)))

@app.route("/media/<path:name>")
def media(name):
    return send_from_directory(UPLOADS, name)

# ---------- public ----------
@app.route("/")
def home():
    feat = db().execute("SELECT * FROM portfolio ORDER BY id DESC LIMIT 9").fetchall()
    return render_template("home.html", feat=feat, packages=PACKAGES, adv=ADVANCE_PERCENT, cats=CATEGORIES)

@app.route("/portfolio")
@app.route("/portfolio/<cat>")
def portfolio(cat=None):
    q, args = "SELECT * FROM portfolio", ()
    if cat: q, args = q + " WHERE category=?", (cat,)
    photos = db().execute(q + " ORDER BY id DESC", args).fetchall()
    return render_template("portfolio.html", photos=photos, cat=cat, cats=CATEGORIES)

@app.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":
        f = {k: request.form.get(k, "").strip() for k in
             ("name", "phone", "email", "occasion", "event_date", "location", "message")}
        if not f["name"] or len(f["phone"]) < 10 or not f["event_date"]:
            flash("Enter your name, a 10-digit phone number and the event date.", "err")
            return render_template("book.html", cats=CATEGORIES, places=PLACES, f=f)
        db().execute("""INSERT INTO bookings(name,phone,email,occasion,event_date,location,message)
                        VALUES(?,?,?,?,?,?,?)""", tuple(f.values()))
        db().commit()
        text = (f"New booking - {f['name']}\nPhone: {f['phone']}\nOccasion: {f['occasion']}\n"
                f"Date: {f['event_date']}\nPlace: {f['location']}\nNote: {f['message']}")
        return render_template("book_done.html", wa="https://wa.me/91%s?text=%s" % (BUSINESS["phone"], quote(text)), name=f["name"])
    return render_template("book.html", cats=CATEGORIES, places=PLACES, f={})

# ---------- client gallery ----------
@app.route("/client", methods=["GET", "POST"])
def client_login():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        pin = request.form.get("pin", "").strip()
        gal = db().execute("SELECT * FROM galleries WHERE code=?", (code,)).fetchone()
        if gal and secrets.compare_digest(gal["pin"], pin):
            session["gallery"] = gal["id"]
            return redirect(url_for("client_gallery"))
        flash("Gallery code or PIN is wrong. Check the message we sent you.", "err")
    return render_template("client_login.html")

@app.route("/client/gallery")
def client_gallery():
    gid = session.get("gallery")
    if not gid: return redirect(url_for("client_login"))
    gal = db().execute("SELECT * FROM galleries WHERE id=?", (gid,)).fetchone()
    photos = db().execute("SELECT * FROM photos WHERE gallery_id=? ORDER BY id", (gid,)).fetchall()
    return render_template("client_gallery.html", gal=gal, photos=photos)

@app.route("/client/favorite/<int:pid>", methods=["POST"])
def favorite(pid):
    gid = session.get("gallery")
    p = db().execute("SELECT * FROM photos WHERE id=? AND gallery_id=?", (pid, gid)).fetchone()
    if not p: abort(403)
    new = 0 if p["favorite"] else 1
    db().execute("UPDATE photos SET favorite=? WHERE id=?", (new, pid)); db().commit()
    return jsonify(favorite=new)

@app.route("/client/download/<int:pid>")
def download(pid):
    gid = session.get("gallery")
    p = db().execute("SELECT * FROM photos WHERE id=? AND gallery_id=?", (pid, gid)).fetchone()
    if not p: abort(403)
    return send_from_directory(UPLOADS, p["filename"], as_attachment=True)

@app.route("/client/logout")
def client_logout():
    session.pop("gallery", None); return redirect(url_for("home"))

# ---------- admin ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        row = db().execute("SELECT * FROM admin WHERE username=?", (request.form.get("username", ""),)).fetchone()
        if row and check_password_hash(row["pw"], request.form.get("password", "")):
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("Wrong username or password.", "err")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None); return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin():
    d = db()
    return render_template("admin.html",
        bookings=d.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall(),
        galleries=d.execute("SELECT g.*, (SELECT COUNT(*) FROM photos WHERE gallery_id=g.id) n, "
                            "(SELECT COUNT(*) FROM photos WHERE gallery_id=g.id AND favorite=1) fav "
                            "FROM galleries g ORDER BY id DESC").fetchall(),
        portfolio=d.execute("SELECT * FROM portfolio ORDER BY id DESC").fetchall(), cats=CATEGORIES)

@app.route("/admin/booking/<int:i>/status", methods=["POST"])
@admin_required
def booking_status(i):
    db().execute("UPDATE bookings SET status=? WHERE id=?", (request.form["status"], i)); db().commit()
    return redirect(url_for("admin") + "#bookings")

@app.route("/admin/booking/<int:i>/delete", methods=["POST"])
@admin_required
def booking_delete(i):
    db().execute("DELETE FROM bookings WHERE id=?", (i,)); db().commit()
    return redirect(url_for("admin") + "#bookings")

@app.route("/admin/portfolio/upload", methods=["POST"])
@admin_required
def portfolio_upload():
    n = 0
    for f in request.files.getlist("photos"):
        name = save_upload(f)
        if name:
            db().execute("INSERT INTO portfolio(category,filename) VALUES(?,?)", (request.form["category"], name)); n += 1
    db().commit(); flash(f"{n} photo(s) added to the portfolio.", "ok")
    return redirect(url_for("admin") + "#portfolio")

@app.route("/admin/portfolio/<int:i>/delete", methods=["POST"])
@admin_required
def portfolio_delete(i):
    r = db().execute("SELECT filename FROM portfolio WHERE id=?", (i,)).fetchone()
    if r:
        try: os.remove(os.path.join(UPLOADS, r["filename"]))
        except OSError: pass
        db().execute("DELETE FROM portfolio WHERE id=?", (i,)); db().commit()
    return redirect(url_for("admin") + "#portfolio")

@app.route("/admin/gallery/create", methods=["POST"])
@admin_required
def gallery_create():
    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    pin = "".join(secrets.choice(string.digits) for _ in range(4))
    db().execute("INSERT INTO galleries(title,client_name,code,pin) VALUES(?,?,?,?)",
                 (request.form["title"], request.form["client_name"], code, pin)); db().commit()
    flash(f"Gallery created. Code: {code}  PIN: {pin} - send both to the client.", "ok")
    return redirect(url_for("admin") + "#galleries")

@app.route("/admin/gallery/<int:i>")
@admin_required
def gallery_manage(i):
    gal = db().execute("SELECT * FROM galleries WHERE id=?", (i,)).fetchone() or abort(404)
    photos = db().execute("SELECT * FROM photos WHERE gallery_id=? ORDER BY id", (i,)).fetchall()
    return render_template("admin_gallery.html", gal=gal, photos=photos)

@app.route("/admin/gallery/<int:i>/upload", methods=["POST"])
@admin_required
def gallery_upload(i):
    n = 0
    for f in request.files.getlist("photos"):
        name = save_upload(f)
        if name:
            db().execute("INSERT INTO photos(gallery_id,filename) VALUES(?,?)", (i, name)); n += 1
    db().commit(); flash(f"{n} photo(s) uploaded.", "ok")
    return redirect(url_for("gallery_manage", i=i))

@app.route("/admin/photo/<int:pid>/delete", methods=["POST"])
@admin_required
def photo_delete(pid):
    r = db().execute("SELECT * FROM photos WHERE id=?", (pid,)).fetchone() or abort(404)
    try: os.remove(os.path.join(UPLOADS, r["filename"]))
    except OSError: pass
    db().execute("DELETE FROM photos WHERE id=?", (pid,)); db().commit()
    return redirect(url_for("gallery_manage", i=r["gallery_id"]))

@app.route("/admin/gallery/<int:i>/delete", methods=["POST"])
@admin_required
def gallery_delete(i):
    for r in db().execute("SELECT filename FROM photos WHERE gallery_id=?", (i,)).fetchall():
        try: os.remove(os.path.join(UPLOADS, r["filename"]))
        except OSError: pass
    db().execute("DELETE FROM photos WHERE gallery_id=?", (i,))
    db().execute("DELETE FROM galleries WHERE id=?", (i,)); db().commit()
    return redirect(url_for("admin") + "#galleries")

init_db()
if __name__ == "__main__":
    app.run(debug=True, port=5000)
