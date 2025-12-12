"""
Example usage of the Sequential Analysis feature for AI Document Search

This script demonstrates how to use the sequential_analysis mode for different use cases.
"""

import requests
import json
from typing import Dict, Any

# API Configuration
API_BASE_URL = "http://localhost:8000/api"


def search_with_sequential_analysis(
    query: str,
    reasoning_mode: str = "non_reasoning",
    top_k: int = 10,
    conversation_history: list = None
) -> Dict[str, Any]:
    """
    Perform a search using sequential_analysis mode

    Args:
        query: The user's question
        reasoning_mode: "non_reasoning", "reasoning", "reasoning_gpt5", or "deep_research"
        top_k: Number of document chunks to retrieve
        conversation_history: Optional previous conversation context

    Returns:
        Dictionary with the search response
    """
    payload = {
        "query": query,
        "search_mode": "sequential_analysis",
        "reasoning_mode": reasoning_mode,
        "top_k": top_k
    }

    if conversation_history:
        payload["conversation_history"] = conversation_history

    response = requests.post(f"{API_BASE_URL}/search", json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")


def print_response(response: Dict[str, Any], show_details: bool = True):
    """Pretty print the response"""
    print("\n" + "="*80)
    print("QUERY:", response.get("query"))
    print("="*80)

    if response.get("selected_mode"):
        print(f"\n🔍 Selected Mode: {response['selected_mode']}")

    print("\n📊 FINAL ANSWER:")
    print("-"*80)
    print(response.get("answer", "No answer generated"))

    if show_details:
        if response.get("extracted_info"):
            print("\n📄 EXTRACTED FROM DOCUMENTS (Step 1):")
            print("-"*80)
            print(response["extracted_info"])

        if response.get("online_search_response"):
            print("\n🌐 ONLINE SEARCH RESULTS (Step 2):")
            print("-"*80)
            print(response["online_search_response"][:500] + "..." if len(response["online_search_response"]) > 500 else response["online_search_response"])

        print(f"\n⏱️  Processing Time: {response.get('processing_time', 0):.1f}s")
        print(f"📈 Documents Retrieved: {response.get('total_results', 0)}")

    print("="*80 + "\n")


# =============================================================================
# Example 1: Competitive Analysis
# =============================================================================
def example_competitive_analysis():
    """
    Use Case: Finding competitors based on your company's assets
    Pattern: competitive_analysis
    """
    print("\n" + "🔬 EXAMPLE 1: COMPETITIVE ANALYSIS")
    print("="*80)

    query = "What are the competitors of PPInnova?"

    print(f"Query: {query}")
    print("\nExpected behavior:")
    print("  Step 0: Analyze query → Identify as competitive_analysis")
    print("  Step 1: Extract PPInnova's assets, indications, and targets from documents")
    print("  Step 2: Search online for companies with assets in same indication/target")
    print("  Step 3: Synthesize into competitor analysis")

    try:
        response = search_with_sequential_analysis(query)
        print_response(response)
    except Exception as e:
        print(f"❌ Error: {e}")


# =============================================================================
# Example 2: Follow-up Questions
# =============================================================================
def example_follow_up_questions():
    """
    Use Case: Generating follow-up questions from meeting notes
    Pattern: follow_up_questions
    """
    print("\n" + "💬 EXAMPLE 2: FOLLOW-UP QUESTIONS")
    print("="*80)

    query = "Based on the KOL call notes, what follow-up questions should we ask besides the ones already discussed?"

    print(f"Query: {query}")
    print("\nExpected behavior:")
    print("  Step 0: Analyze query → Identify as follow_up_questions")
    print("  Step 1: Extract existing questions, topics, and KOL responses from documents")
    print("  Step 2: Search online for KOL engagement best practices and recent developments")
    print("  Step 3: Generate thoughtful, non-redundant follow-up questions")

    try:
        response = search_with_sequential_analysis(query)
        print_response(response)
    except Exception as e:
        print(f"❌ Error: {e}")


# =============================================================================
# Example 3: Benchmarking
# =============================================================================
def example_benchmarking():
    """
    Use Case: Comparing your product's performance to industry standards
    Pattern: benchmarking
    """
    print("\n" + "📊 EXAMPLE 3: BENCHMARKING")
    print("="*80)

    query = "How does our lead drug's Phase 2 efficacy compare to industry standards and competitors?"

    print(f"Query: {query}")
    print("\nExpected behavior:")
    print("  Step 0: Analyze query → Identify as benchmarking")
    print("  Step 1: Extract our drug's efficacy metrics, endpoints, and study design")
    print("  Step 2: Search online for industry benchmarks and competitor Phase 2 results")
    print("  Step 3: Provide detailed comparative analysis")

    try:
        response = search_with_sequential_analysis(query, reasoning_mode="reasoning")
        print_response(response)
    except Exception as e:
        print(f"❌ Error: {e}")


# =============================================================================
# Example 4: Market Intelligence
# =============================================================================
def example_market_intelligence():
    """
    Use Case: Identifying partnership opportunities based on your pipeline
    Pattern: market_intelligence
    """
    print("\n" + "🤝 EXAMPLE 4: MARKET INTELLIGENCE")
    print("="*80)

    query = "What partnerships or collaborations should we explore based on our pipeline?"

    print(f"Query: {query}")
    print("\nExpected behavior:")
    print("  Step 0: Analyze query → Identify as market_intelligence")
    print("  Step 1: Extract pipeline assets, stages, therapeutic areas, and capabilities")
    print("  Step 2: Search online for complementary partners and recent deals")
    print("  Step 3: Identify strategic partnership opportunities")

    try:
        response = search_with_sequential_analysis(query)
        print_response(response)
    except Exception as e:
        print(f"❌ Error: {e}")


# =============================================================================
# Example 5: Multi-turn Conversation
# =============================================================================
def example_conversation():
    """
    Use Case: Multi-turn conversation with context
    Demonstrates how conversation history enhances sequential analysis
    """
    print("\n" + "💭 EXAMPLE 5: MULTI-TURN CONVERSATION")
    print("="*80)

    # First query
    query1 = "What are the main assets in our pipeline?"
    print(f"\nQuery 1: {query1}")

    try:
        response1 = search_with_sequential_analysis(query1)
        print_response(response1, show_details=False)

        # Build conversation history
        conversation_history = [{
            "query": query1,
            "answer": response1.get("answer", "")
        }]

        # Follow-up query using context
        query2 = "Which of these assets have the most promising competitors?"
        print(f"\nQuery 2 (with context): {query2}")

        response2 = search_with_sequential_analysis(
            query2,
            conversation_history=conversation_history
        )
        print_response(response2)

    except Exception as e:
        print(f"❌ Error: {e}")


# =============================================================================
# Example 6: Comparing Reasoning Modes
# =============================================================================
def example_reasoning_modes():
    """
    Use Case: Comparing different reasoning modes
    Shows how to use different LLM models for different query complexities
    """
    print("\n" + "🧠 EXAMPLE 6: REASONING MODES COMPARISON")
    print("="*80)

    query = "Analyze our competitive position in the oncology space based on our pipeline documents"

    reasoning_modes = [
        ("non_reasoning", "Fast mode with GPT-4.1"),
        ("reasoning", "Advanced reasoning with o4-mini"),
    ]

    for mode, description in reasoning_modes:
        print(f"\n{'='*80}")
        print(f"Testing with: {mode} - {description}")
        print('='*80)

        try:
            response = search_with_sequential_analysis(query, reasoning_mode=mode)
            print(f"⏱️  Processing Time: {response.get('processing_time', 0):.1f}s")
            print(f"\nAnswer Preview: {response.get('answer', '')[:300]}...")
        except Exception as e:
            print(f"❌ Error: {e}")


# =============================================================================
# Main execution
# =============================================================================
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║              SEQUENTIAL ANALYSIS - EXAMPLE USAGE GUIDE                   ║
    ║                                                                          ║
    ║  This script demonstrates the Sequential Analysis feature which:        ║
    ║  1. Analyzes your query to determine extraction requirements            ║
    ║  2. Extracts specific information from your documents                   ║
    ║  3. Uses extracted info to perform targeted online searches             ║
    ║  4. Synthesizes everything into a comprehensive answer                  ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)

    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        examples = {
            "1": example_competitive_analysis,
            "2": example_follow_up_questions,
            "3": example_benchmarking,
            "4": example_market_intelligence,
            "5": example_conversation,
            "6": example_reasoning_modes,
        }

        if example_num in examples:
            examples[example_num]()
        else:
            print(f"❌ Invalid example number. Choose 1-6.")
            sys.exit(1)
    else:
        print("Usage: python sequential_analysis_examples.py [example_number]")
        print("\nAvailable examples:")
        print("  1 - Competitive Analysis (PPInnova competitors)")
        print("  2 - Follow-up Questions (KOL call notes)")
        print("  3 - Benchmarking (Efficacy comparison)")
        print("  4 - Market Intelligence (Partnership opportunities)")
        print("  5 - Multi-turn Conversation (Context-aware queries)")
        print("  6 - Reasoning Modes Comparison")
        print("\nOr run all examples:")

        run_all = input("\nRun all examples? (y/n): ").strip().lower()
        if run_all == 'y':
            example_competitive_analysis()
            example_follow_up_questions()
            example_benchmarking()
            example_market_intelligence()
            example_conversation()
            example_reasoning_modes()
        else:
            print("Exiting. Run with an example number (1-6) to see specific examples.")
