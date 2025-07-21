from flask import Flask, render_template_string, request, redirect, url_for, session
from faiss_store import ChapterFaissStore
from together_rag import TogetherRAG
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# Available chapters (based on your faiss_indexes)
CHAPTERS = ["Full Book", "UNIT 1"]

faiss_store = ChapterFaissStore(index_dir="../faiss_indexes")
rag = TogetherRAG(faiss_store)

TEMPLATE_INDEX = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RAG Learning System</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #f8fafc; }
    .container { max-width: 600px; margin-top: 60px; }
    .loader-overlay { display: none; position: fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(255,255,255,0.7); z-index:9999; align-items:center; justify-content:center; }
    .loader { border: 8px solid #f3f3f3; border-top: 8px solid #3498db; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; }
    @keyframes spin { 100% { transform: rotate(360deg); } }
  </style>
</head>
<body>
<div class="container shadow p-4 bg-white rounded">
  <h2 class="mb-4 text-center">RAG Learning System</h2>
  <form method="post" action="/select" onsubmit="showLoader()">
    <div class="mb-3">
      <label for="chapter" class="form-label">Select Chapter:</label>
      <select name="chapter" id="chapter" class="form-select">
        {% for ch in chapters %}
          <option value="{{ch}}">{{ch}}</option>
        {% endfor %}
      </select>
    </div>
    <button type="submit" class="btn btn-primary w-100">Go</button>
  </form>
</div>
<div class="loader-overlay" id="loader"><div class="loader"></div></div>
<script>
function showLoader() { document.getElementById('loader').style.display = 'flex'; }
</script>
</body>
</html>
'''

TEMPLATE_CHAPTER = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Chapter: {{chapter}}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>.container { max-width: 700px; margin-top: 60px; }</style>
</head>
<body>
<div class="container shadow p-4 bg-white rounded">
  <h2 class="mb-4">Chapter: {{chapter}}</h2>
  <form method="post" action="/notes" class="mb-3" onsubmit="showLoader()">
    <input type="hidden" name="chapter" value="{{chapter}}">
    <button type="submit" class="btn btn-success">Generate Notes</button>
  </form>
  <form method="post" action="/mcq" onsubmit="showLoader()">
    <input type="hidden" name="chapter" value="{{chapter}}">
    <label class="form-label">Number of MCQs:
      <input type="number" name="num_mcqs" value="3" min="1" max="100" class="form-control d-inline-block w-auto ms-2">
    </label>
    <button type="submit" class="btn btn-warning ms-2">Start MCQ Quiz</button>
  </form>
  <a href="/" class="btn btn-link mt-3">Back</a>
</div>
<div class="loader-overlay" id="loader"><div class="loader"></div></div>
<script>
function showLoader() { document.getElementById('loader').style.display = 'flex'; }
</script>
</body>
</html>
'''

TEMPLATE_NOTES = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Notes for {{chapter}}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>.container { max-width: 700px; margin-top: 60px; }</style>
</head>
<body>
<div class="container shadow p-4 bg-white rounded">
  <h2 class="mb-4">Notes for {{chapter}}</h2>
  <pre class="bg-light p-3 rounded">{{notes}}</pre>
  <a href="/chapter/{{chapter}}" class="btn btn-link mt-3">Back to Chapter</a>
</div>
</body>
</html>
'''

TEMPLATE_MCQ = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MCQ Quiz - {{chapter}}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>.container { max-width: 700px; margin-top: 60px; }</style>
</head>
<body>
<div class="container shadow p-4 bg-white rounded">
  <h2 class="mb-4">MCQ Quiz - {{chapter}}</h2>
  <form method="post" action="/mcq_submit" onsubmit="showLoader()">
    <input type="hidden" name="chapter" value="{{chapter}}">
    <input type="hidden" name="num_mcqs" value="{{mcqs|length}}">
    {% for mcq in mcqs %}
      {% set qidx = loop.index0 %}
      <div class="mb-4">
        <b>Q{{ qidx + 1 }}: {{mcq.question}}</b><br>
        {% for opt in mcq.options %}
          <div class="form-check">
            <input class="form-check-input" type="radio" name="q{{ qidx }}" value="{{ loop.index0 }}" required>
            <label class="form-check-label">{{ opt }}</label>
          </div>
        {% endfor %}
      </div>
    {% endfor %}
    <button type="submit" class="btn btn-primary">Submit Answers</button>
  </form>
  <a href="/chapter/{{chapter}}" class="btn btn-link mt-3">Back to Chapter</a>
</div>
<div class="loader-overlay" id="loader"><div class="loader"></div></div>
<script>
function showLoader() { document.getElementById('loader').style.display = 'flex'; }
</script>
</body>
</html>
'''

TEMPLATE_RESULT = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Quiz Results - {{chapter}}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>.container { max-width: 700px; margin-top: 60px; }</style>
</head>
<body>
<div class="container shadow p-4 bg-white rounded">
  <h2 class="mb-4">Quiz Results - {{chapter}}</h2>
  <p class="fs-5">Your score: <b>{{score}} / {{mcqs|length}}</b></p>
  {% for mcq in mcqs %}
    <div class="mb-4">
      <b>Q{{ loop.index }}: {{mcq.question}}</b><br>
      <b>Your answer:</b> {{user_answers[loop.index0]}}<br>
      <b>Correct answer:</b> {{mcq.correct}}<br>
      {% if explanations[loop.index0] %}
        <div class="alert alert-info mt-2"><b>Explanation:</b> {{explanations[loop.index0]}}</div>
      {% endif %}
    </div>
  {% endfor %}
  <a href="/chapter/{{chapter}}" class="btn btn-link mt-3">Back to Chapter</a>
</div>
</body>
</html>
'''

@app.route("/", methods=["GET"])
def index():
    return render_template_string(TEMPLATE_INDEX, chapters=CHAPTERS)

@app.route("/select", methods=["POST"])
def select():
    chapter = request.form["chapter"]
    session["chapter"] = chapter
    return redirect(url_for("chapter_page", chapter=chapter))

@app.route("/chapter/<chapter>", methods=["GET"])
def chapter_page(chapter):
    return render_template_string(TEMPLATE_CHAPTER, chapter=chapter)

@app.route("/notes", methods=["POST"])
def notes():
    chapter = request.form["chapter"]
    notes = rag.generate_chapter_notes(chapter)
    return render_template_string(TEMPLATE_NOTES, chapter=chapter, notes=notes)

@app.route("/mcq", methods=["POST"])
def mcq():
    chapter = request.form["chapter"]
    num_mcqs = int(request.form.get("num_mcqs", 3))
    mcqs = rag.generate_mcq(chapter, num_mcqs=num_mcqs, num_options=4)
    session["mcqs"] = mcqs
    session["chapter"] = chapter
    return render_template_string(TEMPLATE_MCQ, chapter=chapter, mcqs=mcqs)

@app.route("/mcq_submit", methods=["POST"])
def mcq_submit():
    chapter = session.get("chapter")
    mcqs = session.get("mcqs")
    num_mcqs = int(request.form.get("num_mcqs", len(mcqs)))
    user_answers = []
    explanations = []
    score = 0
    for i in range(num_mcqs):
        ans_idx = int(request.form.get(f"q{i}"))
        user_ans = mcqs[i]["options"][ans_idx]
        user_answers.append(user_ans)
        if user_ans == mcqs[i]["correct"]:
            explanations.append("")
            score += 1
        else:
            explain = rag.explain_answer(chapter, mcqs[i]["question"], user_ans, mcqs[i]["correct"])
            explanations.append(explain)
    return render_template_string(TEMPLATE_RESULT, chapter=chapter, mcqs=mcqs, user_answers=user_answers, explanations=explanations, score=score)

if __name__ == "__main__":
    app.run(debug=True) 