"""
Answer generation using OpenAI GPT models
Similar to answer_with_search_ensemble from original code
"""
from openai import OpenAI
from typing import List, Dict, Any
import logging

from backend.app.config import settings

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generate final answers from search results using GPT"""

    def __init__(self):
        api_key = settings.get_openai_api_key()
        # Debug logging - show first 10 and last 4 chars of API key
        if api_key:
            masked_key = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "***"
            logger.info(f"AnswerGenerator initializing with API key: {masked_key}")
        else:
            logger.warning("AnswerGenerator: No API key provided!")

        self.client = OpenAI(api_key=api_key)
        self.model = settings.VISION_MODEL  # Use o4-mini by default
        logger.info(f"AnswerGenerator using model: {self.model}")

    def generate_answer(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        max_context_length: int = 8000
    ) -> str:
        """
        Generate a comprehensive answer based on search results

        Args:
            query: User's question
            search_results: List of search results with content and metadata
            max_context_length: Maximum characters to include in context

        Returns:
            Generated answer string
        """
        if not search_results:
            return "I couldn't find any relevant information to answer your question."

        # Build context from search results
        context_parts = []
        current_length = 0

        for idx, result in enumerate(search_results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            source = metadata.get("source", "Unknown")

            # Format context chunk
            chunk = f"[Source {idx}: {source}]\n{content}\n"
            chunk_length = len(chunk)

            # Check if adding this chunk exceeds limit
            if current_length + chunk_length > max_context_length:
                break

            context_parts.append(chunk)
            current_length += chunk_length

        context = "\n".join(context_parts)

        # Create prompt similar to original answer_with_search_ensemble
        system_prompt = """You are a helpful AI assistant that answers questions based on provided context.
Your task is to:
1. Carefully read the provided context from multiple sources
2. Synthesize information to provide a comprehensive, accurate answer
3. Cite sources when mentioning specific information
4. If the context doesn't contain enough information, acknowledge this
5. Be concise but thorough

Answer in a clear, professional manner."""

        user_prompt = f"""Question: {query}

Context from search results:
{context}

Based on the above context, please provide a comprehensive answer to the question.
If you reference specific information, mention which source it came from."""

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            answer = response.choices[0].message.content
            logger.info(f"Generated answer for query: {query[:50]}...")
            return answer

        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            # Return search results summary as fallback
            return f"I found {len(search_results)} relevant document(s), but encountered an error generating a comprehensive answer: {str(e)}"


def get_answer_generator() -> AnswerGenerator:
    """Get answer generator instance"""
    return AnswerGenerator()
