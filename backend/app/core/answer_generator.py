"""
Answer generation using OpenAI GPT models
Similar to answer_with_search_ensemble from original code
"""
from openai import OpenAI
from typing import List, Dict, Any, Optional, Tuple
import logging

from backend.app.config import settings
from backend.app.utils.aws_secrets import get_key

logger = logging.getLogger(__name__)

# Gemini imports
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError as e:
    GEMINI_AVAILABLE = False
    logger.warning(f"Google GenAI library not available: {e}. Install with: pip install google-genai")


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

        # Initialize Gemini client
        self.gemini_client = None
        if GEMINI_AVAILABLE:
            try:
                gemini_api_key = get_key("googleai-api-key", "us-west-2")
                self.gemini_client = genai.Client(api_key=gemini_api_key)
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

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
                model="gpt-5.1",  # Use gpt-5.1 for intelligent classification
                input=classification_prompt,
                service_tier="priority"
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

    def analyze_query_for_extraction(self, query: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Analyze the query to determine what information needs to be extracted from documents.
        Uses few-shot prompting to guide the LLM in understanding different use case patterns.

        Args:
            query: User's original question
            conversation_history: Previous conversation context

        Returns:
            Dictionary with extraction_plan, use_case_type, and reasoning
        """
        try:
            conversation_context = self.format_conversation_history(conversation_history)

            analysis_prompt = f"""You are an expert query analyzer for a document search and information extraction system. Your task is to analyze user queries and determine what specific information needs to be extracted from their documents BEFORE performing online searches.

{conversation_context}

**User Query**: "{query}"

**Your Task**: Analyze this query and determine:
1. What specific information needs to be extracted from the user's documents
2. What use case pattern this query follows
3. How the extracted information will be used for online search

**Few-Shot Examples**:

---
**Example 1: Competitive Analysis Pattern**

Query: "What are the competitors of PPInnova?"

Analysis:
- Use Case Type: competitive_analysis
- Information to Extract from Documents:
  1. Identify PPInnova's assets/products (drug names, compound IDs)
  2. For each asset, extract:
     - Indication (disease/condition being treated)
     - Target (biological target, mechanism of action)
     - Stage of development (if mentioned)
     - Key efficacy metrics (if available)
- Online Search Strategy:
  - Search for companies with assets targeting the same indications and targets
  - Search for clinical trials in the same indication
  - Search for competitive landscape in the therapeutic area
- Reasoning: To find competitors, we first need to know what PPInnova is developing. Only after extracting their assets, indications, and targets can we meaningfully search for companies working on similar treatments.

---
**Example 2: Follow-up Questions Pattern**

Query: "Based on this KOL call note, what follow-up questions should we ask besides the ones already discussed?"

Analysis:
- Use Case Type: follow_up_questions
- Information to Extract from Documents:
  1. Identify all questions already asked in the call notes
  2. Extract key topics discussed
  3. Extract the KOL's responses and any gaps or ambiguities
  4. Extract context about the therapeutic area, drug, or study being discussed
  5. Note any concerns, objections, or areas of uncertainty raised by the KOL
- Online Search Strategy:
  - Search for best practices in KOL engagement for this therapeutic area
  - Search for recent developments in the field that weren't addressed
  - Search for common follow-up questions in similar contexts
- Reasoning: To generate meaningful follow-up questions, we need to know what was already asked and what context exists. This prevents redundancy and ensures questions are relevant and build on the existing conversation.

---
**Example 3: Benchmarking Pattern**

Query: "How does our product's efficacy compare to industry standards?"

Analysis:
- Use Case Type: benchmarking
- Information to Extract from Documents:
  1. Identify the product name and type
  2. Extract efficacy metrics (response rates, endpoints, statistical significance)
  3. Extract study design details (phase, patient population, dosing)
  4. Extract any internal benchmarks or comparisons already mentioned
- Online Search Strategy:
  - Search for industry standard efficacy rates for similar products
  - Search for competitor products' clinical trial results
  - Search for meta-analyses or systematic reviews in the indication
- Reasoning: To benchmark effectively, we need our own product's data first. The specific metrics, study design, and patient population will guide what online comparisons are relevant.

---
**Example 4: Market Intelligence Pattern**

Query: "What partnerships or collaborations should we explore based on our pipeline?"

Analysis:
- Use Case Type: market_intelligence
- Information to Extract from Documents:
  1. Identify all assets in the pipeline
  2. Extract development stage for each asset
  3. Extract therapeutic areas and indications
  4. Extract current capabilities and gaps (if mentioned)
  5. Extract geographic focus or limitations
- Online Search Strategy:
  - Search for companies with complementary capabilities in those therapeutic areas
  - Search for recent partnerships or deals in similar indications
  - Search for companies with geographic strengths where needed
- Reasoning: Partnership opportunities depend on understanding our own pipeline, capabilities, and gaps. Only with this context can we search for complementary partners online.

---

**Now analyze the user's query above and provide:**

1. **Use Case Type**: [competitive_analysis | follow_up_questions | benchmarking | market_intelligence | custom]
   - If "custom", briefly name the pattern

2. **Information to Extract from Documents**:
   - Provide a structured, numbered list of specific information items to extract
   - Be concrete and actionable (what exactly to look for)

3. **Online Search Strategy**:
   - How will the extracted information guide the online search?
   - What specific searches will be performed?

4. **Reasoning**:
   - Why does this query require sequential analysis (files first, then online)?
   - What would go wrong if we searched online without extracting from documents first?

**Format your response as JSON**:
```json
{{
  "use_case_type": "...",
  "information_to_extract": [
    "Item 1: ...",
    "Item 2: ..."
  ],
  "online_search_strategy": "...",
  "reasoning": "..."
}}
```

Analyze the query now:"""

            logger.info(f"[QUERY ANALYSIS] Analyzing query for extraction plan...")
            response = self.client.responses.create(
                model="gpt-5.1",  # Use advanced model for query analysis
                input=analysis_prompt,
                service_tier="priority"
            )

            analysis_text = response.output_text
            logger.info(f"[QUERY ANALYSIS] Raw response: {analysis_text[:500]}...")

            # Parse JSON response
            import json
            import re

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', analysis_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("Could not extract JSON from response")

            analysis_result = json.loads(json_str)
            logger.info(f"[QUERY ANALYSIS] Use case type: {analysis_result.get('use_case_type')}")
            logger.info(f"[QUERY ANALYSIS] Items to extract: {len(analysis_result.get('information_to_extract', []))}")

            return analysis_result

        except Exception as e:
            logger.error(f"[QUERY ANALYSIS] Error analyzing query: {str(e)}")
            # Return default analysis
            return {
                "use_case_type": "custom",
                "information_to_extract": [
                    "Key facts, data, and metrics from documents",
                    "Product names, compounds, or entities mentioned",
                    "Quantitative data and statistics",
                    "Key findings or conclusions"
                ],
                "online_search_strategy": "Use extracted information to search for comparative or supplementary data online",
                "reasoning": f"Error during analysis, using default extraction plan: {str(e)}"
            }

    def answer_online_search(self, prompt: str, model: Optional[str] = None, conversation_context: str = "") -> str:
        """
        Perform online search using OpenAI's web_search tool

        Args:
            prompt: Search query/prompt
            model: Optional model to use (defaults to self.online_search_model)
            conversation_context: Formatted conversation history for context

        Returns:
            Search results as text
        """
        try:
            search_model = model or self.online_search_model
            logger.info(f"Performing online search with model {search_model} for: {prompt[:50]}...")

            # Build full prompt with conversation context
            full_prompt = f"{conversation_context}{prompt}" if conversation_context else prompt

            # Build request parameters
            request_params = {
                "model": search_model,
                "tools": [{
                    "type": "web_search",
                }],
                "input": full_prompt
            }

            # Only add service_tier for o-series models that support it
            # gpt-5-pro and other models may not support this parameter
            if search_model.startswith("o"):
                request_params["service_tier"] = "priority"
                logger.info(f"Using priority service tier for {search_model}")

            response = self.client.responses.create(**request_params)
            logger.info("Online search completed successfully")
            return response.output_text
        except Exception as e:
            logger.error(f"Error performing online search: {str(e)}", exc_info=True)
            return f"Error performing online search: {str(e)}"

    def answer_with_gemini(self, prompt: str, conversation_context: str = "") -> str:
        """
        Perform search using Google Gemini with Google Search tool

        Args:
            prompt: Search query/prompt
            conversation_context: Formatted conversation history for context

        Returns:
            Search results as text
        """
        try:
            if not self.gemini_client:
                logger.error("Gemini client not initialized")
                return "Error: Gemini API is not available. Please check your API key configuration."

            logger.info(f"Performing Gemini search for: {prompt[:50]}...")

            # Build full prompt with conversation context
            full_prompt = f"{conversation_context}{prompt}" if conversation_context else prompt

            # Call Gemini with Google Search tool
            response = self.gemini_client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_modalities=["TEXT"],
                )
            )

            logger.info("Gemini search completed successfully")
            return response.text
        except Exception as e:
            logger.error(f"Error performing Gemini search: {str(e)}")
            return f"Error performing Gemini search: {str(e)}"

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
        for i, turn in enumerate(conversation_history[-10:], 1):  # Use last 10 turns (sufficient for 200k token models)
            formatted += f"\nTurn {i}:\n"
            formatted += f"User: {turn.get('query', '')}\n"
            formatted += f"Assistant: {turn.get('answer', '')[:2000]}...\n"  # Truncate answers at 2000 chars

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
            reasoning_mode: "non_reasoning" (gpt-5.1), "reasoning" (o4-mini), "reasoning_gpt5" (gpt-5-pro), "reasoning_gemini" (gemini-3-pro), or "deep_research" (o3-deep-research)
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
        elif reasoning_mode == "reasoning_gpt5":
            search_model = "gpt-5-pro"
        elif reasoning_mode == "reasoning_gemini":
            search_model = "gemini-3-pro-preview"
        elif reasoning_mode == "deep_research":
            search_model = "o3-deep-research"
        else:  # non_reasoning
            search_model = "gpt-5.1"

        logger.info(f"Using reasoning mode '{reasoning_mode}' with model '{search_model}'")

        # Format conversation history if provided
        conversation_context = self.format_conversation_history(conversation_history)

        online_search_response = None

        # Handle online_only mode - just return online search result directly
        if search_mode == "online_only":
            logger.info(f"Using online_only mode for query: {query[:50]}...")
            if reasoning_mode == "reasoning_gemini":
                online_search_response = self.answer_with_gemini(query, conversation_context=conversation_context)
            else:
                online_search_response = self.answer_online_search(query, model=search_model, conversation_context=conversation_context)
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
                    input=prompt,
                    service_tier="priority"
                )
                return response.output_text, None, None
            except Exception as e:
                logger.error(f"Error generating answer: {str(e)}")
                return f"I found {len(search_results)} relevant document(s), but encountered an error generating a comprehensive answer: {str(e)}", None, None

        # Handle sequential_analysis mode - extract from files first, then search online
        if search_mode == "sequential_analysis":
            import time
            seq_start_time = time.time()
            logger.info(f"[SEQUENTIAL] Starting sequential_analysis mode for query: {query[:50]}...")
            logger.info(f"[SEQUENTIAL] Using search_model: {search_model}, base model: {self.model}")

            if not search_results:
                return "I couldn't find any relevant information in your files to extract.", None, None

            # Step 0: Analyze query to determine what to extract (NEW)
            step0_start = time.time()
            logger.info(f"[SEQUENTIAL] Step 0: Analyzing query to determine extraction requirements...")
            query_analysis = self.analyze_query_for_extraction(query, conversation_history)
            step0_duration = time.time() - step0_start
            logger.info(f"[SEQUENTIAL] Step 0 complete in {step0_duration:.1f}s")
            logger.info(f"[SEQUENTIAL] Use case type: {query_analysis['use_case_type']}")
            logger.info(f"[SEQUENTIAL] Extraction items: {len(query_analysis['information_to_extract'])}")

            # Build files context
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

            # Step 1: Extract information guided by Step 0 analysis
            extraction_items_formatted = "\n".join([f"   {item}" for item in query_analysis['information_to_extract']])

            extraction_prompt = f"""You are an expert in bioventure investing.{conversation_context}

**Original Question**: {query}

**Use Case Type**: {query_analysis['use_case_type']}

**Documents**:
{files_context}

**Your Task**: Extract the following specific information from the documents:
{extraction_items_formatted}

**Extraction Guidelines**:
- Be systematic and thorough in extracting the requested information
- Only include information explicitly stated in the documents
- For each piece of information, organize it clearly and concisely
- If certain information is not available in the documents, explicitly state what's missing
- Format the extracted information in a structured way (bullet points, numbered lists, or short sections)
- Do NOT make assumptions or infer information not present in the documents

**Output Format**: Structure your extraction clearly so it can be used to guide an online search. Use headings or numbered sections for each major category of information."""

            try:
                step1_start = time.time()
                logger.info(f"[SEQUENTIAL] Step 1: Extracting info from files using {self.model} with guided analysis...")
                extraction_response = self.client.responses.create(
                    model=self.model,
                    input=extraction_prompt,
                    service_tier="priority"
                )
                extracted_info = extraction_response.output_text
                step1_duration = time.time() - step1_start
                logger.info(f"[SEQUENTIAL] Step 1 complete in {step1_duration:.1f}s. Extracted {len(extracted_info)} chars")
            except Exception as e:
                logger.error(f"[SEQUENTIAL] Step 1 FAILED: {str(e)}")
                return f"Error extracting information from files: {str(e)}", None, None

            # Step 2: Use extracted info to formulate enhanced online search query guided by analysis
            online_search_prompt = f"""Based on the following information extracted from the user's documents, perform an online search following the strategy below:

**Extracted Information from User's Documents**:
{extracted_info}

**Original Question**: {query}

**Use Case Type**: {query_analysis['use_case_type']}

**Online Search Strategy**: {query_analysis['online_search_strategy']}

**Task**: Execute the online search strategy using the extracted information. Be comprehensive and search for:
- Specific entities, companies, or products that match the criteria from extracted info
- Comparative data, benchmarks, or competitive intelligence
- Recent developments, news, or updates related to the extracted information
- Any gaps or missing information that needs to be filled with online data

Provide detailed, factual results from your online search."""

            try:
                step2_start = time.time()
                logger.info(f"[SEQUENTIAL] Step 2: Performing online search with {search_model}...")
                if reasoning_mode == "reasoning_gemini":
                    online_search_response = self.answer_with_gemini(online_search_prompt, conversation_context=conversation_context)
                else:
                    online_search_response = self.answer_online_search(online_search_prompt, model=search_model, conversation_context=conversation_context)
                step2_duration = time.time() - step2_start
                logger.info(f"[SEQUENTIAL] Step 2 complete in {step2_duration:.1f}s. Response: {len(online_search_response) if online_search_response else 0} chars")
            except Exception as e:
                logger.error(f"[SEQUENTIAL] Step 2 FAILED: {str(e)}")
                online_search_response = f"Error performing online search: {str(e)}"

            # Step 3: Combine extracted info and online results into final answer
            final_prompt = f"""You are an expert in bioventure investing.{conversation_context}

**Original Question**: {query}

**Analysis Context**:
- Use Case Type: {query_analysis['use_case_type']}
- Analysis Reasoning: {query_analysis['reasoning']}

**Step 1 - Information Extracted from User's Documents**:
{extracted_info}

**Step 2 - Online Search Results**:
{online_search_response}

**Task**: Provide a comprehensive answer that addresses the original question. Structure your answer appropriately based on the use case type:

For **competitive_analysis**: Focus on identifying competitors and comparing capabilities
For **follow_up_questions**: Provide thoughtful follow-up questions with rationale
For **benchmarking**: Compare user's data with industry standards
For **market_intelligence**: Identify opportunities and strategic insights
For **custom**: Structure based on the specific question

**Response Requirements**:
- Synthesize information from both documents and online sources
- Be objective and factual - do not fabricate any information
- Bold the most important facts, conclusions, or recommendations
- If there are discrepancies between file data and online data, point them out
- Provide actionable insights where appropriate
- Do not include reference filenames in the answer
- If this is a follow-up question referring to previous conversation, use the context to understand what the user is asking about"""

            try:
                step3_start = time.time()
                logger.info(f"[SEQUENTIAL] Step 3: Generating final answer using {self.model}...")
                final_response = self.client.responses.create(
                    model=self.model,
                    input=final_prompt,
                    service_tier="priority"
                )
                step3_duration = time.time() - step3_start
                total_duration = time.time() - seq_start_time
                logger.info(f"[SEQUENTIAL] Step 3 complete in {step3_duration:.1f}s")
                logger.info(f"[SEQUENTIAL] Total sequential_analysis completed in {total_duration:.1f}s")
                logger.info(f"[SEQUENTIAL] Performance breakdown: Step0={step0_duration:.1f}s, Step1={step1_duration:.1f}s, Step2={step2_duration:.1f}s, Step3={step3_duration:.1f}s")

                # Return answer with query analysis metadata
                return final_response.output_text, online_search_response, extracted_info
            except Exception as e:
                logger.error(f"[SEQUENTIAL] Step 3 FAILED: {str(e)}")
                return f"Error generating final answer: {str(e)}", online_search_response, extracted_info

        # Handle both mode with priority ordering
        if search_mode == "both":
            logger.info(f"Using both mode with priority: {priority_order} for query: {query[:50]}...")

            # Get online search response if included in priority
            if 'online_search' in priority_order:
                if reasoning_mode == "reasoning_gemini":
                    online_search_response = self.answer_with_gemini(query, conversation_context=conversation_context)
                else:
                    online_search_response = self.answer_online_search(query, model=search_model, conversation_context=conversation_context)

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
                    input=prompt,
                    service_tier="priority"
                )
                return response.output_text, online_search_response, None
            except Exception as e:
                logger.error(f"Error generating answer: {str(e)}")
                return f"Error generating answer: {str(e)}", online_search_response, None

        return "Invalid search mode specified.", None, None


def get_answer_generator() -> AnswerGenerator:
    """Get answer generator instance"""
    return AnswerGenerator()
