import os
import logging

from flask import Flask, request, render_template, Response, session
from google import genai

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Ensure these environment variables are set in your deployment environment
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
if not GENAI_API_KEY:
    raise RuntimeError("Environment variable GENAI_API_KEY is required")

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "")
if not FLASK_SECRET_KEY:
    logging.warning("FLASK_SECRET_KEY is not set; sessions will be insecure")

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# -----------------------------------------------------------------------------
# Initialize AI client & Flask app
# -----------------------------------------------------------------------------

client = genai.Client(api_key=GENAI_API_KEY)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """
    Render the main HTML page containing the form and roadmap container.
    """
    return render_template("tem.html")


@app.route("/recommend", methods=["GET"])
def recommend():
    """
    Generate a personalized certification roadmap based on query parameters.
    Returns an HTML fragment wrapped in <div class="roadmap-phase">….
    """
    # Gather user inputs
    name  = request.args.get("name", "").strip()
    age   = request.args.get("age", "").strip()
    exp   = request.args.get("experience", "").strip()
    certs = request.args.get("current_certs", "").strip()
    intr  = request.args.get("interest", "").strip()
    tf    = request.args.get("timeframe", "").strip()

    # Build a simple profile text
    profile = []
    if name:  profile.append(f"- Name: {name}")
    if age:   profile.append(f"- Age: {age}")
    if exp:   profile.append(f"- Experience Level: {exp}")
    if certs: profile.append(f"- Current Certifications: {certs}")
    if intr:  profile.append(f"- Areas of Interest: {intr}")
    profile_text = "\n".join(profile)

    # Save profile in session for later explain-node calls
    session["user_profile"] = {
        "name": name,
        "age": age,
        "experience": exp,
        "current_certs": certs,
        "interest": intr
    }

    # Build the prompt asking Gemini to return a self-contained HTML fragment
    prompt = f"""
You are a friendly cybersecurity career advisor.
Generate a tailored certification roadmap (wrapped in <div class="roadmap-phase">…</div>)
for the user based on their profile below.

User Profile:
{profile_text}

Desired Timeframe: {tf}

IMPORTANT:
 - Return only the HTML fragment (no <html>, <head>, or <body> tags).
 - Use <h2>, <h3>, <ul>, <li> for structure.
 - Each phase must live inside its own <div class="roadmap-phase">.
"""

    logging.info("Requesting roadmap from Gemini AI…")
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        fragment = resp.text.strip() or "<p>No roadmap generated.</p>"
        return Response(fragment, mimetype="text/html")
    except Exception as e:
        logging.exception("Error generating roadmap")
        return Response(
            f"<p style='color:red;'>Error generating roadmap: {e}</p>",
            status=500,
            mimetype="text/html"
        )


@app.route("/explain-node", methods=["GET"])
def explain_node():
    """
    Given a data-title from an SVG node, return a concise HTML explanation fragment.
    """
    title = request.args.get("title", "").strip()
    if not title:
        return Response("Missing node title", status=400, mimetype="text/plain")

    # Reconstruct profile from session (or query params if provided)
    profile_data = session.get("user_profile", {})
    name  = request.args.get("name",  "").strip() or profile_data.get("name", "")
    age   = request.args.get("age",   "").strip() or profile_data.get("age", "")
    exp   = request.args.get("experience", "").strip() or profile_data.get("experience", "")
    certs = request.args.get("current_certs", "").strip() or profile_data.get("current_certs", "")
    intr  = request.args.get("interest", "").strip() or profile_data.get("interest", "")

    profile = []
    if name:  profile.append(f"- Name: {name}")
    if age:   profile.append(f"- Age: {age}")
    if exp:   profile.append(f"- Experience Level: {exp}")
    if certs: profile.append(f"- Current Certifications: {certs}")
    if intr:  profile.append(f"- Areas of Interest: {intr}")
    profile_text = "\n".join(profile)

    prompt = f"""
Teach the topic "{title}" in a concise, friendly tutorial style.
Context:
{profile_text}

IMPORTANT:
 - Return only a self-contained HTML fragment.
 - Wrap it in appropriate tags (e.g. <div>, <h2>, <p>).
 - No surrounding document boilerplate.
"""

    logging.info(f"Requesting explanation for '{title}'")
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        html = resp.text.strip() or "<div>No explanation available.</div>"
        return Response(html, mimetype="text/html")
    except Exception as e:
        logging.exception("Error generating explanation")
        return Response(
            f"<p style='color:red;'>Error generating explanation: {e}</p>",
            status=500,
            mimetype="text/html"
        )


# -----------------------------------------------------------------------------
# Application entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # In production, run under Gunicorn/UWSGI instead; set debug=False
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
