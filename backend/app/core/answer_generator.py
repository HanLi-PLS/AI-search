"""
Answer generation using OpenAI GPT models
Similar to answer_with_search_ensemble from original code
"""
from openai import OpenAI
from typing import List, Dict, Any, Optional, Tuple
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
        self.model = settings.ANSWER_MODEL  # Use gpt-4.1 for answer generation
        self.online_search_model = settings.ONLINE_SEARCH_MODEL  # Use o4-mini for online search
        self.temperature = settings.ANSWER_TEMPERATURE
        logger.info(f"AnswerGenerator using model: {self.model} with temperature: {self.temperature}")
        logger.info(f"AnswerGenerator using online search model: {self.online_search_model}")

    def answer_online_search(self, prompt: str) -> str:
        """
        Perform online search using OpenAI's web_search_preview tool

        Args:
            prompt: Search query/prompt

        Returns:
            Search results as text
        """
        try:
            logger.info(f"Performing online search for: {prompt[:50]}...")
            response = self.client.responses.create(
                model=self.online_search_model,
                tools=[{
                    "type": "web_search_preview",
                    "search_context_size": "high",
                }],
                input=f"{prompt}"
            )
            logger.info("Online search completed successfully")
            return response.output_text
        except Exception as e:
            logger.error(f"Error performing online search: {str(e)}")
            return f"Error performing online search: {str(e)}"

    def generate_answer(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        search_mode: str = "files_only",
        priority_order: Optional[List[str]] = None,
        max_context_length: int = 8000
    ) -> Tuple[str, Optional[str]]:
        """
        Generate a comprehensive answer based on search mode
        Similar to answer_with_search_ensemble from original code

        Args:
            query: User's question
            search_results: List of search results with content and metadata
            search_mode: "files_only", "online_only", or "both"
            priority_order: Priority order for 'both' mode, e.g., ['online_search', 'files']
            max_context_length: Maximum characters to include in context

        Returns:
            Tuple of (answer, online_search_response)
        """
        if priority_order is None:
            priority_order = ['online_search', 'files']

        online_search_response = None

        # Handle online_only mode - just return online search result directly
        if search_mode == "online_only":
            logger.info(f"Using online_only mode for query: {query[:50]}...")
            online_search_response = self.answer_online_search(query)
            # Return online search response as the answer directly (no duplicate processing)
            return online_search_response, None

        # Handle files_only mode
        if search_mode == "files_only":
            logger.info(f"Using files_only mode for query: {query[:50]}...")
            if not search_results:
                return "I couldn't find any relevant information to answer your question.", None

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

            prompt = f"""You are an expert in bioventure investing. Answer the following question: {query}

**Knowledge Base**:
1. Files:
{context}

**Response Requirements**:
Do not fabricate any information that is not in the given content.
Answer in formal written English, be objectively and factually, avoid subjective adjectives or exaggerations.
Please provide a response with a concise introductory phrase,
but avoid meaningless fillers like 'ok', 'sure' or 'certainly'. Focus on delivering a direct and informative answer.
Please bold the most important facts or conclusions in your answer to help readers quickly identify key information,
especially when the response is long.
Do not include reference filenames in the answer.
"""

            try:
                response = self.client.responses.create(
                    model=self.model,
                    temperature=self.temperature,
                    input=prompt
                )
                return response.output_text, None
            except Exception as e:
                logger.error(f"Error generating answer: {str(e)}")
                return f"I found {len(search_results)} relevant document(s), but encountered an error generating a comprehensive answer: {str(e)}", None

        # Handle both mode with priority ordering
        if search_mode == "both":
            logger.info(f"Using both mode with priority: {priority_order} for query: {query[:50]}...")

            # Get online search response if included in priority
            if 'online_search' in priority_order:
                online_search_response = self.answer_online_search(query)

            # Build context from files
            files_context = ""
            if 'files' in priority_order and search_results:
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

                files_context = "\n".join(context_parts)

            # Build knowledge base from each source
            knowledge_base = {
                'files': files_context if 'files' in priority_order else "",
                'online_search': online_search_response if 'online_search' in priority_order else ""
            }

            # Build prioritized context using the given priority order
            priority_context = []
            for idx, source in enumerate(priority_order, 1):
                heading = {
                    'files': f"{idx}. Files",
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

**Question**: {query}

**Response Requirements**:
Do not fabricate any information that is not in the given content.
Answer in formal written English, be objectively and factually, avoid subjective adjectives or exaggerations.
Please provide a response with a concise introductory phrase,
but avoid meaningless fillers like 'ok', 'sure' or 'certainly'. Focus on delivering a direct and informative answer.
Please bold the most important facts or conclusions in your answer to help readers quickly identify key information,
especially when the response is long.
Do not include reference filenames in the answer.
"""

            try:
                response = self.client.responses.create(
                    model=self.model,
                    temperature=self.temperature,
                    input=prompt
                )
                return response.output_text, online_search_response
            except Exception as e:
                logger.error(f"Error generating answer: {str(e)}")
                return f"Error generating answer: {str(e)}", online_search_response

        return "Invalid search mode specified.", None


def get_answer_generator() -> AnswerGenerator:
    """Get answer generator instance"""
    return AnswerGenerator()
