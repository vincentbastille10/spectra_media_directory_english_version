
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    abort,
    flash,
)

import stripe


# ============================================================
# FLASK CONFIG
# ============================================================

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

# Stripe (optional but ready)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")  # recurring or one-time price
STRIPE_SUCCESS_URL = os.getenv(
    "STRIPE_SUCCESS_URL",
    "http://localhost:5000/checkout/success",
)
STRIPE_CANCEL_URL = os.getenv(
    "STRIPE_CANCEL_URL",
    "http://localhost:5000/checkout/cancel",
)

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# ============================================================
# DATABASE
# ============================================================

DB_PATH = os.path.join(os.path.dirname(__file__), "spectra_ai_directory.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                website_url TEXT NOT NULL,
                short_description TEXT NOT NULL,
                long_description TEXT,
                category TEXT NOT NULL,
                tags TEXT,
                target_audience TEXT,
                pricing TEXT,
                is_featured INTEGER DEFAULT 0,
                is_approved INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )


# Create DB on first run
init_db()


# ============================================================
# HELPERS
# ============================================================

def slugify(name: str) -> str:
    import re

    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "tool"


def get_categories():
    """
    Central place for the 6 main categories.
    These labels are what we display in the UI.
    """
    return [
        "Productivity & Automation",
        "Sales & Marketing",
        "Customer Support",
        "Data & Analytics",
        "Content & Design",
        "Developer & Ops",
    ]


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    """
    Landing page for the English version of the Spectra AI Directory.
    Focused on companies and professionals.
    """
    with get_db() as db:
        cur = db.execute(
            """
            SELECT * FROM tools
            WHERE is_approved = 1
            ORDER BY name COLLATE NOCASE ASC
            """
        )
        tools = cur.fetchall()

    categories = get_categories()
    return render_template(
        "index.html",
        tools=tools,
        categories=categories,
        stripe_enabled=bool(STRIPE_SECRET_KEY and STRIPE_PRICE_ID),
    )


@app.route("/directory")
@app.route("/annuaire")
def annuaire_list():
    """
    Full tools directory.
    Same content as index, but dedicated URL for sharing.
    """
    with get_db() as db:
        cur = db.execute(
            """
            SELECT * FROM tools
            WHERE is_approved = 1
            ORDER BY name COLLATE NOCASE ASC
            """
        )
        tools = cur.fetchall()

    categories = get_categories()
    return render_template(
        "annuaire_list.html",
        tools=tools,
        categories=categories,
        stripe_enabled=bool(STRIPE_SECRET_KEY and STRIPE_PRICE_ID),
    )


@app.route("/tool/<slug>")
def tool_detail(slug: str):
    with get_db() as db:
        cur = db.execute(
            "SELECT * FROM tools WHERE slug = ? AND is_approved = 1",
            (slug,),
        )
        tool = cur.fetchone()

    if tool is None:
        abort(404)

    return render_template("tool_detail.html", tool=tool)


@app.route("/add", methods=["GET", "POST"])
@app.route("/ajouter", methods=["GET", "POST"])
def ajouter():
    """
    Add a new tool to the directory.
    In this English version, the UI is fully in English,
    but we keep the /ajouter route for backward compatibility.
    """
    categories = get_categories()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        website_url = request.form.get("website_url", "").strip()
        short_description = request.form.get("short_description", "").strip()
        long_description = request.form.get("long_description", "").strip()
        category = request.form.get("category", "").strip()
        tags = request.form.get("tags", "").strip()
        target_audience = request.form.get("target_audience", "").strip()
        pricing = request.form.get("pricing", "").strip()

        if not name or not website_url or not short_description:
            flash("Please fill at least the name, website URL and short description.", "error")
            return render_template(
                "ajouter.html",
                categories=categories,
                form=request.form,
            )

        slug = slugify(name)
        created_at = datetime.utcnow().isoformat()

        with get_db() as db:
            # Ensure slug is unique (append counter if needed)
            base_slug = slug
            counter = 1
            while True:
                cur = db.execute(
                    "SELECT COUNT(*) AS c FROM tools WHERE slug = ?",
                    (slug,),
                )
                if cur.fetchone()["c"] == 0:
                    break
                counter += 1
                slug = f"{base_slug}-{counter}"

            db.execute(
                """
                INSERT INTO tools (
                    name, slug, website_url,
                    short_description, long_description,
                    category, tags, target_audience,
                    pricing, is_featured, is_approved, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    slug,
                    website_url,
                    short_description,
                    long_description,
                    category or "Productivity & Automation",
                    tags,
                    target_audience,
                    pricing,
                    0,
                    1,  # directly approved for now
                    created_at,
                ),
            )

        flash("Thanks! Your AI tool has been added to the directory.", "success")

        # If Stripe is configured, redirect user to payment page
        if STRIPE_SECRET_KEY and STRIPE_PRICE_ID:
            return redirect(url_for("start_checkout", slug=slug))

        return redirect(url_for("annuaire_list"))

    return render_template(
        "ajouter.html",
        categories=categories,
        form={},
    )


@app.route("/checkout/<slug>")
def start_checkout(slug: str):
    """
    Create a Stripe Checkout session for the AI tool listing payment.
    """
    if not (STRIPE_SECRET_KEY and STRIPE_PRICE_ID):
        flash("Stripe is not configured yet. Please contact us directly.", "error")
        return redirect(url_for("annuaire_list"))

    # We do not strictly need the tool here, but we try to fetch it
    with get_db() as db:
        cur = db.execute(
            "SELECT * FROM tools WHERE slug = ?",
            (slug,),
        )
        tool = cur.fetchone()

    if tool is None:
        abort(404)

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }
        ],
        success_url=STRIPE_SUCCESS_URL + "?slug=" + slug,
        cancel_url=STRIPE_CANCEL_URL,
        metadata={
            "tool_slug": slug,
            "tool_name": tool["name"],
        },
    )

    return redirect(session.url, code=303)


@app.route("/checkout/success")
def checkout_success():
    """
    Simple confirmation page.
    The Stripe webhook should be used in a real deployment
    to mark the payment as validated on our side.
    """
    slug = request.args.get("slug")
    return render_template("checkout_success.html", slug=slug)


@app.route("/checkout/cancel")
def checkout_cancel():
    flash("Payment cancelled. Your AI tool is still saved but not confirmed yet.", "error")
    return redirect(url_for("annuaire_list"))


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", content="<h1>404 – Page not found</h1>"), 404


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # For local testing only
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
