# Smart Search Mode - Usage Examples

"""
This file shows how to use the new SmartPipeline mode alongside existing search modes.

The SmartPipeline automatically analyzes your query and determines:
1. What information to extract from internal documents
2. What to search for online
3. How to combine the results

It uses gpt-5.1 by default for query analysis.
"""

from document_search import DocumentSearchSystem

# ============================================================================
# SETUP (Same as before)
# ============================================================================

# Initialize the search system
search_system = DocumentSearchSystem(enable_logging=True)

# Assume you have already loaded:
# - bm25_retriever (from BM25Retriever.from_documents)
# - db_jd (ChromaDB vector database)

# ============================================================================
# EXISTING SEARCH MODES (Still work exactly the same!)
# ============================================================================

# Mode 1: Internal docs only
result, online_response = search_system.answer_with_search_ensemble(
    question="What is PPInnova's pipeline?",
    bm25_retriever=bm25_retriever,
    k_bm=50,
    db_jd=db_jd,
    k_jd=50,
    search_model="gpt-4.1",
    priority_order=["jarvis_docs"]  # Only internal docs
)
print(result)

# Mode 2: Online search only
result, online_response = search_system.answer_with_search_ensemble(
    question="Who are PPInnova's competitors?",
    bm25_retriever=bm25_retriever,
    k_bm=50,
    db_jd=db_jd,
    k_jd=50,
    search_model="o4-mini",
    priority_order=["online_search"]  # Only online search
)
print(result)

# Mode 3: Both sources (internal docs priority)
result, online_response = search_system.answer_with_search_ensemble(
    question="What is the market size for atopic dermatitis?",
    bm25_retriever=bm25_retriever,
    k_bm=50,
    db_jd=db_jd,
    k_jd=50,
    search_model="gpt-5-pro",
    priority_order=["jarvis_docs", "online_search"]  # Internal first, then online
)
print(result)

# Mode 4: Both sources (online priority)
result, online_response = search_system.answer_with_search_ensemble(
    question="Recent funding rounds in biotech",
    bm25_retriever=bm25_retriever,
    k_bm=50,
    db_jd=db_jd,
    k_jd=50,
    search_model="o4-mini",
    priority_order=["online_search", "jarvis_docs"]  # Online first, then internal
)
print(result)

# ============================================================================
# NEW: SMART MODE (Automatic query analysis and planning)
# ============================================================================

# The SmartPipeline automatically figures out what to do based on your query!

# Example 1: Competitor Analysis (automatically detected)
results = search_system.answer_with_smart_pipeline(
    question="Who are PPInnova's main competitors?",
    bm25_retriever=bm25_retriever,
    db_jd=db_jd,
    planning_model="gpt-5.1"  # Uses gpt-5.1 to analyze the query
)

print("=" * 70)
print("SMART MODE RESULTS")
print("=" * 70)
print(f"Query Type Detected: {results['plan']['query_type']}")
print(f"\nFinal Answer:\n{results['final_answer']}")

# Optional: Inspect the plan
print(f"\nGenerated Plan:")
print(f"- Extraction needed: {results['plan']['extraction_needed']}")
print(f"- Fields to extract: {results['plan'].get('extraction_fields', [])}")

# Example 2: KOL Follow-up Questions (automatically detected)
call_notes = """
Dr. Smith discussed our Phase 2 results for the STAT6 degrader.
Positive feedback on efficacy, but raised concerns about dosing schedule.
Did not fully explore combination therapy potential.
"""

results = search_system.answer_with_smart_pipeline(
    question=f"Generate follow-up questions from this KOL call: {call_notes}",
    bm25_retriever=bm25_retriever,
    db_jd=db_jd,
    planning_model="gpt-5.1"
)

print("\n" + "=" * 70)
print("KOL FOLLOW-UP - SMART MODE")
print("=" * 70)
print(f"Query Type: {results['plan']['query_type']}")
print(f"\n{results['final_answer']}")

# Example 3: Market Assessment (automatically detected)
results = search_system.answer_with_smart_pipeline(
    question="What's the market opportunity for our atopic dermatitis program?",
    bm25_retriever=bm25_retriever,
    db_jd=db_jd,
    planning_model="gpt-5.1"
)

print("\n" + "=" * 70)
print("MARKET ASSESSMENT - SMART MODE")
print("=" * 70)
print(results['final_answer'])

# Example 4: Any other query type (system adapts automatically)
results = search_system.answer_with_smart_pipeline(
    question="What are the key risks for investing in this company?",
    bm25_retriever=bm25_retriever,
    db_jd=db_jd,
    planning_model="gpt-5.1"
)

print("\n" + "=" * 70)
print("CUSTOM QUERY - SMART MODE")
print("=" * 70)
print(results['final_answer'])

# ============================================================================
# WHEN TO USE EACH MODE
# ============================================================================

"""
Use EXISTING MODES when:
- You know exactly which sources to use (internal vs online)
- Running repeated queries with same pattern
- Need maximum control over the process
- Want fastest performance (no planning overhead)

Use SMART MODE when:
- Exploring different types of questions
- Not sure which sources/approach to use
- Want comprehensive multi-step analysis
- Query requires extract → search → combine workflow
- Trying new query patterns

Examples:
- "What's in our internal docs?" → Use existing mode: priority_order=["jarvis_docs"]
- "Latest news online?" → Use existing mode: priority_order=["online_search"]
- "Who are our competitors?" → Use SMART mode (extracts company data, searches competitors)
- "Generate follow-up questions" → Use SMART mode (extracts topics, generates questions)
- "Market analysis?" → Use SMART mode (multi-dimensional research)
"""

# ============================================================================
# PERFORMANCE COMPARISON
# ============================================================================

"""
EXISTING MODES:
- Latency: 5-15 seconds (direct search + answer)
- Cost: $0.005-0.02 per query
- Best for: Known patterns, repeated queries

SMART MODE:
- Latency: 10-30 seconds (includes planning stage)
- Cost: $0.01-0.04 per query (includes planning)
- Best for: Complex analysis, exploration, new query types
"""

# ============================================================================
# AVAILABLE MODELS
# ============================================================================

"""
All these models work with both existing and smart modes:

Planning (for Smart mode only):
- gpt-5.1 (default, 400k context) - Best reasoning
- gpt-5-pro (400k context) - Alternative
- gpt-4o (128k context) - Faster

Search & Answer (for both modes):
- gpt-5.1 (400k context) - Best for complex reasoning
- gpt-5-pro (400k context) - Strong reasoning
- o4-mini (128k context) - Fast and cost-effective
- gpt-4.1 (128k context) - Balanced
- o3 (128k context) - Advanced
- gpt-4o (128k context) - Fast
"""
