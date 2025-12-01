# Spectra AI Directory — English Version

This is an **English alternative** of the Spectra AI Directory project.

- Target: companies and professionals looking for AI tools.
- Tech stack: Python + Flask + SQLite + Stripe Checkout (optional).
- Structure kept simple so it can be deployed on Render / Vercel-compatible Python environment.

## Main routes

- `/` — Landing page (English) with a preview of a few tools.
- `/directory` and `/annuaire` — Full directory with 6 blue category filters and an alphabetical list.
- `/tool/<slug>` — Detail page for each AI tool.
- `/add` and `/ajouter` — Form to submit a new AI tool (UI in English).
- `/checkout/<slug>` — Starts a Stripe Checkout session (if Stripe is configured).
- `/checkout/success` — Confirmation page after payment.
- `/checkout/cancel` — Cancel page.

## Environment variables

Create a `.env` file or set environment variables in your hosting provider:

- `FLASK_SECRET_KEY` — random secret string.
- `STRIPE_SECRET_KEY` — your Stripe secret key (optional for local dev).
- `STRIPE_PRICE_ID` — Stripe price ID for the 20€ listing.
- `STRIPE_SUCCESS_URL` — absolute URL of `/checkout/success` in production.
- `STRIPE_CANCEL_URL` — absolute URL of `/checkout/cancel` in production.

If Stripe variables are **not** set, the app still works; it simply skips the payment redirection.

## Local setup

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install -r requirements.txt
export FLASK_APP=app.py
flask run  # or: python app.py
```

The SQLite database (`spectra_ai_directory.db`) is created automatically on first run.

## Notes

- All interface text is in English.
- The 6 category buttons are defined in `get_categories()` in `app.py`.
- You can safely duplicate this repository as a **separate GitHub repo** for the English version and route traffic to it once it's online.
