import os
import sys
import uuid

# Make the project root importable (needed so `app/` resolves both
# locally and inside Vercel's serverless function bundle).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv

load_dotenv()

from app.rag import ingest_pdf, answer_question, list_papers, delete_paper  # noqa: E402
from app.readiness import check_readiness  # noqa: E402

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT, "templates"),
    static_folder=os.path.join(ROOT, "static"),
)

# SECRET_KEY signs the session cookie that carries each visitor's
# owner_id. Set a real fixed value in .env / Vercel env vars - if it's
# missing we fall back to a random key, but on serverless that key
# changes on every cold start, which would reset everyone's session
# (and their papers becoming "invisible") unpredictably.
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

# Keep each device's document space around long-term instead of resetting
# every time the browser closes. This doesn't change privacy - it's still
# one cookie per device/browser, so different devices never see each
# other's papers - it just makes that cookie last a year instead of a tab.
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 365  # 1 year


@app.before_request
def ensure_session():
    """No login required - just silently give each new browser its own
    private, long-lived document space, scoped to this session cookie."""
    session.permanent = True
    if "owner_id" not in session:
        session["owner_id"] = str(uuid.uuid4())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400
    try:
        result = ingest_pdf(file.read(), file.filename, session["owner_id"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def query():
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "").strip()
    paper_id = data.get("paper_id") or None
    if not question:
        return jsonify({"error": "Question is required"}), 400
    try:
        result = answer_question(
            question, session["owner_id"], paper_id=paper_id
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/papers", methods=["GET"])
def papers():
    try:
        return jsonify(list_papers(session["owner_id"]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/papers/<paper_id>", methods=["DELETE"])
def remove_paper(paper_id):
    try:
        delete_paper(session["owner_id"], paper_id)
        return jsonify({"deleted": paper_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/papers/<paper_id>/readiness", methods=["POST"])
def readiness(paper_id):
    data = request.get_json(silent=True) or {}
    title = data.get("title", "this paper")
    try:
        result = check_readiness(session["owner_id"], paper_id, title)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
