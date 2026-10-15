# MK Photography - Flask + SQLite

## Run
    pip install -r requirements.txt
    export ADMIN_USER=mallu ADMIN_PASSWORD='your-strong-password' SECRET_KEY='long-random-text'
    python app.py            # open http://127.0.0.1:5000

Set ADMIN_USER / ADMIN_PASSWORD BEFORE the first run (the admin account is created once).
Default if you skip it: admin / ChangeMe@123 - change it.

## Pages
- /                 Home, packages, how booking works
- /portfolio        Photos by category (uploaded from admin)
- /book             Booking form (saved to database + WhatsApp message)
- /client           Client opens private gallery with code + PIN, marks favorites, downloads
- /admin            Bookings, client galleries, portfolio upload

## Edit your details
Top of app.py: BUSINESS (phone, email, Instagram), CATEGORIES, PLACES, PACKAGES (prices).

## Deploy
Use gunicorn:  gunicorn -w 2 app:app   (PythonAnywhere / Render / a VPS). Keep mk.db and uploads/ backed up.
