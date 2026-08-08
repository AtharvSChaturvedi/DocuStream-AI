import os
import sys

# Make the project root importable (needed so `app/` resolves both
# locally and inside Vercel's serverless function bundle).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

from app.rag import ingest_pdf, answer_question, list_papers  # noqa: E402

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT, "templates"),
    static_folder=os.path.join(ROOT, "static"),
)


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
        result = ingest_pdf(file.read(), file.filename)
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
        result = answer_question(question, paper_id=paper_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/papers", methods=["GET"])
def papers():
    try:
        return jsonify(list_papers())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
