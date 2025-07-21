import streamlit as st
from faiss_store import ChapterFaissStore
from together_rag import TogetherRAG

# Set up Streamlit page config
st.set_page_config(page_title="RAG Learning System", layout="centered")
st.title("📚 RAG Learning System")

# Initialize FAISS and RAG
faiss_store = ChapterFaissStore(index_dir="../faiss_indexes")
rag = TogetherRAG(faiss_store)

CHAPTERS = ["Full Book", "UNIT 1"]

# Sidebar for chapter selection
st.sidebar.header("Select Chapter")
chapter = st.sidebar.selectbox("Chapter", CHAPTERS)

st.markdown("---")

# Notes generation
if st.button("Generate Chapter Notes", type="primary"):
    with st.spinner("Generating notes..."):
        try:
            notes = rag.generate_chapter_notes(chapter)
            st.subheader(f"Notes for {chapter}")
            st.code(notes)
        except Exception as e:
            st.error(f"Error generating notes: {e}")

st.markdown("---")

# MCQ Quiz
st.subheader("MCQ Quiz")
num_mcqs = st.number_input("Number of MCQs", min_value=1, max_value=100, value=3, step=1)

if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
if 'mcqs' not in st.session_state:
    st.session_state.mcqs = []
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = []
if 'quiz_submitted' not in st.session_state:
    st.session_state.quiz_submitted = False

if st.button("Start MCQ Quiz", type="secondary") or st.session_state.quiz_started:
    if not st.session_state.quiz_started:
        with st.spinner("Generating MCQs..."):
            try:
                mcqs = rag.generate_mcq(chapter, num_mcqs=int(num_mcqs), num_options=4)
                if not mcqs:
                    st.warning("Not enough content to generate MCQs. Try fewer questions or another chapter.")
                    st.session_state.quiz_started = False
                else:
                    st.session_state.mcqs = mcqs
                    st.session_state.user_answers = [None] * len(mcqs)
                    st.session_state.quiz_started = True
                    st.session_state.quiz_submitted = False
            except Exception as e:
                st.error(f"Error generating MCQs: {e}")
                st.session_state.quiz_started = False
    if st.session_state.quiz_started:
        with st.form("mcq_quiz_form"):
            for i, mcq in enumerate(st.session_state.mcqs):
                st.markdown(f"**Q{i+1}: {mcq['question']}**")
                st.session_state.user_answers[i] = st.radio(
                    f"Select your answer for Q{i+1}",
                    mcq['options'],
                    key=f"q{i}",
                    index=st.session_state.user_answers[i] if st.session_state.user_answers[i] is not None else 0
                )
            submitted = st.form_submit_button("Submit Answers")
            if submitted:
                st.session_state.quiz_submitted = True
                st.session_state.quiz_started = False

if st.session_state.quiz_submitted:
    score = 0
    explanations = []
    incorrect_indices = []
    for i, mcq in enumerate(st.session_state.mcqs):
        if st.session_state.user_answers[i] == mcq['correct']:
            score += 1
            explanations.append("")
        else:
            incorrect_indices.append(i)
            with st.spinner(f"Explaining Q{i+1}..."):
                explain = rag.explain_answer(chapter, mcq['question'], st.session_state.user_answers[i], mcq['correct'])
                explanations.append(explain)
    st.success(f"Your score: {score} / {len(st.session_state.mcqs)}")
    for i, mcq in enumerate(st.session_state.mcqs):
        st.markdown(f"**Q{i+1}: {mcq['question']}**")
        st.markdown(f"- Your answer: {st.session_state.user_answers[i]}")
        st.markdown(f"- Correct answer: {mcq['correct']}")
        if i in incorrect_indices:
            st.info(f"Explanation: {explanations[i]}")
    if st.button("Start New Quiz"):
        st.session_state.quiz_started = False
        st.session_state.mcqs = []
        st.session_state.user_answers = []
        st.session_state.quiz_submitted = False 