from functools import wraps
from flask import session, redirect, url_for, request
from datetime import datetime, timedelta
from database import get_setting

OWNER_TIMEOUT_MINUTES = 5


def owner_login(pin):
    """Validate PIN and create owner session."""
    correct = get_setting("owner_pin", "1234")
    if pin == correct:
        session["owner_logged_in"] = True
        session["owner_last_active"] = datetime.now().isoformat()
        session.permanent = False
        return True
    return False


def owner_logout():
    session.pop("owner_logged_in", None)
    session.pop("owner_last_active", None)


def is_owner_active():
    """Returns True only if logged in AND active within last 5 minutes."""
    if not session.get("owner_logged_in"):
        return False
    last = session.get("owner_last_active")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
        if datetime.now() - last_dt > timedelta(minutes=OWNER_TIMEOUT_MINUTES):
            owner_logout()
            return False
    except Exception:
        owner_logout()
        return False
    return True


def touch_owner_session():
    """Call this on every owner request to reset the 5-min timer."""
    if session.get("owner_logged_in"):
        session["owner_last_active"] = datetime.now().isoformat()


def owner_required(f):
    """Decorator — redirects to PIN screen if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_owner_active():
            return redirect(url_for("owner.login", next=request.path))
        touch_owner_session()
        return f(*args, **kwargs)
    return decorated
