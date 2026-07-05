import os
# Force offline mode for Hugging Face to prevent online update checks and hangs
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import time
import uuid
import threading
import chromadb
from sentence_transformers import SentenceTransformer

class RAGEngine:
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = RAGEngine()
        return cls._instance

    def __init__(self):
        self.interaction_count = 0
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_data")
        os.makedirs(self.db_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(
            name="jk_memory",
            metadata={"hnsw:space": "cosine"}
        )
        
        print("[Memory] Loading SentenceTransformer 'all-MiniLM-L6-v2'...")
        # Use local_files_only=True so it works entirely offline
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu', local_files_only=True)
        print("[Memory] Engine ready.")
        
        self._check_and_seed()

    def _check_and_seed(self):
        if self.collection.count() == 0:
            print("[Memory] Empty database detected. Injecting seed data...")
            seeds = [
                "User is named Madan",
                "User is from Kurnool, Andhra Pradesh, India",
                "User speaks Telugu and English",
                "User is preparing for placement interviews",
                "User wants to learn English teaching skills",
                "User wants to learn programming languages",
                "User uses JK 80-90% on mobile",
                "User is building JK as a career project"
            ]
            self.add_facts_async("personal_facts", seeds)

    def _embed(self, text: str) -> list:
        return self.encoder.encode(text).tolist()

    def add_memory_sync(self, category: str, text: str, metadata: dict = None):
        try:
            vector = self._embed(text)
            doc_id = str(uuid.uuid4())
            meta = {"category": category, "timestamp": time.time()}
            if metadata:
                meta.update(metadata)
                
            self.collection.add(
                embeddings=[vector],
                documents=[text],
                metadatas=[meta],
                ids=[doc_id]
            )
        except Exception as e:
            print(f"[Memory] Failed to add memory: {e}")

    def add_memory(self, category: str, text: str, metadata: dict = None):
        """Asynchronously add a memory without blocking."""
        t = threading.Thread(target=self.add_memory_sync, args=(category, text, metadata))
        t.daemon = True
        t.start()

    def add_facts_async(self, category: str, facts: list):
        if not facts: return
        def _add():
            for f in facts:
                self.add_memory_sync(category, f)
        t = threading.Thread(target=_add)
        t.daemon = True
        t.start()

    def save_interaction(self, user_text: str, jk_text: str):
        text = f"User said: {user_text} | JK replied: {jk_text}"
        self.add_memory("conversations", text)

    def _run_consolidation(self):
        try:
            res = self.collection.get(where={"category": "conversations"})
            ids = res.get("ids", [])
            docs = res.get("documents", [])
            
            if len(docs) < 5:
                return
                
            # To avoid token limits, take max 50 recent interactions for consolidation
            if len(docs) > 50:
                docs = docs[-50:]
                ids_to_delete = ids[-50:]
            else:
                ids_to_delete = ids
                
            log_text = "\n".join(docs)
            prompt = f"Analyze these raw chat logs between a user and an AI named JK.\nExtract only high-value, persistent facts about the user (preferences, relationships, learning struggles, personal details). Format as concise bullet points starting with '- User'. Ignore small talk, greetings, and ephemeral commands.\n\nLogs:\n{log_text}\n\nFacts:"
            
            from engine.ai.hybrid_llm import HybridLLM
            llm_res = HybridLLM.chat_completion([{"role": "user", "content": prompt}], max_tokens=300)
            facts_text = llm_res.choices[0].message.content.strip()
            
            facts = []
            for line in facts_text.split('\n'):
                line = line.strip()
                if line.startswith('- User') or line.startswith('* User'):
                    facts.append(line.lstrip('-* '))
            
            if facts:
                print(f"[Memory] Consolidator extracted {len(facts)} high-value facts. Synthesizing Knowledge Graph.")
                self.add_facts_async("personal_facts", facts)
                
            # Delete the raw logs that were processed
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
        except Exception as e:
            print(f"[Memory] Consolidation failed: {e}")

    def search_memory(self, query: str, top_k: int = 3, max_time: float = 0.5) -> list:
        """Fast search with a timeout."""
        start_time = time.time()
        try:
            if time.time() - start_time > max_time: return []
            vector = self._embed(query)
            if time.time() - start_time > max_time: return []
            
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=top_k
            )
            
            if results and results['documents'] and len(results['documents'][0]) > 0:
                return results['documents'][0]
        except Exception as e:
            print(f"[Memory] Search error: {e}")
            
        return []
        
    def forget_memory(self, topic: str) -> str:
        try:
            vector = self._embed(topic)
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=1
            )
            if results and results['ids'] and len(results['ids'][0]) > 0:
                doc_id = results['ids'][0][0]
                doc_text = results['documents'][0][0]
                self.collection.delete(ids=[doc_id])
                return f"Forgot: {doc_text}"
        except Exception as e:
            pass
        return "Could not find related memory to forget."
