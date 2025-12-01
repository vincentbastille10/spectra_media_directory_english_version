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
    Response,
)

import stripe


# ============================================================
# FLASK CONFIG
# ============================================================

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

# Stripe
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
# INITIAL CATALOG — 50 AI TOOLS FOR BUSINESSES
# ============================================================

INITIAL_TOOLS = [
    # Productivity & Automation (but we feature Betty in Sales & Marketing)
    {
        "name": "Betty Bots",
        "website_url": "https://www.spectramedia.online/",
        "short_description": "AI lead-qualification assistants for small businesses and professionals.",
        "long_description": "",
        "category": "Sales & Marketing",
        "tags": "lead qualification, chatbot, assistant, SMB",
        "target_audience": "small businesses, agencies, local services, professionals",
        "pricing": "From €29.90 / month",
        "is_featured": 1,
    },
    {
        "name": "Notion AI",
        "website_url": "https://www.notion.so/product/ai",
        "short_description": "AI inside Notion to write, summarize and organize documents for teams.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "notes, knowledge base, writing assistant",
        "target_audience": "knowledge-heavy teams, product and ops teams",
        "pricing": "Add-on on top of Notion",
    },
    {
        "name": "ClickUp Brain",
        "website_url": "https://clickup.com/ai",
        "short_description": "AI that helps teams manage tasks, docs and project updates in ClickUp.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "project management, tasks, docs",
        "target_audience": "project teams, agencies, ops teams",
        "pricing": "Paid ClickUp plans",
    },
    {
        "name": "Motion",
        "website_url": "https://www.usemotion.com/",
        "short_description": "AI calendar and task manager that automatically plans your day.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "calendar, scheduling, productivity",
        "target_audience": "busy founders, managers, consultants",
        "pricing": "Subscription",
    },
    {
        "name": "Zapier AI",
        "website_url": "https://zapier.com/ai",
        "short_description": "Automate workflows between business apps with AI-assisted Zaps.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "automation, workflows, integrations",
        "target_audience": "non-technical teams that need automation",
        "pricing": "Free + paid tiers",
    },
    {
        "name": "Airtable AI",
        "website_url": "https://www.airtable.com/ai",
        "short_description": "AI on top of Airtable databases to generate, analyze and clean data.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "database, no-code, operations",
        "target_audience": "ops, product, marketing teams",
        "pricing": "Included in selected plans",
    },
    {
        "name": "Otter.ai",
        "website_url": "https://otter.ai/",
        "short_description": "AI note-taker that records, transcribes and summarizes meetings.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "meeting notes, transcription, summaries",
        "target_audience": "remote teams, sales, customer success",
        "pricing": "Free + paid tiers",
    },
    {
        "name": "Superhuman AI",
        "website_url": "https://superhuman.com/ai",
        "short_description": "Email client with AI-powered triage, replies and follow-ups.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "email, productivity",
        "target_audience": "executives, founders, sales roles",
        "pricing": "Subscription",
    },
    {
        "name": "Microsoft Copilot for 365",
        "website_url": "https://www.microsoft.com/en-us/microsoft-365/copilot",
        "short_description": "AI assistant integrated into Word, Excel, PowerPoint, Outlook and Teams.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "office suite, enterprise, writing",
        "target_audience": "Microsoft 365 companies",
        "pricing": "Per-user licence",
    },

    # Sales & Marketing
    {
        "name": "HubSpot AI",
        "website_url": "https://www.hubspot.com/artificial-intelligence",
        "short_description": "AI features across HubSpot CRM to write emails, score leads and analyze data.",
        "long_description": "",
        "category": "Sales & Marketing",
        "tags": "CRM, marketing automation, sales",
        "target_audience": "SMBs and mid-market sales & marketing teams",
        "pricing": "Included in HubSpot plans",
    },
    {
        "name": "Salesforce Einstein",
        "website_url": "https://www.salesforce.com/products/einstein-ai/overview/",
        "short_description": "AI layer on top of Salesforce CRM for predictions, scoring and insights.",
        "long_description": "",
        "category": "Sales & Marketing",
        "tags": "CRM, enterprise, forecasting",
        "target_audience": "Salesforce customers",
        "pricing": "Enterprise pricing",
    },
    {
        "name": "Apollo AI",
        "website_url": "https://www.apollo.io/",
        "short_description": "Prospecting and outbound sales platform with AI-generated emails.",
        "long_description": "",
        "category": "Sales & Marketing",
        "tags": "prospecting, B2B leads, emails",
        "target_audience": "outbound sales teams, SDRs",
        "pricing": "Free + paid tiers",
    },
    {
        "name": "Lavender",
        "website_url": "https://www.lavender.ai/",
        "short_description": "AI coach that helps write better cold emails that convert.",
        "long_description": "",
        "category": "Sales & Marketing",
        "tags": "email coaching, copywriting, sales",
        "target_audience": "sales reps, SDRs, founders doing outreach",
        "pricing": "Subscription",
    },
    {
        "name": "Lemlist AI",
        "website_url": "https://lemlist.com/",
        "short_description": "Cold outreach platform with AI-assisted personalization and sequences.",
        "long_description": "",
        "category": "Sales & Marketing",
        "tags": "outbound, personalization, campaigns",
        "target_audience": "growth teams, B2B founders",
        "pricing": "Subscription",
    },
    {
        "name": "Seventh Sense",
        "website_url": "https://www.theseventhsense.com/",
        "short_description": "AI that optimizes send-time for email campaigns to improve engagement.",
        "long_description": "",
        "category": "Sales & Marketing",
        "tags": "email optimization, marketing",
        "target_audience": "email marketers using HubSpot or Marketo",
        "pricing": "Subscription",
    },
    {
        "name": "Jasper",
        "website_url": "https://www.jasper.ai/",
        "short_description": "AI content platform to generate on-brand marketing copy at scale.",
        "long_description": "",
        "category": "Sales & Marketing",
        "tags": "copywriting, content marketing",
        "target_audience": "marketing teams, agencies",
        "pricing": "Subscription",
    },
    {
        "name": "Copy.ai",
        "website_url": "https://www.copy.ai/",
        "short_description": "AI assistant to create sales and marketing content faster.",
        "long_description": "",
        "category": "Sales & Marketing",
        "tags": "copywriting, automation, workflows",
        "target_audience": "sales, marketing, content teams",
        "pricing": "Free + paid tiers",
    },

    # Customer Support
    {
        "name": "Intercom Fin",
        "website_url": "https://www.intercom.com/ai",
        "short_description": "AI agent that answers support questions using your help center content.",
        "long_description": "",
        "category": "Customer Support",
        "tags": "AI agent, helpdesk, chat",
        "target_audience": "SaaS and B2B support teams",
        "pricing": "Intercom add-on",
    },
    {
        "name": "Zendesk AI",
        "website_url": "https://www.zendesk.com/service/ai/",
        "short_description": "AI features across Zendesk to route, suggest and automate support tickets.",
        "long_description": "",
        "category": "Customer Support",
        "tags": "ticketing, macros, chatbots",
        "target_audience": "teams using Zendesk",
        "pricing": "Included in selected plans",
    },
    {
        "name": "Freshdesk AI",
        "website_url": "https://www.freshworks.com/freshdesk/customer-support-software/ai/",
        "short_description": "AI for Freshdesk to handle routine questions and assist agents.",
        "long_description": "",
        "category": "Customer Support",
        "tags": "helpdesk, automation, chatbots",
        "target_audience": "SMB support teams",
        "pricing": "Subscription",
    },
    {
        "name": "Forethought",
        "website_url": "https://forethought.ai/",
        "short_description": "AI for support that deflects tickets and assists human agents.",
        "long_description": "",
        "category": "Customer Support",
        "tags": "deflection, agent assist",
        "target_audience": "support teams with high ticket volume",
        "pricing": "Enterprise",
    },
    {
        "name": "Ada",
        "website_url": "https://www.ada.cx/",
        "short_description": "AI-powered customer service automation for chat and messaging.",
        "long_description": "",
        "category": "Customer Support",
        "tags": "chatbot, automation, enterprise",
        "target_audience": "e-commerce, fintech, SaaS",
        "pricing": "Enterprise",
    },
    {
        "name": "Ultimate.ai",
        "website_url": "https://www.ultimate.ai/",
        "short_description": "AI platform to automate repetitive support requests across channels.",
        "long_description": "",
        "category": "Customer Support",
        "tags": "ticket automation, chat, email",
        "target_audience": "support teams on Zendesk, Salesforce, etc.",
        "pricing": "Subscription",
    },
    {
        "name": "Tidio AI",
        "website_url": "https://www.tidio.com/",
        "short_description": "AI chatbots for small businesses to answer customers 24/7.",
        "long_description": "",
        "category": "Customer Support",
        "tags": "live chat, chatbot, ecommerce",
        "target_audience": "online stores, SMB websites",
        "pricing": "Free + paid tiers",
    },
    {
        "name": "Gorgias AI",
        "website_url": "https://www.gorgias.com/",
        "short_description": "Helpdesk for e-commerce with AI-assisted replies and macros.",
        "long_description": "",
        "category": "Customer Support",
        "tags": "ecommerce, Shopify, support",
        "target_audience": "brands and online shops",
        "pricing": "Subscription",
    },

    # Data & Analytics
    {
        "name": "Power BI with Copilot",
        "website_url": "https://powerbi.microsoft.com/",
        "short_description": "Use natural language to explore data and build visuals in Power BI.",
        "long_description": "",
        "category": "Data & Analytics",
        "tags": "BI, dashboards, Microsoft",
        "target_audience": "analytics and finance teams",
        "pricing": "Power BI plans + Copilot",
    },
    {
        "name": "Tableau AI",
        "website_url": "https://www.tableau.com/products/ai",
        "short_description": "AI assistance inside Tableau for insights, explanations and predictions.",
        "long_description": "",
        "category": "Data & Analytics",
        "tags": "BI, data viz, analytics",
        "target_audience": "Tableau users",
        "pricing": "Enterprise",
    },
    {
        "name": "Hex",
        "website_url": "https://hex.tech/",
        "short_description": "Notebook-style analytics with AI assistance for queries and narratives.",
        "long_description": "",
        "category": "Data & Analytics",
        "tags": "analytics, notebooks, collaboration",
        "target_audience": "data teams, analysts",
        "pricing": "Subscription",
    },
    {
        "name": "Mode AI",
        "website_url": "https://mode.com/",
        "short_description": "BI platform with AI to help write SQL and explain dashboards.",
        "long_description": "",
        "category": "Data & Analytics",
        "tags": "BI, SQL, dashboards",
        "target_audience": "analysts, business teams",
        "pricing": "Subscription",
    },
    {
        "name": "Obviously.ai",
        "website_url": "https://obviously.ai/",
        "short_description": "No-code predictive analytics for business users.",
        "long_description": "",
        "category": "Data & Analytics",
        "tags": "predictions, no-code, analytics",
        "target_audience": "non-technical business users",
        "pricing": "Subscription",
    },
    {
        "name": "Akkio",
        "website_url": "https://www.akkio.com/",
        "short_description": "No-code AI platform to build predictive models on business data.",
        "long_description": "",
        "category": "Data & Analytics",
        "tags": "no-code, ML, analytics",
        "target_audience": "ops, marketing, sales",
        "pricing": "Subscription",
    },
    {
        "name": "BigQuery with Duet AI",
        "website_url": "https://cloud.google.com/bigquery",
        "short_description": "Use natural language to help query and explore data in BigQuery.",
        "long_description": "",
        "category": "Data & Analytics",
        "tags": "data warehouse, SQL, Google Cloud",
        "target_audience": "data teams on GCP",
        "pricing": "Usage-based",
    },
    {
        "name": "Dataiku",
        "website_url": "https://www.dataiku.com/",
        "short_description": "Enterprise platform to build and deploy AI projects collaboratively.",
        "long_description": "",
        "category": "Data & Analytics",
        "tags": "ML platform, enterprise",
        "target_audience": "large data & analytics teams",
        "pricing": "Enterprise",
    },

    # Content & Design
    {
        "name": "Canva Magic Studio",
        "website_url": "https://www.canva.com/magic-studio/",
        "short_description": "AI features in Canva to generate designs, copy and images.",
        "long_description": "",
        "category": "Content & Design",
        "tags": "design, templates, images",
        "target_audience": "marketing teams, social media managers",
        "pricing": "Free + Pro",
    },
    {
        "name": "Adobe Firefly",
        "website_url": "https://www.adobe.com/sensei/generative-ai.html",
        "short_description": "Generative AI for images and text integrated into Adobe tools.",
        "long_description": "",
        "category": "Content & Design",
        "tags": "creative cloud, images, design",
        "target_audience": "designers, creative teams",
        "pricing": "Included in Adobe plans",
    },
    {
        "name": "Descript",
        "website_url": "https://www.descript.com/",
        "short_description": "AI-powered audio & video editor with transcripts and overdub.",
        "long_description": "",
        "category": "Content & Design",
        "tags": "podcast, video, editing",
        "target_audience": "content creators, marketers",
        "pricing": "Free + paid tiers",
    },
    {
        "name": "Runway",
        "website_url": "https://runwayml.com/",
        "short_description": "Generative video and AI editing tools for creators and studios.",
        "long_description": "",
        "category": "Content & Design",
        "tags": "video, generative, VFX",
        "target_audience": "video teams, creative studios",
        "pricing": "Subscription",
    },
    {
        "name": "Synthesia",
        "website_url": "https://www.synthesia.io/",
        "short_description": "Create AI-generated videos with avatars and voiceover from text.",
        "long_description": "",
        "category": "Content & Design",
        "tags": "training, explainer videos",
        "target_audience": "L&D teams, marketing, HR",
        "pricing": "Subscription",
    },
    {
        "name": "ElevenLabs",
        "website_url": "https://elevenlabs.io/",
        "short_description": "High-quality AI voice generation for content, games and support.",
        "long_description": "",
        "category": "Content & Design",
        "tags": "voice, audio, TTS",
        "target_audience": "media companies, game studios, creators",
        "pricing": "Usage-based",
    },
    {
        "name": "Midjourney",
        "website_url": "https://www.midjourney.com/",
        "short_description": "Image generation model for creative and commercial visuals.",
        "long_description": "",
        "category": "Content & Design",
        "tags": "images, branding, concept art",
        "target_audience": "designers, agencies, artists",
        "pricing": "Subscription",
    },
    {
        "name": "DALL·E",
        "website_url": "https://openai.com/dall-e-3",
        "short_description": "Generate high-quality images from text prompts.",
        "long_description": "",
        "category": "Content & Design",
        "tags": "image generation, creative",
        "target_audience": "marketing, product, design",
        "pricing": "Usage-based",
    },

    # Developer & Ops
    {
        "name": "GitHub Copilot",
        "website_url": "https://github.com/features/copilot",
        "short_description": "AI pair programmer that suggests code and tests inside your IDE.",
        "long_description": "",
        "category": "Developer & Ops",
        "tags": "coding, productivity, IDE",
        "target_audience": "software engineers, teams on GitHub",
        "pricing": "Per-user",
    },
    {
        "name": "Cursor",
        "website_url": "https://www.cursor.com/",
        "short_description": "AI-native code editor that understands your repo and helps ship faster.",
        "long_description": "",
        "category": "Developer & Ops",
        "tags": "IDE, AI assistant, coding",
        "target_audience": "dev teams, startups",
        "pricing": "Free + paid tiers",
    },
    {
        "name": "Replit Agent",
        "website_url": "https://replit.com/",
        "short_description": "AI agents that can write, run and iterate code in the browser.",
        "long_description": "",
        "category": "Developer & Ops",
        "tags": "coding, prototyping, agents",
        "target_audience": "indie hackers, learners, teams",
        "pricing": "Usage-based",
    },
    {
        "name": "AWS CodeWhisperer",
        "website_url": "https://aws.amazon.com/codewhisperer/",
        "short_description": "AI coding companion integrated with AWS tooling.",
        "long_description": "",
        "category": "Developer & Ops",
        "tags": "cloud, AWS, coding",
        "target_audience": "developers building on AWS",
        "pricing": "Free + pro",
    },
    {
        "name": "Codeium",
        "website_url": "https://codeium.com/",
        "short_description": "AI code completion and chat for multiple IDEs.",
        "long_description": "",
        "category": "Developer & Ops",
        "tags": "autocomplete, IDE, teams",
        "target_audience": "dev teams, enterprises",
        "pricing": "Free + enterprise",
    },
    {
        "name": "Snyk AI",
        "website_url": "https://snyk.io/product/snyk-ai/",
        "short_description": "AI that helps find and fix security issues in code and dependencies.",
        "long_description": "",
        "category": "Developer & Ops",
        "tags": "security, DevSecOps",
        "target_audience": "security and dev teams",
        "pricing": "Subscription",
    },
    {
        "name": "Datadog AI",
        "website_url": "https://www.datadoghq.com/",
        "short_description": "AI-assisted observability to detect anomalies and incidents faster.",
        "long_description": "",
        "category": "Developer & Ops",
        "tags": "monitoring, observability",
        "target_audience": "SRE, DevOps, platform teams",
        "pricing": "Usage-based",
    },
    {
        "name": "PagerDuty AIOps",
        "website_url": "https://www.pagerduty.com/solutions/aiops/",
        "short_description": "AI to reduce noise and speed up incident response.",
        "long_description": "",
        "category": "Developer & Ops",
        "tags": "incident management, alerts",
        "target_audience": "on-call and operations teams",
        "pricing": "Subscription",
    },

    # Extras (Productivity)
    {
        "name": "Slack AI",
        "website_url": "https://slack.com/ai",
        "short_description": "AI in Slack to summarize channels, search and catch up faster.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "collaboration, chat, summaries",
        "target_audience": "teams already on Slack",
        "pricing": "Add-on",
    },
    {
        "name": "Miro Assist",
        "website_url": "https://miro.com/miro-assist/",
        "short_description": "AI assistant in Miro to cluster ideas, summarize boards and generate content.",
        "long_description": "",
        "category": "Productivity & Automation",
        "tags": "whiteboard, workshops, collaboration",
        "target_audience": "product teams, facilitators, agencies",
        "pricing": "Included in selected plans",
    },
]


def seed_initial_tools() -> None:
    """
    Seed the SQLite database with an initial catalog of ~50 business-oriented AI tools.
    This only runs when the table is empty, so user-submitted tools are never overwritten.
    """
    with get_db() as db:
        cur = db.execute("SELECT COUNT(*) AS c FROM tools")
        row = cur.fetchone()
        if row and row["c"] > 0:
            return  # Already populated

        now = datetime.utcnow().isoformat()
        for t in INITIAL_TOOLS:
            slug = slugify(t["name"])
            db.execute(
                """
                INSERT OR IGNORE INTO tools
                (name, slug, website_url,
                 short_description, long_description,
                 category, tags, target_audience,
                 pricing, is_featured, is_approved, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t["name"],
                    slug,
                    t["website_url"],
                    t["short_description"],
                    t.get("long_description", "") or "",
                    t.get("category", "Productivity & Automation"),
                    t.get("tags", "") or "",
                    t.get("target_audience", "") or "",
                    t.get("pricing", "") or "",
                    1 if t.get("is_featured") else 0,
                    1,
                    now,
                ),
            )


# Initialize DB on import (good for Render/Vercel)
init_db()
seed_initial_tools()


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
            ORDER BY is_featured DESC, name COLLATE NOCASE ASC
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
            ORDER BY is_featured DESC, name COLLATE NOCASE ASC
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

            # New tools: NOT approved until Stripe payment is confirmed
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
                    0,  # is_featured
                    0,  # is_approved -> will be set to 1 after Stripe payment
                    created_at,
                ),
            )

        flash("Your AI tool has been saved. Please complete payment to publish it.", "success")

        # If Stripe is configured, redirect user to payment page
        if STRIPE_SECRET_KEY and STRIPE_PRICE_ID:
            return redirect(url_for("start_checkout", slug=slug))

        # If no Stripe configured, publish immediately (fallback)
        with get_db() as db:
            db.execute(
                "UPDATE tools SET is_approved = 1 WHERE slug = ?",
                (slug,),
            )
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

    # Fetch tool (should exist, just created)
    with get_db() as db:
        cur = db.execute(
            "SELECT * FROM tools WHERE slug = ?",
            (slug,),
        )
        tool = cur.fetchone()

    if tool is None:
        abort(404)

    # success_url with slug + {CHECKOUT_SESSION_ID} placeholder
    success_url = f"{STRIPE_SUCCESS_URL}?slug={slug}&session_id={{CHECKOUT_SESSION_ID}}"

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }
        ],
        success_url=success_url,
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
    Called by Stripe redirect after payment.
    We verify the Checkout Session and, if paid, mark the tool as approved.
    """
    slug = request.args.get("slug")
    session_id = request.args.get("session_id")

    if not slug:
        abort(400)

    if STRIPE_SECRET_KEY and session_id:
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            payment_status = getattr(s, "payment_status", None) or s.get("payment_status")
        except Exception:
            payment_status = None

        if payment_status == "paid":
            with get_db() as db:
                db.execute(
                    "UPDATE tools SET is_approved = 1 WHERE slug = ?",
                    (slug,),
                )

    return render_template("checkout_success.html", slug=slug)


@app.route("/checkout/cancel")
def checkout_cancel():
    flash("Payment cancelled. Your AI tool is saved but not published.", "error")
    return redirect(url_for("annuaire_list"))


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", content="<h1>404 – Page not found</h1>"), 404
# ============================================================
# GOOGLE SEARCH CONSOLE VERIFICATION
# ============================================================

@app.route("/google8334646a4a411e97.html")
def google_verify():
    # must match EXACT Google expected content
    return "google-site-verification: google8334646a4a411e97.html"

# ============================================================
# SEO: robots.txt + sitemap.xml
# ============================================================

@app.route("/robots.txt")
def robots_txt():
    """
    Robots.txt generated dynamically.
    Tells Google the site is indexable and where the sitemap is.
    """
    base = request.url_root.rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {base}/sitemap.xml",
        "",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    """
    XML sitemap for Google and other search engines.
    Includes:
    - main pages (/, /directory, /add)
    - one URL per approved tool (/tool/<slug>)
    """
    base = request.url_root.rstrip("/")

    static_urls = [
        {"loc": f"{base}/", "priority": "1.0"},
        {"loc": f"{base}/directory", "priority": "0.9"},
        {"loc": f"{base}/add", "priority": "0.8"},
    ]

    with get_db() as db:
        cur = db.execute(
            """
            SELECT slug, created_at
            FROM tools
            WHERE is_approved = 1
            ORDER BY created_at DESC
            """
        )
        tools = cur.fetchall()

    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    # Static URLs
    for u in static_urls:
        xml.append("  <url>")
        xml.append(f"    <loc>{u['loc']}</loc>")
        xml.append(f"    <priority>{u['priority']}</priority>")
        xml.append("  </url>")

    # Tool URLs
    for t in tools:
        loc = f"{base}/tool/{t['slug']}"
        lastmod = t["created_at"] or datetime.utcnow().isoformat()

        xml.append("  <url>")
        xml.append(f"    <loc>{loc}</loc>")
        xml.append(f"    <lastmod>{lastmod}</lastmod>")
        xml.append("    <priority>0.7</priority>")
        xml.append("  </url>")

    xml.append("</urlset>")

    return Response("\n".join(xml), mimetype="application/xml")

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # For local testing only
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
