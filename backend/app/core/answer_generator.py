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

    def classify_query(self, query: str) -> Tuple[str, str]:
        """
        Automatically classify the query to determine the best search mode

        Args:
            query: User's question

        Returns:
            Tuple of (selected_mode, reasoning)
        """
        try:
            logger.info(f"Classifying query: {query[:50]}...")

            classification_prompt = f"""You are an intelligent query router for a hybrid search system. Analyze the following user query and determine the best search strategy.

**User Query**: "{query}"

**Available Search Modes**:
1. **files_only**: Search only in the user's uploaded documents
   - Use when: Query is clearly about specific documents the user has uploaded, asking about data in their files, mentions "my files", "my documents", "uploaded", etc.
   - Examples: "What's in my documents?", "Summarize the uploaded files", "What data do I have?"

2. **online_only**: Search only using online/web search
   - Use when: Query requires current information, general knowledge, latest news, industry trends, or information that wouldn't be in personal documents
   - Examples: "What's the latest news about X?", "Current market trends", "Who is the CEO of Y?"

3. **both**: Search both files and online in parallel, then synthesize
   - Use when: Query needs information from both sources but they can be processed independently
   - Examples: "What does my document say and what's the current status?", "Compare my data with industry standards"

4. **sequential_analysis**: Extract from files first, then search online using extracted info
   - Use when: Query requires extracting specific information from files first, then using that to search for comparative/competitive data online
   - Examples: "What's our drug efficacy and how does it compare to competitors?", "Extract our metrics and benchmark against industry", "Get our performance data and compare with others"

**Instructions**:
Analyze the query carefully and select the most appropriate mode. Consider:
- Does the query mention personal documents/files? (suggests files_only or sequential)
- Does it require current/external information? (suggests online_only or both/sequential)
- Does it need extraction followed by comparison? (suggests sequential_analysis)
- Can both sources be processed in parallel? (suggests both)

**Response Format** (you must respond in exactly this format):
MODE: [files_only|online_only|both|sequential_analysis]
REASONING: [Brief explanation in 1-2 sentences why this mode was chosen]

Example responses:
MODE: sequential_analysis
REASONING: The query asks to extract drug efficacy from the user's files and then compare with competitors, requiring sequential processing where file data informs the online search.

MODE: online_only
REASONING: The query asks for current market trends which requires up-to-date online information not available in personal documents.

Now classify the user's query."""

            response = self.client.responses.create(
                model="gpt-5-nano",  # Use fast, efficient model for classification
                input=classification_prompt
            )

            classification_text = response.output_text
            logger.info(f"Classification response: {classification_text[:200]}...")

            # Parse the response to extract mode and reasoning
            mode = "files_only"  # Default fallback
            reasoning = "Unable to classify query, defaulting to files_only mode."

            for line in classification_text.split('\n'):
                line = line.strip()
                if line.startswith("MODE:"):
                    mode_text = line.replace("MODE:", "").strip().lower()
                    # Extract just the mode name (in case there's extra text)
                    if "files_only" in mode_text:
                        mode = "files_only"
                    elif "online_only" in mode_text:
                        mode = "online_only"
                    elif "sequential_analysis" in mode_text:
                        mode = "sequential_analysis"
                    elif "both" in mode_text:
                        mode = "both"
                elif line.startswith("REASONING:"):
                    reasoning = line.replace("REASONING:", "").strip()

            logger.info(f"Query classified as: {mode}")
            logger.info(f"Reasoning: {reasoning}")

            return mode, reasoning

        except Exception as e:
            logger.error(f"Error classifying query: {str(e)}")
            return "files_only", f"Error during classification, defaulting to files_only mode: {str(e)}"

    def answer_online_search(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Perform online search using OpenAI's web_search_preview tool

        Args:
            prompt: Search query/prompt
            model: Optional model to use (defaults to self.online_search_model)

        Returns:
            Search results as text
        """
        try:
            search_model = model or self.online_search_model
            logger.info(f"Performing online search with model {search_model} for: {prompt[:50]}...")
            response = self.client.responses.create(
                model=search_model,
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

    def format_conversation_history(self, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
        """
        Format conversation history for inclusion in prompts

        Args:
            conversation_history: List of previous conversation turns

        Returns:
            Formatted conversation history string
        """
        if not conversation_history or len(conversation_history) == 0:
            return ""

        formatted = "\n**Previous Conversation**:\n"
        for i, turn in enumerate(conversation_history[-5:], 1):  # Only use last 5 turns to avoid token limits
            formatted += f"\nTurn {i}:\n"
            formatted += f"User: {turn.get('query', '')}\n"
            formatted += f"Assistant: {turn.get('answer', '')[:500]}...\n"  # Truncate long answers

        formatted += "\n**Current Question** (use the context above to understand references like 'it', 'that', 'them'):\n"
        return formatted

    def generate_answer(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        search_mode: str = "files_only",
        reasoning_mode: str = "non_reasoning",
        priority_order: Optional[List[str]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        max_context_length: int = 8000
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Generate a comprehensive answer based on search mode
        Similar to answer_with_search_ensemble from original code

        Args:
            query: User's question
            search_results: List of search results with content and metadata
            search_mode: "files_only", "online_only", "both", or "sequential_analysis"
            reasoning_mode: "non_reasoning" (gpt-4.1), "reasoning" (o4-mini), or "deep_research" (o3-deep-research)
            priority_order: Priority order for 'both' mode, e.g., ['online_search', 'files']
            conversation_history: Previous conversation turns for context
            max_context_length: Maximum characters to include in context

        Returns:
            Tuple of (answer, online_search_response, extracted_info)
        """
        if priority_order is None:
            priority_order = ['online_search', 'files']

        # Select model based on reasoning mode
        if reasoning_mode == "reasoning":
            search_model = "o4-mini"
        elif reasoning_mode == "deep_research":
            search_model = "o3-deep-research"
        else:  # non_reasoning
            search_model = "gpt-4.1"

        logger.info(f"Using reasoning mode '{reasoning_mode}' with model '{search_model}'")

        # Format conversation history if provided
        conversation_context = self.format_conversation_history(conversation_history)

        online_search_response = None

        # Handle online_only mode - just return online search result directly
        if search_mode == "online_only":
            logger.info(f"Using online_only mode for query: {query[:50]}...")
            online_search_response = self.answer_online_search(query, model=search_model)
            # Return online search response as the answer directly (no duplicate processing)
            return online_search_response, None, None

        # Handle files_only mode
        if search_mode == "files_only":
            logger.info(f"Using files_only mode for query: {query[:50]}...")
            if not search_results:
                return "I couldn't find any relevant information to answer your question.", None, None

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

            prompt = f"""You are an expert in bioventure investing.{conversation_context}

**Question**: {query}

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
If this is a follow-up question referring to previous conversation, use the context to understand what the user is asking about.
"""

            try:
                response = self.client.responses.create(
                    model=self.model,
                    temperature=self.temperature,
                    input=prompt
                )
                return response.output_text, None, None
            except Exception as e:
                logger.error(f"Error generating answer: {str(e)}")
                return f"I found {len(search_results)} relevant document(s), but encountered an error generating a comprehensive answer: {str(e)}", None, None

        # Handle sequential_analysis mode - extract from files first, then search online
        if search_mode == "sequential_analysis":
            logger.info(f"Using sequential_analysis mode for query: {query[:50]}...")

            if not search_results:
                return "I couldn't find any relevant information in your files to extract.", None, None

            # Step 1: Extract key information from files
            files_context_parts = []
            current_length = 0

            for idx, result in enumerate(search_results, 1):
                content = result.get("content", "")
                metadata = result.get("metadata", {})
                source = metadata.get("source", "Unknown")

                chunk = f"[Source {idx}: {source}]\n{content}\n"
                chunk_length = len(chunk)

                if current_length + chunk_length > max_context_length:
                    break

                files_context_parts.append(chunk)
                current_length += chunk_length

            files_context = "\n".join(files_context_parts)

            # Extract structured information from files
            extraction_prompt = f"""You are an expert in bioventure investing.{conversation_context}

**Question**: {query}

**Documents**:
{files_context}

**Task**: Extract and summarize ONLY the key facts, data, and conclusions from the documents. Focus on:
- Drug names, compounds, or products mentioned
- Efficacy rates, success rates, or performance metrics
- Clinical trial results or study outcomes
- Any quantitative data or statistics
- Key findings or conclusions

Be concise and factual. Only include information explicitly stated in the documents.

**Format your response as structured data** (e.g., bullet points or short paragraphs) that can be used for online comparison."""

            try:
                extraction_response = self.client.responses.create(
                    model=self.model,
                    temperature=self.temperature,
                    input=extraction_prompt
                )
                extracted_info = extraction_response.output_text
                logger.info(f"Extracted info from files: {extracted_info[:100]}...")
            except Exception as e:
                logger.error(f"Error extracting info from files: {str(e)}")
                return f"Error extracting information from files: {str(e)}", None, None

            # Step 2: Use extracted info to formulate enhanced online search query
            online_search_prompt = f"""Based on the following information extracted from documents, search for comparable or competitive information online:

**Extracted Information from User's Documents**:
{extracted_info}

**Original Question**: {query}

Search online for competitor data, industry benchmarks, or comparative information that relates to the extracted data above."""

            try:
                online_search_response = self.answer_online_search(online_search_prompt, model=search_model)
                logger.info("Online search completed in sequential mode")
            except Exception as e:
                logger.error(f"Error in online search: {str(e)}")
                online_search_response = f"Error performing online search: {str(e)}"

            # Step 3: Combine extracted info and online results into final answer
            final_prompt = f"""You are an expert in bioventure investing.{conversation_context}

**Question**: {query}

**Step 1 - Information Extracted from User's Documents**:
{extracted_info}

**Step 2 - Online Search Results**:
{online_search_response}

**Task**: Provide a comprehensive comparison and analysis. Structure your answer as follows:
1. **Summary of User's Document Data**: Briefly summarize the key findings from the user's files
2. **Comparative Analysis**: Compare with online findings (competitors, industry standards, etc.)
3. **Key Insights**: Provide actionable insights from the comparison
4. **Conclusion**: Synthesize the information

**Response Requirements**:
Do not fabricate any information. Be objective and factual.
Bold the most important facts or conclusions.
If there are discrepancies between file data and online data, point them out.
Do not include reference filenames in the answer.
If this is a follow-up question referring to previous conversation, use the context to understand what the user is asking about."""

            try:
                final_response = self.client.responses.create(
                    model=self.model,
                    temperature=self.temperature,
                    input=final_prompt
                )
                return final_response.output_text, online_search_response, extracted_info
            except Exception as e:
                logger.error(f"Error generating final answer: {str(e)}")
                return f"Error generating final answer: {str(e)}", online_search_response, extracted_info

        # Handle both mode with priority ordering
        if search_mode == "both":
            logger.info(f"Using both mode with priority: {priority_order} for query: {query[:50]}...")

            # Get online search response if included in priority
            if 'online_search' in priority_order:
                online_search_response = self.answer_online_search(query, model=search_model)

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

            prompt = f"""{conversation_context}

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
If this is a follow-up question referring to previous conversation, use the context to understand what the user is asking about.
"""

            try:
                response = self.client.responses.create(
                    model=self.model,
                    temperature=self.temperature,
                    input=prompt
                )
                return response.output_text, online_search_response, None
            except Exception as e:
                logger.error(f"Error generating answer: {str(e)}")
                return f"Error generating answer: {str(e)}", online_search_response, None

        return "Invalid search mode specified.", None, None


def get_answer_generator() -> AnswerGenerator:
    """Get answer generator instance"""
    return AnswerGenerator()
