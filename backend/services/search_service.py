"""
Search and RAG service for AI search
Handles vector search, BM25 retrieval, and GPT-4 answer generation
"""
import os
import gc
import pickle
from typing import List, Dict, Any, Tuple
import torch

import chromadb
from langchain.docstore.document import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from sentence_transformers import SentenceTransformer
from langchain.embeddings.base import Embeddings
from transformers import set_seed
from transformers.utils import is_bitsandbytes_available
from openai import OpenAI


class SentenceTransformerEmbeddings(Embeddings):
    """Custom embeddings using SentenceTransformer with optional INT8 quantization"""

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        batch_size: int = 8,
        max_length: int = 8192,
        use_int8: bool = False
    ):
        self.device = device
        self.batch_size = batch_size

        # Minimize CUDA fragmentation
        os.environ.setdefault(
            "PYTORCH_CUDA_ALLOC_CONF",
            "expandable_segments:True,max_split_size_mb:128"
        )
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Build kwargs
        load_kwargs = {"trust_remote_code": True}
        if device == "cuda":
            if use_int8 and is_bitsandbytes_available():
                load_kwargs["model_kwargs"] = {
                    "load_in_8bit": True,
                    "device_map": "auto",
                }
            else:
                load_kwargs["model_kwargs"] = {"torch_dtype": torch.float16}

        # Load model
        self.model = SentenceTransformer(model_name, **load_kwargs)

        # If we took the fp16 path, cast & move once
        if device == "cuda" and not (use_int8 and is_bitsandbytes_available()):
            self.model.half()
            self.model.to(device)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        vecs = self.model.encode(
            documents,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
            device=self.device,
        )
        return vecs.tolist()

    def embed_query(self, query: str) -> List[float]:
        return self.embed_documents([query])[0]


class SearchService:
    """Service for vector search and RAG"""

    def __init__(
        self,
        openai_api_key: str,
        embeddings_model_name: str = "Qwen/Qwen3-Embedding-4B",
        use_int8: bool = False
    ):
        self.openai_api_key = openai_api_key
        self.embeddings_model_name = embeddings_model_name
        self.use_int8 = use_int8
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Initialize embeddings
        set_seed(42)
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

        self.embeddings = HuggingFaceEmbeddings(
            model_name=embeddings_model_name,
            model_kwargs={'device': self.device},
            encode_kwargs={'batch_size': 8, 'normalize_embeddings': True}
        )

        self.db_jd = None
        self.bm25_retriever = None

    def create_vector_db(
        self,
        texts: List[Document],
        collection_name: str = "jarvis_docs",
        persist_directory: str = "./chroma_db_jarvis_docs",
        batch_size: int = 1000
    ):
        """Create ChromaDB vector database from documents"""
        os.makedirs(persist_directory, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=persist_directory)

        # Drop & recreate collection
        try:
            chroma_client.delete_collection(collection_name)
        except ValueError:
            pass

        self.db_jd = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            client=chroma_client,
            collection_metadata={"hnsw:space": "cosine"},
        )

        print(f"Total documents to process: {len(texts)} (batch {batch_size})")

        # Add documents in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i: i + batch_size]
            print(f"Adding docs {i}-{i + len(batch_texts) - 1}")
            self.db_jd.add_documents(batch_texts)

            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

        print("Vector database creation completed!")
        print("Final document count:", chroma_client.get_collection(collection_name).count())

    def load_vector_db(
        self,
        collection_name: str = "jarvis_docs",
        persist_directory: str = "./chroma_db_jarvis_docs"
    ):
        """Load existing ChromaDB vector database"""
        chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.db_jd = Chroma(
            client=chroma_client,
            collection_name=collection_name,
            embedding_function=self.embeddings
        )
        print(f"Loaded vector database with {chroma_client.get_collection(collection_name).count()} documents")

    def create_bm25_retriever(
        self,
        collection_name: str = "jarvis_docs",
        persist_directory: str = "./chroma_db_jarvis_docs",
        save_path: str = "all_page_contents_docs.pkl"
    ):
        """Create BM25 retriever from ChromaDB collection"""
        chroma_client = chromadb.PersistentClient(path=persist_directory)
        collection = chroma_client.get_collection(collection_name)

        # Get all page contents in batches
        all_contents = []
        offset = 0
        batch_size = 1000

        while True:
            print(f"Processing batch starting at offset {offset}...")
            batch_data = collection.get(
                limit=batch_size,
                offset=offset,
                include=["documents"]
            )

            if not batch_data['documents']:
                break

            all_contents.extend(batch_data['documents'])
            offset += batch_size
            print(f"Processed {len(all_contents)} documents so far...")

        # Save to pickle
        with open(save_path, 'wb') as f:
            pickle.dump(all_contents, f)

        # Create BM25 retriever
        all_docs = [Document(page_content=content) for content in all_contents]
        self.bm25_retriever = BM25Retriever.from_documents(all_docs)
        print(f"BM25 retriever created with {len(all_docs)} documents")

    def load_bm25_retriever(self, save_path: str = "all_page_contents_docs.pkl"):
        """Load BM25 retriever from pickle file"""
        with open(save_path, 'rb') as f:
            all_page_contents = pickle.load(f)

        all_docs = [Document(page_content=content) for content in all_page_contents]
        self.bm25_retriever = BM25Retriever.from_documents(all_docs)
        print(f"BM25 retriever loaded with {len(all_docs)} documents")

    def answer_gpt(self, prompt: str, model: str = "gpt-4.1") -> str:
        """Get answer from GPT model"""
        client = OpenAI(api_key=self.openai_api_key)
        response = client.responses.create(
            model=model,
            temperature=0,
            input=f"You are an expert in bioventure investing. Answer the following question: {prompt}"
        )
        return response.output_text

    def answer_online_search(self, prompt: str, search_model: str = "o4-mini") -> str:
        """Get answer using OpenAI with web search"""
        client = OpenAI(api_key=self.openai_api_key)
        response = client.responses.create(
            model=search_model,
            tools=[{
                "type": "web_search_preview",
                "search_context_size": "high",
            }],
            input=f"{prompt}"
        )
        return response.output_text

    def answer_with_search_ensemble(
        self,
        question: str,
        k_bm: int = 50,
        k_jd: int = 50,
        search_model: str = "gpt-4.1",
        priority_order: List[str] = ['online_search', 'jarvis_docs']
    ) -> Tuple[str, str]:
        """Answer question using ensemble retrieval (BM25 + vector) and GPT"""
        if not self.bm25_retriever or not self.db_jd:
            raise ValueError("BM25 retriever and vector DB must be initialized")

        # Retrieve documents
        self.bm25_retriever.k = k_bm
        vector_retriever = self.db_jd.as_retriever(search_kwargs={"k": k_jd})

        ensemble = EnsembleRetriever(
            retrievers=[self.bm25_retriever, vector_retriever],
            weights=[0.5, 0.5]
        )

        jarvis_docs_docs = ensemble.get_relevant_documents(question)

        # Get online search response if required
        online_search_response = ""
        if 'online_search' in priority_order:
            online_search_response = self.answer_online_search(question, search_model)

        # Build knowledge base
        knowledge_base = {
            'jarvis_docs': "\n\n".join(d.page_content for d in jarvis_docs_docs) if 'jarvis_docs' in priority_order else "",
            'online_search': online_search_response if 'online_search' in priority_order else ""
        }

        # Build prioritized context
        priority_context = []
        for idx, source in enumerate(priority_order, 1):
            heading = {
                'jarvis_docs': f"{idx}. JARVIS Docs",
                'online_search': f"{idx}. External Search"
            }[source]

            content = knowledge_base[source] or f"No {source} data available"
            priority_context.append(f"{heading}:\n{content}")

        joined_priority_context = "\n\n".join(priority_context)

        prompt = f"""
**Analysis Directive**: Answer using this priority sequence: {', '.join(priority_order).upper()}

**Knowledge Base**:
{joined_priority_context}

**Conflict Resolution Rules**:
- Follow {priority_order[0].upper()} for numerical disputes
- Resolve conceptual conflicts using {priority_order[0].upper()}
- Use most recent context when dates conflict

**Question**: {question}

**Response Requirements**:
Do not fabricate any information that is not in the given content.
Answer in formal written English, be objectively and factually, avoid subjective adjectives or exaggerations.
Please provide a response with a concise introductory phrase, but avoid meaningless fillers like 'ok', 'sure' or 'certainly'.
Focus on delivering a direct and informative answer.
Please bold the most important facts or conclusions in your answer to help readers quickly identify key information, especially when the response is long.
Do not include reference filenames in the answer.
"""

        answer = self.answer_gpt(prompt)
        return answer, online_search_response
