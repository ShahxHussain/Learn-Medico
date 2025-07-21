from flask import Flask, render_template, request, jsonify
from faiss_store import ChapterFaissStore
from together_rag import TogetherRAG
import os

app = Flask(__name__)

FAISS_INDEX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../faiss_indexes'))
faiss_store = ChapterFaissStore(index_dir=FAISS_INDEX_DIR)
rag = TogetherRAG(faiss_store)
CHAPTERS = ["Full Book", "UNIT 1"]

@app.route("/")
def index():
    return render_template("rag_ui.html", chapters=CHAPTERS)

@app.route("/generate_notes", methods=["POST"])
def generate_notes():
    chapter = request.json.get("chapter")
    try:
        notes = rag.generate_chapter_notes(chapter)
        return jsonify({"success": True, "notes": notes})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/generate_mcqs", methods=["POST"])
def generate_mcqs():
    chapter = request.json.get("chapter")
    num_mcqs = int(request.json.get("num_mcqs", 3))
    try:
        mcqs = rag.generate_mcq(chapter, num_mcqs=num_mcqs, num_options=4)
        # Don't send correct answers to the frontend!
        for mcq in mcqs:
            mcq.pop("correct")
            mcq.pop("correct_letter")
            mcq.pop("explanation")
        return jsonify({"success": True, "mcqs": mcqs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/check_mcqs", methods=["POST"])
def check_mcqs():
    chapter = request.json.get("chapter")
    user_answers = request.json.get("user_answers")
    mcqs = request.json.get("mcqs")
    results = []
    for i, mcq in enumerate(mcqs):
        correct = rag.generate_mcq(chapter, num_mcqs=1, num_options=4)[0]["options"].index(mcq["correct"])
        is_correct = user_answers[i] == correct
        explanation = ""
        if not is_correct:
            explanation = rag.explain_answer(chapter, mcq["question"], mcq["options"][user_answers[i]], mcq["correct"])
        results.append({
            "question": mcq["question"],
            "user_answer": mcq["options"][user_answers[i]],
            "correct_answer": mcq["correct"],
            "is_correct": is_correct,
            "explanation": explanation
        })
    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(debug=True)