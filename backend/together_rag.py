import os
from together import Together
from backend.faiss_store import ChapterFaissStore
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Load .env for Together API key
env_loaded = load_dotenv()

class TogetherRAG:
    def __init__(self, faiss_store: ChapterFaissStore):
        api_key = os.getenv("TOGETHER_API")
        if not api_key:
            raise ValueError("TOGETHER_API key not found in environment variables.")
        self.client = Together(api_key=api_key)
        self.faiss_store = faiss_store
        self.model = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

    def retrieve_context(self, chapter: str, query: str, top_k: int = 5) -> List[str]:
        results = self.faiss_store.search(chapter, query, top_k)
        return [chunk for chunk, _ in results]

    def generate_chapter_notes(self, chapter: str) -> str:
        context = "\n".join(self.retrieve_context(chapter, "summary"))
        prompt = f"Summarize the following chapter for a student preparing for exams.\n{context}"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def extract_facts_for_mcq(self, context_chunks: List[str], num_options: int = 4) -> List[str]:
        # Naive approach: split context into sentences and pick unique ones as options
        import re
        sentences = []
        for chunk in context_chunks:
            sentences.extend(re.split(r'(?<=[.!?]) +', chunk))
        # Remove duplicates and empty
        unique_sentences = list({s.strip() for s in sentences if len(s.strip()) > 20})
        return unique_sentences[:num_options]

    def generate_mcq(self, chapter: str, num_mcqs: int = 5, num_options: int = 4) -> List[Dict]:
        context_chunks = self.retrieve_context(chapter, "mcq", top_k=10)
        options_pool = self.extract_facts_for_mcq(context_chunks, num_options * num_mcqs)
        mcqs = []
        for i in range(num_mcqs):
            opts = options_pool[i*num_options:(i+1)*num_options]
            if len(opts) < num_options:
                break
            correct = opts[0]
            prompt = (
                f"Create a multiple-choice question for students based on the following facts. "
                f"Use only the provided facts as options.\n"
                f"Options:\n" + "\n".join([f"- {o}" for o in opts]) + "\n"
                f"Mark the correct answer and write a question that fits these options."
            )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content.strip()
            mcqs.append({
                "question": content,
                "options": opts,
                "correct": correct
            })
        return mcqs

    def explain_answer(self, chapter: str, question: str, user_answer: str, correct_answer: str) -> str:
        context = "\n".join(self.retrieve_context(chapter, question, top_k=5))
        prompt = (
            f"Given the following question and context:\n{question}\nContext:\n{context}\n"
            f"The user's answer was: {user_answer}\nThe correct answer is: {correct_answer}.\n"
            "Explain why the user's answer is incorrect and provide the correct reasoning."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip() 