"""Student Success Hub - application factory and entry point.

Run:  python app.py        (development server on http://127.0.0.1:5000)
"""
from datetime import date

from flask import Flask, g, render_template, request, session
from flask_wtf.csrf import CSRFError, CSRFProtect

import db
from config import Config

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    csrf.init_app(app)
    db.init_app(app)
    with app.app_context():
        db.init_db()  # creates tables on first run

    from routes import auth, coach, main, plans, tasks
    for module in (auth, main, tasks, plans, coach):
        app.register_blueprint(module.bp)

    @app.before_request
    def load_user():
        g.user = None
        uid = session.get("user_id")
        if uid is not None:
            g.user = db.get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
            if g.user is None:
                session.clear()

    @app.context_processor
    def inject_globals():
        from services import ai_service
        return {"today": date.today(), "ai_online": ai_service.is_configured()}

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if g.get("user"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        if request.path.startswith("/api/"):
            return {"error": "Your session expired. Refresh the page and try again."}, 400
        return render_template("errors/error.html", code=400,
                               message="Your form session expired. Go back, refresh the page and try again."), 400

    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return {"error": "Not found."}, 404
        return render_template("errors/error.html", code=404,
                               message="That page does not exist."), 404

    @app.errorhandler(500)
    def server_error(_e):
        if request.path.startswith("/api/"):
            return {"error": "Something went wrong on the server."}, 500
        return render_template("errors/error.html", code=500,
                               message="Something went wrong on our side. Please try again."), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
