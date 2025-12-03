"""
Sequential Analysis Pipeline for Document Search

Two-stage process:
1. Extract structured information from internal documents
2. Use extracted info to search online for additional context (e.g., competitors)
"""

import logging
from typing import List, Dict, Any, Tuple
import json
import re

from document_search import DocumentSearchSystem
from langchain.retrievers import BM25Retriever
from langchain_chroma import Chroma

logger = logging.getLogger(__name__)


class SequentialAnalysisPipeline:
    """
    Multi-stage analysis pipeline that:
    1. Extracts structured info from internal docs
    2. Uses extracted info for targeted online searches
    3. Combines results
    """

    def __init__(self, search_system: DocumentSearchSystem):
        """Initialize with a DocumentSearchSystem instance"""
        self.search_system = search_system

    def extract_structured_info(
        self,
        question: str,
        bm25_retriever: BM25Retriever,
        k_bm: int,
        db_jd: Chroma,
        k_jd: int,
        extraction_model: str = "gpt-5-pro",
        extraction_schema: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Stage 1: Extract structured information from internal documents only

        Args:
            question: Extraction question
            bm25_retriever: BM25 retriever
            k_bm: Number of docs from BM25
            db_jd: Vector database
            k_jd: Number of docs from vector search
            extraction_model: Model for extraction
            extraction_schema: Expected JSON structure

        Returns:
            Extracted structured data as dict
        """
        logger.info(f"Stage 1: Extracting structured info from internal docs")

        # Use internal docs only (no online search)
        extraction_prompt = question

        if extraction_schema:
            # Add schema to guide extraction
            schema_str = json.dumps(extraction_schema, indent=2)
            extraction_prompt = f"{question}\n\nReturn ONLY a JSON object with this structure:\n{schema_str}"

        # Search internal docs only
        result, _ = self.search_system.answer_with_search_ensemble(
            question=extraction_prompt,
            bm25_retriever=bm25_retriever,
            k_bm=k_bm,
            db_jd=db_jd,
            k_jd=k_jd,
            search_model=extraction_model,
            priority_order=['jarvis_docs'],  # Internal docs ONLY
            auto_reduce_on_limit=True
        )

        # Parse JSON response
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())
            else:
                # If no JSON found, return as text
                extracted_data = {"raw_text": result}
                logger.warning("No JSON found in extraction, returning as raw text")

            logger.info(f"Stage 1 complete: Extracted {len(extracted_data)} fields")
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {"raw_text": result, "parse_error": str(e)}

    def search_online_with_extracted_info(
        self,
        extracted_info: Dict[str, Any],
        search_template: str,
        search_model: str = "o4-mini"
    ) -> List[Dict[str, str]]:
        """
        Stage 2: Use extracted info to perform targeted online searches

        Args:
            extracted_info: Data extracted from stage 1
            search_template: Template for building search queries
                           Use {field_name} to reference extracted data
            search_model: Model for online search

        Returns:
            List of search results
        """
        logger.info(f"Stage 2: Searching online with extracted info")

        search_results = []

        # Build search queries from template
        queries = self._build_search_queries(extracted_info, search_template)

        for idx, query in enumerate(queries):
            logger.info(f"Online search {idx+1}/{len(queries)}: {query[:100]}...")

            # Perform online search
            result = self.search_system.answer_online_search(
                prompt=query,
                search_model=search_model
            )

            search_results.append({
                "query": query,
                "result": result
            })

        logger.info(f"Stage 2 complete: {len(search_results)} online searches")
        return search_results

    def _build_search_queries(
        self,
        extracted_info: Dict[str, Any],
        search_template: str
    ) -> List[str]:
        """
        Build search queries from extracted info and template

        Example template:
        "Find competitors for {asset_name} targeting {indication} with {target}"
        """
        queries = []

        # Handle nested structures (e.g., assets array)
        if "assets" in extracted_info and isinstance(extracted_info["assets"], list):
            # Build query for each asset
            for asset in extracted_info["assets"]:
                try:
                    query = search_template.format(**asset)
                    queries.append(query)
                except KeyError as e:
                    logger.warning(f"Missing field in template: {e}")
                    continue
        else:
            # Single query from top-level fields
            try:
                query = search_template.format(**extracted_info)
                queries.append(query)
            except KeyError as e:
                logger.warning(f"Missing field in template: {e}")

        return queries

    def combine_results(
        self,
        question: str,
        extracted_info: Dict[str, Any],
        online_results: List[Dict[str, str]],
        combine_model: str = "gpt-5-pro"
    ) -> str:
        """
        Stage 3: Combine extracted info with online results

        Args:
            question: Original user question
            extracted_info: Data from stage 1
            online_results: Results from stage 2
            combine_model: Model for final combination

        Returns:
            Final combined answer
        """
        logger.info(f"Stage 3: Combining extracted info with online results")

        # Build combined prompt
        extracted_str = json.dumps(extracted_info, indent=2)
        online_str = "\n\n".join([
            f"Search: {r['query']}\nResult: {r['result']}"
            for r in online_results
        ])

        prompt = f"""
**Original Question**: {question}

**Information from Internal Documents** (Authoritative):
{extracted_str}

**Information from Online Search** (Supplementary):
{online_str}

**Instructions**:
1. Use the internal documents as the primary source of truth
2. Enrich with online search results (competitors, market data, etc.)
3. Provide a comprehensive answer that combines both sources
4. Clearly distinguish between internal facts and external market data
5. If conflicts exist, trust internal documents over online sources
6. Bold important facts for readability

**Answer the original question comprehensively:**
"""

        # Use answer_gpt directly (no retrieval needed, we have all context)
        answer = self.search_system.answer_gpt(prompt, model=combine_model)

        logger.info(f"Stage 3 complete: Combined answer generated")
        return answer

    def run_sequential_analysis(
        self,
        question: str,
        bm25_retriever: BM25Retriever,
        k_bm: int,
        db_jd: Chroma,
        k_jd: int,
        extraction_schema: Dict[str, Any],
        search_template: str,
        extraction_model: str = "gpt-5-pro",
        search_model: str = "o4-mini",
        combine_model: str = "gpt-5-pro"
    ) -> Tuple[Dict[str, Any], List[Dict[str, str]], str]:
        """
        Run complete sequential analysis pipeline

        Args:
            question: Question for extraction (stage 1)
            bm25_retriever: BM25 retriever for internal docs
            k_bm: Number of BM25 docs
            db_jd: Vector database
            k_jd: Number of vector docs
            extraction_schema: JSON schema for extraction
            search_template: Template for online search queries
            extraction_model: Model for extraction
            search_model: Model for online search
            combine_model: Model for final combination

        Returns:
            Tuple of (extracted_info, online_results, final_answer)
        """
        logger.info("="*60)
        logger.info("STARTING SEQUENTIAL ANALYSIS PIPELINE")
        logger.info("="*60)

        # Stage 1: Extract from internal docs
        extracted_info = self.extract_structured_info(
            question=question,
            bm25_retriever=bm25_retriever,
            k_bm=k_bm,
            db_jd=db_jd,
            k_jd=k_jd,
            extraction_model=extraction_model,
            extraction_schema=extraction_schema
        )

        # Stage 2: Search online with extracted info
        online_results = self.search_online_with_extracted_info(
            extracted_info=extracted_info,
            search_template=search_template,
            search_model=search_model
        )

        # Stage 3: Combine results
        final_answer = self.combine_results(
            question=f"Based on the extracted info, {question}",
            extracted_info=extracted_info,
            online_results=online_results,
            combine_model=combine_model
        )

        logger.info("="*60)
        logger.info("SEQUENTIAL ANALYSIS COMPLETE")
        logger.info("="*60)

        return extracted_info, online_results, final_answer


# Example usage
def example_competitor_analysis():
    """
    Example: Find competitors for PPInnova's assets
    """
    from document_search import DocumentSearchSystem

    # Initialize system
    search_system = DocumentSearchSystem(enable_logging=True)
    pipeline = SequentialAnalysisPipeline(search_system)

    # Define extraction schema for PPInnova assets
    extraction_schema = {
        "company_name": "string",
        "assets": [
            {
                "asset_name": "string",
                "indication": "string or list",
                "target": "string",
                "modality": "string",
                "development_stage": "string"
            }
        ]
    }

    # Stage 1: Extract PPInnova's assets from internal docs
    extraction_question = """
    Extract structured information about PPInnova's drug pipeline.
    For each asset, include: asset name, indication(s), target, modality, and development stage.
    Return ONLY a JSON object.
    """

    # Stage 2: Search online for competitors (template)
    search_template = (
        "Find biotech companies with drug programs targeting {target} "
        "for {indication}. Include company names, asset names, development stages, "
        "and any funding/valuation information."
    )

    # Run pipeline (uncomment when you have the data loaded)
    # extracted_info, online_results, final_answer = pipeline.run_sequential_analysis(
    #     question=extraction_question,
    #     bm25_retriever=bm25_retriever,
    #     k_bm=50,
    #     db_jd=db_jd,
    #     k_jd=50,
    #     extraction_schema=extraction_schema,
    #     search_template=search_template,
    #     extraction_model="gpt-5-pro",
    #     search_model="o4-mini",
    #     combine_model="gpt-5-pro"
    # )
    #
    # print("\n" + "="*60)
    # print("EXTRACTED INFO FROM INTERNAL DOCS:")
    # print("="*60)
    # print(json.dumps(extracted_info, indent=2))
    #
    # print("\n" + "="*60)
    # print("ONLINE SEARCH RESULTS:")
    # print("="*60)
    # for result in online_results:
    #     print(f"\nQuery: {result['query']}")
    #     print(f"Result: {result['result'][:200]}...")
    #
    # print("\n" + "="*60)
    # print("FINAL COMBINED ANSWER:")
    # print("="*60)
    # print(final_answer)

    print("Example configuration ready. Uncomment code when data is loaded.")


if __name__ == "__main__":
    example_competitor_analysis()
