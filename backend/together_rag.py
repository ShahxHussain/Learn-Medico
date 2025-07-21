import os
import re
from together import Together
from faiss_store import ChapterFaissStore
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
        sentences = []
        for chunk in context_chunks:
            sentences.extend(re.split(r'(?<=[.!?]) +', chunk))
        # Remove duplicates and empty
        unique_sentences = list({s.strip() for s in sentences if len(s.strip()) > 20})
        return unique_sentences[:num_options]

    def generate_mcq(self, chapter: str, num_mcqs: int = 5, num_options: int = 4) -> List[Dict]:
        context_chunks = self.retrieve_context(chapter, "mcq", top_k=3)
        context = "\n".join(context_chunks)
        if len(context) > 2000:
            context = context[:2000]
        mcqs = []
        for i in range(num_mcqs):
            prompt = (
                f"Based only on the following context, generate one multiple-choice question for a student. "
                f"Provide 4 options, mark the correct answer, and give a brief explanation. "
                f"Do not use any information not present in the context.\n\n"
                f"Context:\n{context}\n\n"
                "Format your response as:\n"
                "Question: ...\nA) ...\nB) ...\nC) ...\nD) ...\nAnswer: <A/B/C/D>\nExplanation: ..."
            )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512
            )
            content = response.choices[0].message.content.strip()
            # Parse the LLM response
            q_match = re.search(r"Question:\s*(.*)", content)
            opts = re.findall(r"([A-D])\)\s*(.*)", content)
            ans_match = re.search(r"Answer:\s*([A-D])", content)
            exp_match = re.search(r"Explanation:\s*(.*)", content)
            if not (q_match and len(opts) == 4 and ans_match):
                continue  # skip malformed MCQ
            question = q_match.group(1).strip()
            options = [opt[1].strip() for opt in opts]
            correct_letter = ans_match.group(1)
            correct_idx = ord(correct_letter) - ord('A')
            correct = options[correct_idx]
            explanation = exp_match.group(1).strip() if exp_match else ""
            mcqs.append({
                "question": question,
                "options": options,
                "correct": correct,
                "correct_letter": correct_letter,
                "explanation": explanation
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

if __name__ == "__main__":
    import sys
    print("=== TogetherRAG CLI Test ===")
    faiss_store = ChapterFaissStore(index_dir="../faiss_indexes")
    rag = TogetherRAG(faiss_store)

    chapters = ["Full Book", "UNIT 1"]
    print("Available chapters:")
    for idx, ch in enumerate(chapters, 1):
        print(f"  {idx}. {ch}")
    ch_idx = int(input("Select chapter (number): ")) - 1
    chapter = chapters[ch_idx]

    print("\n1. Generate Chapter Notes\n2. Generate MCQs\n3. Exit")
    choice = input("Choose an option: ")

    if choice == "1":
        print("\nGenerating notes...")
        notes = rag.generate_chapter_notes(chapter)
        print("\n--- Chapter Notes ---\n", notes)
    elif choice == "2":
        num_mcqs = int(input("How many MCQs? (default 3): ") or "3")
        mcqs = rag.generate_mcq(chapter, num_mcqs=num_mcqs, num_options=4)
        score = 0
        for i, mcq in enumerate(mcqs, 1):
            print(f"\nQ{i}: {mcq['question']}")
            for j, opt in enumerate(mcq['options'], 1):
                print(f"  {j}. {opt}")
            ans = int(input("Your answer (number): ")) - 1
            user_ans = mcq['options'][ans]
            if user_ans == mcq['correct']:
                print("Correct!\n")
                score += 1
            else:
                print(f"Incorrect. Correct answer: {mcq['correct']}")
                explain = rag.explain_answer(chapter, mcq['question'], user_ans, mcq['correct'])
                print("Explanation:", explain)
        print(f"\nYour score: {score}/{len(mcqs)}")
    else:
        print("Exiting.") 