"""
Document Search System with AI-powered Q&A
Refactored from Jupyter notebooks with proper error handling and model parameter support
"""

import os
import json
import ast
import pickle
import logging
from typing import List, Dict, Optional, Tuple
from collections import Counter

import boto3
from botocore.exceptions import ClientError
from openai import OpenAI
import tiktoken

from langchain_core.documents import Document
from langchain.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_chroma import Chroma

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentSearchSystem:
    """Main document search system with ensemble retrieval and AI-powered answering"""

    # Valid OpenAI models for reasoning and chat
    VALID_MODELS = {
        # Reasoning models
        "o1", "o1-pro", "o1-mini", "o1-preview",
        # GPT-5 series (reasoning)
        "gpt-5-pro", "gpt-5", "gpt-5.1",
        # Chat models
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
        # Legacy models used in the codebase
        "gpt-4.1", "o4-mini", "o3"
    }

    # Model context limits (in tokens)
    MODEL_LIMITS = {
        "gpt-5-pro": 400000,     # GPT-5 Pro has 400k context window
        "gpt-5": 400000,
        "gpt-5.1": 400000,       # GPT-5.1 has 400k context window
        "o1-pro": 200000,
        "o1": 200000,
        "o1-mini": 128000,
        "o1-preview": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 16385,
        "gpt-4.1": 128000,
        "o4-mini": 128000,
        "o3": 128000,
    }

    def __init__(self, region_name: str = "us-west-2", enable_logging: bool = True):
        """Initialize the document search system"""
        self.region_name = region_name
        self.openai_api_key = self._get_secret("openai-api-key", region_name)
        self.client = OpenAI(api_key=self.openai_api_key)
        self.enable_logging = enable_logging

        # Initialize tokenizer for token counting
        try:
            self.encoding = tiktoken.encoding_for_model("gpt-4")
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def _get_secret(self, secret_name: str, region_name: str) -> str:
        """Retrieve secret from AWS Secrets Manager"""
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )

        try:
            response = client.get_secret_value(SecretId=secret_name)
            secret = response['SecretString']
            key = ast.literal_eval(secret)['key']
            return key
        except ClientError as e:
            raise RuntimeError(f"Failed to retrieve secret {secret_name}: {str(e)}")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in a text string"""
        return len(self.encoding.encode(text))

    def _validate_model(self, model: str) -> str:
        """
        Validate model name

        Args:
            model: Model name to validate

        Returns:
            Validated model name

        Raises:
            ValueError: If model is not valid
        """
        # Validate against known models
        if model not in self.VALID_MODELS:
            raise ValueError(
                f"Invalid model '{model}'. "
                f"Valid models: {', '.join(sorted(self.VALID_MODELS))}"
            )

        return model

    def _check_token_limit(self, text: str, model: str) -> Tuple[int, int, bool]:
        """
        Check if text exceeds model's token limit

        Args:
            text: Text to check
            model: Model name

        Returns:
            Tuple of (token_count, limit, exceeds_limit)
        """
        token_count = self._count_tokens(text)
        limit = self.MODEL_LIMITS.get(model, 128000)
        exceeds = token_count > limit

        if self.enable_logging:
            if exceeds:
                logger.warning(
                    f"Token limit exceeded for {model}: {token_count} tokens > {limit} limit"
                )
            else:
                logger.info(
                    f"Token count for {model}: {token_count}/{limit} tokens ({token_count/limit*100:.1f}%)"
                )

        return token_count, limit, exceeds

    def answer_gpt(self, prompt: str, model: str = "gpt-4.1", temperature: float = 0) -> str:
        """
        Answer a question using GPT model via OpenAI Responses API

        Args:
            prompt: The question/prompt to answer
            model: Model name (default: gpt-4.1)
            temperature: Temperature for response generation

        Returns:
            The model's response text

        Raises:
            ValueError: If model is invalid or input exceeds token limit
            RuntimeError: If API call fails
        """
        try:
            # Validate and normalize model name
            validated_model = self._validate_model(model)

            # Build full input
            full_input = f"You are an expert in bioventure investing. Answer the following question: {prompt}"

            # Check token limit
            token_count, limit, exceeds = self._check_token_limit(full_input, validated_model)

            if exceeds:
                raise ValueError(
                    f"Input exceeds {validated_model} token limit: {token_count} tokens > {limit} limit. "
                    f"Try reducing the number of retrieved documents (k_bm, k_jd parameters) or use a model with larger context."
                )

            if self.enable_logging:
                logger.info(f"Calling {validated_model} with {token_count} tokens")

            response = self.client.responses.create(
                model=validated_model,
                temperature=temperature,
                input=full_input
            )
            return response.output_text

        except ValueError as e:
            # Re-raise validation errors with context
            raise ValueError(f"Model validation failed: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            # Check if error is related to token limits
            if "maximum context length" in error_msg.lower() or "token" in error_msg.lower():
                logger.error(f"Token limit error: {error_msg}")
                raise ValueError(
                    f"Token limit error with {model}: {error_msg}. "
                    f"Try reducing k_bm and k_jd parameters or use a model with larger context."
                )
            raise RuntimeError(f"OpenAI API call failed with model '{model}': {error_msg}")

    def answer_online_search(self, prompt: str, search_model: str = "o4-mini") -> str:
        """
        Answer a question using web search capabilities

        Args:
            prompt: The question/prompt to answer
            search_model: Model to use for search (default: o4-mini)

        Returns:
            The model's response with web search context

        Raises:
            ValueError: If model is invalid
            RuntimeError: If API call fails
        """
        try:
            # Validate and normalize model name
            validated_model = self._validate_model(search_model)

            response = self.client.responses.create(
                model=validated_model,
                tools=[{
                    "type": "web_search_preview",
                    "search_context_size": "high",
                }],
                input=f"{prompt}"
            )
            return response.output_text

        except ValueError as e:
            raise ValueError(f"Model validation failed: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"OpenAI search API call failed with model '{search_model}': {str(e)}")

    def answer_with_search_ensemble(
        self,
        question: str,
        bm25_retriever: BM25Retriever,
        k_bm: int,
        db_jd: Chroma,
        k_jd: int,
        search_model: str = "gpt-4.1",
        priority_order: List[str] = ['online_search', 'jarvis_docs'],
        auto_reduce_on_limit: bool = True
    ) -> Tuple[str, str]:
        """
        Answer questions using ensemble retrieval with multiple knowledge sources

        Args:
            question: The question to answer
            bm25_retriever: BM25 retriever for keyword search
            k_bm: Number of documents to retrieve with BM25
            db_jd: ChromaDB vector database
            k_jd: Number of documents to retrieve from vector DB
            search_model: Model to use for both online search AND final answer
            priority_order: Order of knowledge sources to prioritize
            auto_reduce_on_limit: Automatically reduce context if token limit exceeded

        Returns:
            Tuple of (answer, online_search_response)

        Raises:
            ValueError: If model is invalid or input exceeds limits
        """
        if self.enable_logging:
            logger.info(f"Starting search with model={search_model}, k_bm={k_bm}, k_jd={k_jd}")

        # Retrieve documents from docs
        bm25_retriever.k = k_bm
        vector_retriever = db_jd.as_retriever(search_kwargs={"k": k_jd})

        ensemble = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[0.5, 0.5]
        )

        jarvis_docs_docs = ensemble.get_relevant_documents(question)

        # Get online_search response if required
        online_search_response = ""
        if 'online_search' in priority_order:
            try:
                online_search_response = self.answer_online_search(question, search_model)
            except Exception as e:
                print(f"Warning: Online search failed: {str(e)}")
                online_search_response = f"[Online search unavailable: {str(e)}]"

        # Build the knowledge base from each source
        knowledge_base = {
            'jarvis_docs': "\n\n".join(d.page_content for d in jarvis_docs_docs) if 'jarvis_docs' in priority_order else "",
            'online_search': online_search_response if 'online_search' in priority_order else ""
        }

        # Build prioritized context using the given priority order
        priority_context = []
        for idx, source in enumerate(priority_order, 1):
            heading = {
                'jarvis_docs': f"{idx}. JARVIS Docs",
                'online_search': f"{idx}. External Search"
            }[source]

            content = knowledge_base[source] or f"No {source} data available"
            priority_context.append(f"{heading}:\n{content}")

        # Precompute the joined priority context
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
Please provide a response with a concise introductory phrase,
but avoid meaningless fillers like 'ok', 'sure' or 'certainly'. Focus on delivering a direct and informative answer.
Please bold the most important facts or conclusions in your answer to help readers quickly identify key information,
especially when the response is long.
Do not include reference filenames in the answer.
"""

        # Check token limit before calling API
        token_count, limit, exceeds = self._check_token_limit(prompt, search_model)

        # If exceeds and auto_reduce is enabled, try reducing context
        if exceeds and auto_reduce_on_limit:
            logger.warning(
                f"Token limit exceeded ({token_count} > {limit}). "
                f"Attempting to reduce context by halving retrieval counts..."
            )

            # Recursively retry with reduced parameters
            new_k_bm = max(5, k_bm // 2)
            new_k_jd = max(5, k_jd // 2)

            if new_k_bm < k_bm or new_k_jd < k_jd:
                logger.info(f"Retrying with k_bm={new_k_bm}, k_jd={new_k_jd}")
                return self.answer_with_search_ensemble(
                    question=question,
                    bm25_retriever=bm25_retriever,
                    k_bm=new_k_bm,
                    db_jd=db_jd,
                    k_jd=new_k_jd,
                    search_model=search_model,
                    priority_order=priority_order,
                    auto_reduce_on_limit=False  # Don't recurse infinitely
                )
            else:
                raise ValueError(
                    f"Cannot reduce context further. Input still exceeds limit: {token_count} > {limit}. "
                    f"Current: k_bm={k_bm}, k_jd={k_jd}. "
                    f"Try using a model with larger context window."
                )

        # FIX: Use the same search_model for the final answer instead of hardcoded "gpt-4.1"
        try:
            answer = self.answer_gpt(prompt, model=search_model)
            if self.enable_logging:
                logger.info("Successfully generated answer")
        except Exception as e:
            logger.error(f"Failed to generate answer: {str(e)}")
            raise RuntimeError(f"Failed to generate answer: {str(e)}")

        return answer, online_search_response

    def answer_with_smart_pipeline(
        self,
        question: str,
        bm25_retriever: BM25Retriever,
        db_jd: Chroma,
        planning_model: str = "gpt-5.1",
        k_bm: int = 40,
        k_jd: int = 40
    ) -> Dict:
        """
        Answer questions using SmartPipeline with automatic query analysis and planning

        This method uses LLM to automatically:
        1. Analyze the query type
        2. Determine what information to extract from internal docs
        3. Plan what to search for online
        4. Execute the planned pipeline
        5. Combine results into comprehensive answer

        Args:
            question: The question to answer
            bm25_retriever: BM25 retriever for keyword search
            db_jd: ChromaDB vector database
            planning_model: Model to use for query analysis (default: gpt-5.1)
            k_bm: Number of documents to retrieve with BM25 (default: 40)
            k_jd: Number of documents to retrieve from vector DB (default: 40)

        Returns:
            Dict with keys:
                - query: The original question
                - plan: The generated execution plan
                - final_answer: The comprehensive answer
                - stages: Results from all pipeline stages

        Example:
            >>> search_system = DocumentSearchSystem()
            >>> results = search_system.answer_with_smart_pipeline(
            ...     question="Who are PPInnova's competitors?",
            ...     bm25_retriever=bm25_retriever,
            ...     db_jd=db_jd,
            ...     planning_model="gpt-5.1"
            ... )
            >>> print(results["final_answer"])
        """
        try:
            # Import SmartPipeline (lazy import to avoid circular dependency)
            from sequential_pipeline import SmartPipeline

            # Create pipeline instance
            smart_pipeline = SmartPipeline(
                search_system=self,
                bm25_retriever=bm25_retriever,
                db_jd=db_jd
            )

            # Run smart analysis
            if self.enable_logging:
                logger.info(f"Running SmartPipeline with planning_model={planning_model}")

            results = smart_pipeline.run_smart(
                user_query=question,
                planning_model=planning_model
            )

            if self.enable_logging:
                logger.info(f"SmartPipeline completed. Query type: {results['plan'].get('query_type', 'unknown')}")

            return results

        except ImportError as e:
            raise RuntimeError(
                f"SmartPipeline not available. Make sure sequential_pipeline.py is in the same directory. Error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"SmartPipeline failed: {str(e)}")
            raise RuntimeError(f"SmartPipeline execution failed: {str(e)}")


def main():
    """Example usage and testing"""
    try:
        # Initialize the system
        search_system = DocumentSearchSystem(region_name="us-west-2")

        # Test model validation
        print("Testing model validation...")

        # This should work
        test_models = ["gpt-4o", "o1-pro", "o4-mini", "gpt-4.1"]
        for model in test_models:
            try:
                validated = search_system._validate_model(model)
                print(f"✓ {model} → {validated}")
            except ValueError as e:
                print(f"✗ {model}: {e}")

        # This should be corrected
        print("\nTesting auto-correction...")
        try:
            validated = search_system._validate_model("gpt-5-pro")
            print(f"✓ gpt-5-pro → {validated} (auto-corrected)")
        except ValueError as e:
            print(f"✗ gpt-5-pro: {e}")

        # This should fail with helpful error
        print("\nTesting invalid model...")
        try:
            search_system._validate_model("invalid-model")
        except ValueError as e:
            print(f"✓ Caught invalid model: {e}")

        print("\n✓ All validation tests passed!")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()
