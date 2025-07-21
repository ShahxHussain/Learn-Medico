from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from typing import List, Dict, Tuple
import os
import pickle

EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'

class ChapterFaissStore:
    def __init__(self, index_dir: str = 'faiss_indexes'):
        # Force CPU usage to avoid CUDA errors
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME, device='cpu')
        self.index_dir = index_dir
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
        self.indexes = {}  # unit -> (faiss index, id2chunk)

    def embed_chunks(self, chunks: List[str]) -> np.ndarray:
        return np.array(self.model.encode(chunks, show_progress_bar=False, convert_to_numpy=True))

    def store_chapter(self, unit: str, chunks: List[str]):
        embeddings = self.embed_chunks(chunks)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)
        id2chunk = {i: chunk for i, chunk in enumerate(chunks)}
        # Save index and mapping
        faiss.write_index(index, os.path.join(self.index_dir, f'{unit}.index'))
        with open(os.path.join(self.index_dir, f'{unit}_id2chunk.pkl'), 'wb') as f:
            pickle.dump(id2chunk, f)
        self.indexes[unit] = (index, id2chunk)

    def load_chapter(self, unit: str):
        index_path = os.path.join(self.index_dir, f'{unit}.index')
        id2chunk_path = os.path.join(self.index_dir, f'{unit}_id2chunk.pkl')
        if os.path.exists(index_path) and os.path.exists(id2chunk_path):
            index = faiss.read_index(index_path)
            with open(id2chunk_path, 'rb') as f:
                id2chunk = pickle.load(f)
            self.indexes[unit] = (index, id2chunk)
        else:
            raise FileNotFoundError(f'Index or mapping for unit {unit} not found.')

    def search(self, unit: str, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if unit not in self.indexes:
            self.load_chapter(unit)
        index, id2chunk = self.indexes[unit]
        query_emb = self.embed_chunks([query])
        D, I = index.search(query_emb, top_k)
        results = [(id2chunk[i], float(D[0][j])) for j, i in enumerate(I[0])]
        return results 