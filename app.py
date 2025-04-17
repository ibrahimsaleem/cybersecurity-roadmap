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
    # Collect user inputs
    name  = request.args.get("name", "").strip()
    age   = request.args.get("age", "").strip()
    exp   = request.args.get("experience", "").strip()
    certs = request.args.get("current_certs", "").strip()
    intr  = request.args.get("interest", "").strip()
    tf    = request.args.get("timeframe", "").strip()
   
    # Build profile details dynamically
    profile_lines = []
    if name:
        profile_lines.append(f"- Name: {name}")
    if age:
        profile_lines.append(f"- Age: {age}")
    if exp:
        profile_lines.append(f"- Experience Level: {exp}")
    if certs:
        profile_lines.append(f"- Current Certifications: {certs}")
    if intr:
        profile_lines.append(f"- Areas of Interest: {intr}")
    profile_text = "\n".join(profile_lines)
    
    # Save the user profile into session for later use
    session["user_profile"] = {
        "name": name,
        "age": age,
        "experience": exp,
        "current_certs": certs,
        "interest": intr
    }
    
    # Build prompt, requesting HTML with roadmap-phase classes
    prompt = f"""
You are a cybersecurity career advisor with a fun and personal touch. Based on the user's profile, generate a personalized certification roadmap and guidance for that perosn say his name.

**IMPORTANT**: Return a self‑contained HTML fragment only.  
- Wrap each phase in <div class="roadmap-phase">…</div>.  
- Use <h2>, <h3>, <ul>, <li> for structure.  
- No external CSS or JS—just the fragment.

User Profile:
{profile_text}
Desired Roadmap Timeframe: {tf}
"""

    logging.info("Requesting HTML roadmap from Gemini AI…")
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        html_fragment = resp.text.strip() or "<p>No roadmap generated.</p>"
        return Response(html_fragment, status=200, mimetype="text/html")
    except Exception as e:
        logging.exception("Error generating roadmap")
        return Response(f"<p style='color:red;'>Error: {e}</p>", status=500, mimetype="text/html")



@app.route("/explain-node", methods=["GET"])
def explain_node():
    title = request.args.get("title", "").strip()
    if not title:
        return "Missing node title", 400, {"Content-Type": "text/plain; charset=utf-8"}
    
    # Collect optional personal parameters from current request or saved session
    name          = request.args.get("name", "").strip() or session.get("user_profile", {}).get("name", "")
    age           = request.args.get("age", "").strip() or session.get("user_profile", {}).get("age", "")
    experience    = request.args.get("experience", "").strip() or session.get("user_profile", {}).get("experience", "")
    current_certs = request.args.get("current_certs", "").strip() or session.get("user_profile", {}).get("current_certs", "")
    interest      = request.args.get("interest", "").strip() or session.get("user_profile", {}).get("interest", "")
    
    # Build profile only with non-empty fields
    profile_lines = []
    if name:
        profile_lines.append(f"- Name: {name}")
    if age:
        profile_lines.append(f"- Age: {age}")
    if experience:
        profile_lines.append(f"- Experience Level: {experience}")
    if current_certs:
        profile_lines.append(f"- Current Certifications: {current_certs}")
    if interest:
        profile_lines.append(f"- Areas of Interest: {interest}")
    profile_text = "\n".join(profile_lines)
    
    prompt = f"""Teach the topic '{title}' in a concise, personal, and fun tutorial style for {name or 'the user'}.
User Profile:
{profile_text}

**IMPORTANT**: Return a self-contained HTML fragment only.  
- Wrap the explanation in appropriate HTML elements (e.g. <div>, <h2>, <p>).
- Do not include any extra text.

Provide a short, clear explanation on this topic in the context of cybersecurity certifications and training."""
    
    logging.info(f"Requesting explanation for node: {title} with profile:\n{profile_text or 'No extra profile provided.'}")
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        html_response = resp.text.strip() or "<div>No explanation found.</div>"
        return Response(html_response, status=200, mimetype="text/html")
    except Exception as e:
        logging.exception("Error during node explanation")
        return f"<p style='color:red;'>❌ Error: {e}</p>", 500, {"Content-Type": "text/html"}


# -----------------------------------------------------------------------------
# Application entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # In production, run under Gunicorn/UWSGI instead; set debug=False
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
