"""
Dynamic Sequential Analysis Pipeline

A flexible, configurable multi-stage pipeline for complex analysis workflows.
Supports arbitrary stage sequences with different operations:
- Extract: Pull structured data from documents
- Search: Query online with context from previous stages
- Transform: Process/analyze results from previous stages
- Generate: Create new content (e.g., follow-up questions)
- Combine: Synthesize results from multiple stages

Example Use Cases:
1. Competitor Analysis: Extract assets → Search competitors → Combine
2. KOL Follow-up: Extract topics → Generate questions → Research answers
3. Market Analysis: Extract indications → Search market data → Assess landscape
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from document_search import DocumentSearchSystem
from langchain.retrievers import BM25Retriever
from langchain_chroma import Chroma

logger = logging.getLogger(__name__)


class StageType(Enum):
    """Types of pipeline stages"""
    PLAN = "plan"                 # Analyze query and plan extraction/search strategy
    EXTRACT = "extract"           # Extract structured info from internal docs
    SEARCH = "search"             # Search online with context
    TRANSFORM = "transform"       # Process previous results
    GENERATE = "generate"         # Generate new content (questions, summaries, etc.)
    COMBINE = "combine"           # Combine multiple stage results


@dataclass
class StageConfig:
    """Configuration for a single pipeline stage"""
    name: str                                    # Stage identifier
    stage_type: StageType                       # Type of operation
    prompt_template: str                        # Prompt with {placeholders}
    model: str = "gpt-4.1"                      # Model to use

    # For EXTRACT stages
    extraction_schema: Optional[Dict] = None    # Expected JSON structure
    use_internal_docs: bool = True              # Search internal docs
    k_bm: int = 25                              # BM25 retrieval count
    k_jd: int = 25                              # Vector retrieval count

    # For SEARCH stages
    search_queries: Optional[List[str]] = None  # Static queries
    query_template: Optional[str] = None        # Dynamic query from prev stages
    iterate_over: Optional[str] = None          # Field to iterate (e.g., "assets")

    # For TRANSFORM/GENERATE stages
    input_stages: List[str] = field(default_factory=list)  # Previous stages to use

    # Output configuration
    output_format: str = "text"                 # 'json', 'text', 'list'
    output_key: Optional[str] = None            # Key for storing in context


class PipelineContext:
    """Maintains state across pipeline stages"""

    def __init__(self, initial_input: str):
        self.initial_input = initial_input
        self.stages: Dict[str, Any] = {}

    def add_result(self, stage_name: str, result: Any):
        """Store result from a stage"""
        self.stages[stage_name] = result

    def get_result(self, stage_name: str) -> Any:
        """Retrieve result from a stage"""
        return self.stages.get(stage_name)

    def format_template(self, template: str) -> str:
        """
        Format a template string with context values

        Supports:
        - {initial_input} - The original input
        - {stage_name.field} - Access specific stage result fields
        - {stage_name} - Access entire stage result
        """
        # Build replacement dict
        replacements = {
            "initial_input": self.initial_input
        }

        # Add all stage results
        for stage_name, result in self.stages.items():
            if isinstance(result, dict):
                # Add top-level access
                replacements[stage_name] = json.dumps(result, indent=2)
                # Add field-level access
                for key, value in result.items():
                    replacements[f"{stage_name}.{key}"] = str(value)
            else:
                replacements[stage_name] = str(result)

        # Format template
        try:
            return template.format(**replacements)
        except KeyError as e:
            logger.warning(f"Missing template key: {e}")
            return template


class SequentialPipeline:
    """
    Dynamic multi-stage analysis pipeline

    Executes a sequence of configurable stages, passing context between them.
    """

    def __init__(
        self,
        search_system: DocumentSearchSystem,
        bm25_retriever: Optional[BM25Retriever] = None,
        db_jd: Optional[Chroma] = None
    ):
        """
        Initialize pipeline

        Args:
            search_system: DocumentSearchSystem instance
            bm25_retriever: Optional BM25 retriever for internal docs
            db_jd: Optional vector database for internal docs
        """
        self.search_system = search_system
        self.bm25_retriever = bm25_retriever
        self.db_jd = db_jd

    def run(
        self,
        stages: List[StageConfig],
        initial_input: str
    ) -> Dict[str, Any]:
        """
        Execute the pipeline

        Args:
            stages: List of stage configurations to execute
            initial_input: Initial question/prompt

        Returns:
            Dict with results from all stages
        """
        logger.info("=" * 60)
        logger.info("STARTING SEQUENTIAL PIPELINE")
        logger.info(f"Stages: {len(stages)}")
        logger.info("=" * 60)

        context = PipelineContext(initial_input)

        for idx, stage in enumerate(stages, 1):
            logger.info(f"\nStage {idx}/{len(stages)}: {stage.name} ({stage.stage_type.value})")

            result = self._execute_stage(stage, context)
            context.add_result(stage.name, result)

            logger.info(f"Stage {stage.name} complete")

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)

        return {
            "initial_input": initial_input,
            "stages": context.stages
        }

    def _execute_stage(
        self,
        stage: StageConfig,
        context: PipelineContext
    ) -> Any:
        """Execute a single stage based on its type"""

        if stage.stage_type == StageType.PLAN:
            return self._execute_plan(stage, context)

        elif stage.stage_type == StageType.EXTRACT:
            return self._execute_extract(stage, context)

        elif stage.stage_type == StageType.SEARCH:
            return self._execute_search(stage, context)

        elif stage.stage_type == StageType.TRANSFORM:
            return self._execute_transform(stage, context)

        elif stage.stage_type == StageType.GENERATE:
            return self._execute_generate(stage, context)

        elif stage.stage_type == StageType.COMBINE:
            return self._execute_combine(stage, context)

        else:
            raise ValueError(f"Unknown stage type: {stage.stage_type}")

    def _execute_plan(
        self,
        stage: StageConfig,
        context: PipelineContext
    ) -> Dict[str, Any]:
        """
        Analyze the query and plan what to extract and search for
        Uses few-shot prompting with examples
        """
        # Format prompt with context
        prompt = context.format_template(stage.prompt_template)

        # Use GPT to analyze and plan
        result = self.search_system.answer_gpt(
            prompt=prompt,
            model=stage.model
        )

        # Parse JSON plan
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
                logger.info(f"Plan generated: {len(plan.get('extraction_fields', []))} fields to extract")
                return plan
            else:
                logger.warning("No JSON found in plan, returning raw text")
                return {"raw_text": result}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            return {"raw_text": result, "parse_error": str(e)}

    def _execute_extract(
        self,
        stage: StageConfig,
        context: PipelineContext
    ) -> Dict[str, Any]:
        """
        Extract structured information from internal documents
        """
        # Format prompt with context
        prompt = context.format_template(stage.prompt_template)

        # Add schema if provided
        if stage.extraction_schema:
            schema_str = json.dumps(stage.extraction_schema, indent=2)
            prompt = f"{prompt}\n\nReturn ONLY a JSON object with this structure:\n{schema_str}"

        # Search internal docs
        if not (self.bm25_retriever and self.db_jd):
            raise ValueError("EXTRACT stage requires bm25_retriever and db_jd")

        result, _ = self.search_system.answer_with_search_ensemble(
            question=prompt,
            bm25_retriever=self.bm25_retriever,
            k_bm=stage.k_bm,
            db_jd=self.db_jd,
            k_jd=stage.k_jd,
            search_model=stage.model,
            priority_order=['jarvis_docs'],  # Internal docs only
            auto_reduce_on_limit=True
        )

        # Parse JSON if expected
        if stage.output_format == "json":
            try:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    logger.warning("No JSON found in extraction, returning raw text")
                    return {"raw_text": result}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return {"raw_text": result, "parse_error": str(e)}

        return result

    def _execute_search(
        self,
        stage: StageConfig,
        context: PipelineContext
    ) -> Union[str, List[Dict[str, str]]]:
        """
        Perform online searches using context from previous stages
        """
        queries = []

        # Build queries from template
        if stage.query_template:
            if stage.iterate_over:
                # Iterate over a field from previous stage
                # e.g., iterate_over="extract_assets.assets"
                parts = stage.iterate_over.split('.')
                stage_name = parts[0]
                field_path = parts[1:] if len(parts) > 1 else []

                data = context.get_result(stage_name)
                if not data:
                    raise ValueError(f"Stage {stage_name} not found in context")

                # Navigate to nested field
                for field in field_path:
                    data = data.get(field, [])

                # Build query for each item
                if isinstance(data, list):
                    for item in data:
                        try:
                            query = stage.query_template.format(**item)
                            queries.append(query)
                        except (KeyError, TypeError) as e:
                            logger.warning(f"Failed to format query: {e}")
                else:
                    logger.warning(f"Expected list for iteration, got {type(data)}")
            else:
                # Single query from template
                query = context.format_template(stage.query_template)
                queries.append(query)

        # Use static queries if provided
        if stage.search_queries:
            queries.extend([context.format_template(q) for q in stage.search_queries])

        if not queries:
            raise ValueError("No queries generated for SEARCH stage")

        # Execute searches
        results = []
        for idx, query in enumerate(queries, 1):
            logger.info(f"Search {idx}/{len(queries)}: {query[:80]}...")

            result = self.search_system.answer_online_search(
                prompt=query,
                search_model=stage.model
            )

            results.append({
                "query": query,
                "result": result
            })

        # Return single result or list
        if len(results) == 1:
            return results[0]["result"]
        return results

    def _execute_transform(
        self,
        stage: StageConfig,
        context: PipelineContext
    ) -> Any:
        """
        Transform/process results from previous stages
        """
        # Build prompt with inputs from specified stages
        prompt = context.format_template(stage.prompt_template)

        # Use GPT to transform
        result = self.search_system.answer_gpt(
            prompt=prompt,
            model=stage.model
        )

        # Parse output format
        if stage.output_format == "json":
            try:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        elif stage.output_format == "list":
            # Try to parse as list
            try:
                list_match = re.search(r'\[.*\]', result, re.DOTALL)
                if list_match:
                    return json.loads(list_match.group())
            except json.JSONDecodeError:
                pass

        return result

    def _execute_generate(
        self,
        stage: StageConfig,
        context: PipelineContext
    ) -> Any:
        """
        Generate new content based on previous stages
        """
        # Similar to transform, but focused on generation
        return self._execute_transform(stage, context)

    def _execute_combine(
        self,
        stage: StageConfig,
        context: PipelineContext
    ) -> str:
        """
        Combine results from multiple previous stages
        """
        # Build comprehensive prompt
        prompt = context.format_template(stage.prompt_template)

        # Use GPT to synthesize
        result = self.search_system.answer_gpt(
            prompt=prompt,
            model=stage.model
        )

        return result


# ============================================================================
# PRE-CONFIGURED PIPELINES FOR COMMON USE CASES
# ============================================================================

class PipelineTemplates:
    """Pre-built pipeline configurations for common use cases"""

    @staticmethod
    def competitor_analysis() -> List[StageConfig]:
        """
        Pipeline for finding competitors based on internal company data

        Stages:
        1. Extract company assets/targets/indications from internal docs
        2. Search online for competitors with similar targets
        3. Combine internal + external data
        """
        return [
            StageConfig(
                name="extract_assets",
                stage_type=StageType.EXTRACT,
                prompt_template="""
                Extract the company's drug pipeline assets.
                For each asset, identify:
                - Asset name
                - Molecular target
                - Indication(s)
                - Modality (e.g., degrader, inhibitor, antibody)
                - Development stage

                Based on: {initial_input}
                """,
                model="gpt-5-pro",
                extraction_schema={
                    "company_name": "string",
                    "assets": [{
                        "asset_name": "string",
                        "target": "string",
                        "indication": "string or list",
                        "modality": "string",
                        "development_stage": "string"
                    }]
                },
                k_bm=50,
                k_jd=50,
                output_format="json"
            ),
            StageConfig(
                name="search_competitors",
                stage_type=StageType.SEARCH,
                query_template="""
                Comprehensively list biotech companies with drug programs targeting {target}
                for {indication}. For each competitor, provide:
                - Company name
                - Asset/program name
                - Modality
                - Development stage
                - Recent funding/valuation (if available)

                Focus on direct competitors with similar approach ({modality}).
                """,
                model="o4-mini",
                iterate_over="extract_assets.assets"
            ),
            StageConfig(
                name="combine_analysis",
                stage_type=StageType.COMBINE,
                prompt_template="""
                **Original Question**: {initial_input}

                **Internal Company Data** (Authoritative):
                {extract_assets}

                **Competitor Research** (External):
                {search_competitors}

                **Instructions**:
                1. Use internal data as the primary source of truth
                2. Enrich with competitor information from online research
                3. Provide a comprehensive competitive landscape analysis
                4. Highlight direct competitors for each asset
                5. Include development stages and funding information
                6. Bold important findings

                Provide a comprehensive answer to the original question.
                """,
                model="gpt-5-pro",
                input_stages=["extract_assets", "search_competitors"]
            )
        ]

    @staticmethod
    def kol_followup_questions() -> List[StageConfig]:
        """
        Pipeline for generating follow-up questions from KOL call notes

        Stages:
        1. Extract key topics and insights from call notes
        2. Generate follow-up questions based on gaps
        3. Optionally research answers to questions
        """
        return [
            StageConfig(
                name="extract_topics",
                stage_type=StageType.EXTRACT,
                prompt_template="""
                Analyze the following KOL call notes and extract:
                - Key topics discussed
                - Important insights or opinions shared
                - Areas that were mentioned but not fully explored
                - Potential concerns or questions raised

                Call notes: {initial_input}
                """,
                model="gpt-5-pro",
                extraction_schema={
                    "topics_discussed": ["string"],
                    "key_insights": ["string"],
                    "unexplored_areas": ["string"],
                    "concerns_raised": ["string"]
                },
                k_bm=25,
                k_jd=25,
                output_format="json"
            ),
            StageConfig(
                name="generate_questions",
                stage_type=StageType.GENERATE,
                prompt_template="""
                Based on the KOL call analysis below, generate thoughtful follow-up questions
                that should be asked in the next interaction.

                Call Analysis:
                {extract_topics}

                Generate 5-10 follow-up questions that:
                1. Explore unexplored areas in more depth
                2. Address any concerns that were raised
                3. Clarify ambiguous statements
                4. Gather additional context on key insights
                5. Are specific, actionable, and professional

                Return as a JSON list of questions with explanations:
                [
                  {{
                    "question": "...",
                    "rationale": "why this question is important",
                    "category": "clarification|exploration|validation"
                  }},
                  ...
                ]
                """,
                model="gpt-5-pro",
                output_format="json"
            ),
            StageConfig(
                name="research_answers",
                stage_type=StageType.SEARCH,
                query_template="""
                Research background information to help prepare for this follow-up question:

                {question}

                Provide relevant context, data, and insights that would be useful
                when asking this question to a KOL.
                """,
                model="o4-mini",
                iterate_over="generate_questions"
            ),
            StageConfig(
                name="compile_report",
                stage_type=StageType.COMBINE,
                prompt_template="""
                **KOL Call Follow-up Report**

                **Topics Extracted**:
                {extract_topics}

                **Generated Follow-up Questions**:
                {generate_questions}

                **Background Research**:
                {research_answers}

                Create a comprehensive follow-up report that includes:
                1. Summary of key topics from the call
                2. List of follow-up questions organized by category
                3. Background research for each question
                4. Recommended approach for the next interaction

                Format for easy reference during the next call.
                """,
                model="gpt-4.1"
            )
        ]

    @staticmethod
    def market_assessment() -> List[StageConfig]:
        """
        Pipeline for market analysis based on company's target indications

        Stages:
        1. Extract company's target indications
        2. Search for market size data
        3. Search for competitive landscape
        4. Search for regulatory environment
        5. Combine into comprehensive assessment
        """
        return [
            StageConfig(
                name="extract_indications",
                stage_type=StageType.EXTRACT,
                prompt_template="""
                Extract the company's target therapeutic indications.
                For each indication, identify:
                - Indication name
                - Target patient population
                - Current standard of care (if mentioned)
                - Company's approach/advantage

                Based on: {initial_input}
                """,
                model="gpt-5-pro",
                extraction_schema={
                    "company_name": "string",
                    "indications": [{
                        "indication": "string",
                        "patient_population": "string",
                        "current_soc": "string",
                        "company_approach": "string"
                    }]
                },
                k_bm=40,
                k_jd=40,
                output_format="json"
            ),
            StageConfig(
                name="market_size",
                stage_type=StageType.SEARCH,
                query_template="""
                Research the market size for {indication}:
                - Total addressable market (TAM) in USD
                - Market growth rate (CAGR)
                - Patient population size
                - Current market leaders and their revenues
                - Market trends and projections

                Provide specific numbers with sources where possible.
                """,
                model="o4-mini",
                iterate_over="extract_indications.indications"
            ),
            StageConfig(
                name="competitive_landscape",
                stage_type=StageType.SEARCH,
                query_template="""
                Research the competitive landscape for {indication}:
                - Key players and their products
                - Drugs in development (clinical trials)
                - Recent approvals or setbacks
                - Unmet medical needs
                - Barriers to entry
                """,
                model="o4-mini",
                iterate_over="extract_indications.indications"
            ),
            StageConfig(
                name="regulatory_environment",
                stage_type=StageType.SEARCH,
                query_template="""
                Research the regulatory environment for {indication}:
                - FDA/EMA approval pathways
                - Recent regulatory guidance
                - Endpoints and trial requirements
                - Special designations (orphan, fast track, etc.)
                - Pricing and reimbursement considerations
                """,
                model="o4-mini",
                iterate_over="extract_indications.indications"
            ),
            StageConfig(
                name="final_assessment",
                stage_type=StageType.COMBINE,
                prompt_template="""
                **Market Assessment Request**: {initial_input}

                **Company Indications**:
                {extract_indications}

                **Market Size Analysis**:
                {market_size}

                **Competitive Landscape**:
                {competitive_landscape}

                **Regulatory Environment**:
                {regulatory_environment}

                **Instructions**:
                Create a comprehensive market assessment that synthesizes all the above information.

                Include:
                1. Executive Summary
                2. Market Opportunity (size, growth, unmet needs)
                3. Competitive Analysis (key players, positioning)
                4. Regulatory Pathway (requirements, timeline estimates)
                5. Risk Factors and Challenges
                6. Investment Recommendation

                Use bold for key findings and numbers.
                """,
                model="gpt-5-pro"
            )
        ]


# ============================================================================
# SMART PIPELINE WITH AUTO-PLANNING
# ============================================================================

class SmartPipeline(SequentialPipeline):
    """
    Intelligent pipeline that analyzes queries and auto-configures extraction/search

    Uses LLM with few-shot prompting to:
    1. Analyze the user's query
    2. Determine what information to extract from internal docs
    3. Plan what to search for online
    4. Execute the planned pipeline
    """

    def create_few_shot_planning_prompt(self) -> str:
        """
        Create few-shot prompt for query analysis and planning
        """
        return """
You are an AI assistant that analyzes user queries and plans information extraction and search strategies.

Given a user query, output a JSON plan that specifies:
1. What information to extract from internal documents
2. What to search for online
3. How to combine the results

# EXAMPLES:

## Example 1: Competitor Analysis Query
**User Query**: "Who are PPInnova's main competitors?"

**Analysis**:
- Need to extract PPInnova's assets/pipeline from internal docs first
- Then search online for competitors with similar targets/indications
- Combine internal company data with external competitor data

**Plan**:
```json
{
  "query_type": "competitor_analysis",
  "extraction_needed": true,
  "extraction_fields": [
    {
      "field_name": "company_name",
      "description": "The company name",
      "type": "string"
    },
    {
      "field_name": "assets",
      "description": "List of drug pipeline assets",
      "type": "array",
      "item_schema": {
        "asset_name": "string",
        "target": "string (e.g., STAT6, RBM39)",
        "indication": "string or list",
        "modality": "string (e.g., degrader, inhibitor)",
        "development_stage": "string"
      }
    }
  ],
  "extraction_prompt": "Extract the company's drug pipeline assets. For each asset, identify: asset name, molecular target, indication(s), modality, and development stage.",
  "search_template": "Find biotech companies with drug programs targeting {target} for {indication}. Include: company names, asset names, modalities, development stages, and recent funding.",
  "iterate_over_field": "assets",
  "combination_instructions": "Use internal company data as authoritative. Enrich with competitor information from online research. Highlight direct competitors for each asset."
}
```

## Example 2: KOL Follow-up Questions
**User Query**: "Generate follow-up questions based on this KOL call: Dr. Smith discussed our Phase 2 results and mentioned concerns about dosing frequency."

**Analysis**:
- Need to extract key topics, insights, and gaps from call notes
- Generate thoughtful follow-up questions
- Optionally research background for questions

**Plan**:
```json
{
  "query_type": "kol_followup",
  "extraction_needed": true,
  "extraction_fields": [
    {
      "field_name": "topics_discussed",
      "description": "Main topics covered in the call",
      "type": "array of strings"
    },
    {
      "field_name": "key_insights",
      "description": "Important insights or opinions shared",
      "type": "array of strings"
    },
    {
      "field_name": "unexplored_areas",
      "description": "Topics mentioned but not fully explored",
      "type": "array of strings"
    },
    {
      "field_name": "concerns_raised",
      "description": "Concerns or questions raised by the KOL",
      "type": "array of strings"
    }
  ],
  "extraction_prompt": "Analyze the KOL call notes and extract: key topics discussed, important insights, areas not fully explored, and concerns raised.",
  "generate_content": {
    "type": "questions",
    "prompt": "Based on the call analysis, generate 5-10 thoughtful follow-up questions. For each question, provide rationale and category (clarification/exploration/validation).",
    "output_format": "json_array"
  },
  "search_template": "Research background information for this follow-up question: {question}. Provide relevant context and data.",
  "iterate_over_field": "generated_questions",
  "combination_instructions": "Create a comprehensive follow-up report with: call summary, categorized questions, and background research for each question."
}
```

## Example 3: Market Assessment
**User Query**: "What's the market opportunity for our atopic dermatitis program?"

**Analysis**:
- Extract company's target indications and programs
- Search for market size, competitive landscape, regulatory environment
- Synthesize into investment assessment

**Plan**:
```json
{
  "query_type": "market_assessment",
  "extraction_needed": true,
  "extraction_fields": [
    {
      "field_name": "indications",
      "description": "Target therapeutic indications",
      "type": "array",
      "item_schema": {
        "indication": "string",
        "patient_population": "string",
        "current_soc": "string",
        "company_approach": "string"
      }
    }
  ],
  "extraction_prompt": "Extract the company's target therapeutic indications. For each, identify: indication name, target patient population, current standard of care, and company's approach.",
  "search_queries": [
    {
      "query_template": "Market size for {indication}: TAM, growth rate, patient population, market leaders and revenues, trends.",
      "iterate_over": "indications"
    },
    {
      "query_template": "Competitive landscape for {indication}: key players, drugs in development, recent approvals, unmet needs.",
      "iterate_over": "indications"
    },
    {
      "query_template": "Regulatory environment for {indication}: approval pathways, endpoints, trial requirements, special designations.",
      "iterate_over": "indications"
    }
  ],
  "combination_instructions": "Create comprehensive market assessment with: Executive Summary, Market Opportunity (size, growth, unmet needs), Competitive Analysis, Regulatory Pathway, Risk Factors, Investment Recommendation."
}
```

# YOUR TASK:

Analyze the following user query and create a similar JSON plan:

**User Query**: {initial_input}

**Output Requirements**:
1. Return ONLY a valid JSON object (no markdown, no explanations)
2. Include all necessary fields for extraction and search
3. Be specific about what information is needed and where to find it
4. Provide clear templates for searches
5. Specify how to combine results

**JSON Plan**:
"""

    def run_smart(
        self,
        user_query: str,
        planning_model: str = "gpt-5.1"
    ) -> Dict[str, Any]:
        """
        Run intelligent pipeline with automatic planning

        Args:
            user_query: The user's question
            planning_model: Model for query analysis (default: gpt-5.1)

        Returns:
            Dict with plan and results from all stages
        """
        logger.info("=" * 60)
        logger.info("SMART PIPELINE WITH AUTO-PLANNING")
        logger.info("=" * 60)

        # Stage 1: PLAN - Analyze query and create execution plan
        plan_stage = StageConfig(
            name="plan",
            stage_type=StageType.PLAN,
            prompt_template=self.create_few_shot_planning_prompt(),
            model=planning_model,
            output_format="json"
        )

        context = PipelineContext(user_query)
        plan = self._execute_plan(plan_stage, context)
        context.add_result("plan", plan)

        logger.info(f"Query Type: {plan.get('query_type', 'unknown')}")
        logger.info(f"Extraction Needed: {plan.get('extraction_needed', False)}")

        # Stage 2: EXTRACT - Use plan to extract information
        if plan.get("extraction_needed"):
            # Build extraction schema from plan
            extraction_schema = {}
            for field in plan.get("extraction_fields", []):
                field_name = field.get("field_name")
                if field.get("type") == "array":
                    extraction_schema[field_name] = [field.get("item_schema", {})]
                else:
                    extraction_schema[field_name] = field.get("description", "string")

            extract_stage = StageConfig(
                name="extract",
                stage_type=StageType.EXTRACT,
                prompt_template=plan.get("extraction_prompt", "Extract relevant information from documents."),
                model="gpt-5-pro",
                extraction_schema=extraction_schema,
                k_bm=40,
                k_jd=40,
                output_format="json"
            )

            extracted = self._execute_extract(extract_stage, context)
            context.add_result("extract", extracted)
            logger.info(f"Extraction complete: {len(extracted)} fields")

        # Stage 3: SEARCH or GENERATE - Based on plan
        if plan.get("generate_content"):
            # Generate content (e.g., questions)
            gen_config = plan["generate_content"]
            generate_stage = StageConfig(
                name="generate",
                stage_type=StageType.GENERATE,
                prompt_template=gen_config.get("prompt", "Generate content based on: {extract}"),
                model="gpt-5-pro",
                output_format=gen_config.get("output_format", "text")
            )

            generated = self._execute_generate(generate_stage, context)
            context.add_result("generate", generated)
            logger.info("Generation complete")

        # Stage 4: SEARCH - Use plan's search template
        search_results = []
        if plan.get("search_template"):
            search_stage = StageConfig(
                name="search",
                stage_type=StageType.SEARCH,
                query_template=plan.get("search_template"),
                model="o4-mini",
                iterate_over=f"extract.{plan.get('iterate_over_field')}" if plan.get('iterate_over_field') else None
            )

            search_results = self._execute_search(search_stage, context)
            context.add_result("search", search_results)
            logger.info(f"Search complete: {len(search_results) if isinstance(search_results, list) else 1} queries")

        # Handle multiple search queries
        if plan.get("search_queries"):
            for idx, search_config in enumerate(plan["search_queries"]):
                search_stage = StageConfig(
                    name=f"search_{idx+1}",
                    stage_type=StageType.SEARCH,
                    query_template=search_config.get("query_template"),
                    model="o4-mini",
                    iterate_over=f"extract.{search_config.get('iterate_over')}" if search_config.get('iterate_over') else None
                )

                results = self._execute_search(search_stage, context)
                context.add_result(f"search_{idx+1}", results)

        # Stage 5: COMBINE - Synthesize all results
        combine_stage = StageConfig(
            name="final_answer",
            stage_type=StageType.COMBINE,
            prompt_template=f"""
**Original Query**: {{initial_input}}

**Extracted Information** (from internal documents):
{{extract}}

**Search Results** (from online):
{{search}}

**Combination Instructions**:
{plan.get('combination_instructions', 'Provide a comprehensive answer combining internal and external information.')}

**Requirements**:
- Use internal data as authoritative source
- Enrich with external research
- Bold key findings
- Answer the original query comprehensively
            """,
            model="gpt-5-pro"
        )

        final_answer = self._execute_combine(combine_stage, context)
        context.add_result("final_answer", final_answer)

        logger.info("=" * 60)
        logger.info("SMART PIPELINE COMPLETE")
        logger.info("=" * 60)

        return {
            "query": user_query,
            "plan": plan,
            "stages": context.stages,
            "final_answer": final_answer
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Example of how to use the dynamic pipeline system"""

    from document_search import DocumentSearchSystem

    # Initialize
    search_system = DocumentSearchSystem(enable_logging=True)

    # Note: You'll need to load your bm25_retriever and db_jd
    # pipeline = SequentialPipeline(search_system, bm25_retriever, db_jd)

    print("=" * 70)
    print("SEQUENTIAL PIPELINE - EXAMPLE CONFIGURATIONS")
    print("=" * 70)

    # NEW: Smart Pipeline with Auto-Planning
    print("\n0. SMART PIPELINE (AUTO-PLANNING)")
    print("-" * 70)
    print("Automatically analyzes query and plans extraction/search:")
    print("""
# Load your data
bm25_retriever = ...
db_jd = ...

# Create smart pipeline
smart_pipeline = SmartPipeline(search_system, bm25_retriever, db_jd)

# Run with ANY query - it figures out what to do
results = smart_pipeline.run_smart(
    user_query="Who are PPInnova's competitors?",
    planning_model="gpt-5-pro"
)

# Or with different query
results = smart_pipeline.run_smart(
    user_query="Generate follow-up questions from this KOL call: ..."
)

# Access results
print("Plan:", results["plan"])
print("Final Answer:", results["final_answer"])
    """)

    # Example 1: Competitor Analysis
    print("\n1. COMPETITOR ANALYSIS PIPELINE")
    print("-" * 70)
    competitor_stages = PipelineTemplates.competitor_analysis()
    print(f"Stages: {len(competitor_stages)}")
    for idx, stage in enumerate(competitor_stages, 1):
        print(f"  {idx}. {stage.name} ({stage.stage_type.value})")

    # Example 2: KOL Follow-up
    print("\n2. KOL FOLLOW-UP QUESTIONS PIPELINE")
    print("-" * 70)
    kol_stages = PipelineTemplates.kol_followup_questions()
    print(f"Stages: {len(kol_stages)}")
    for idx, stage in enumerate(kol_stages, 1):
        print(f"  {idx}. {stage.name} ({stage.stage_type.value})")

    # Example 3: Market Assessment
    print("\n3. MARKET ASSESSMENT PIPELINE")
    print("-" * 70)
    market_stages = PipelineTemplates.market_assessment()
    print(f"Stages: {len(market_stages)}")
    for idx, stage in enumerate(market_stages, 1):
        print(f"  {idx}. {stage.name} ({stage.stage_type.value})")

    print("\n" + "=" * 70)
    print("To run a pipeline:")
    print("=" * 70)
    print("""
# Load your data
bm25_retriever = ...
db_jd = ...

# Create pipeline
pipeline = SequentialPipeline(search_system, bm25_retriever, db_jd)

# Run with a template
results = pipeline.run(
    stages=PipelineTemplates.competitor_analysis(),
    initial_input="Who are PPInnova's competitors?"
)

# Or create custom stages
custom_stages = [
    StageConfig(
        name="my_stage",
        stage_type=StageType.EXTRACT,
        prompt_template="...",
        model="gpt-5-pro"
    ),
    # ... more stages
]

results = pipeline.run(custom_stages, "My question")
    """)


if __name__ == "__main__":
    example_usage()
