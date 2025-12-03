# Smart Search Mode - Quick Start Guide

## Overview

We've added a new **Smart Search Mode** that automatically analyzes your query and determines the best search strategy. Your existing search modes continue to work exactly as before!

## What's New?

### Smart Mode Features
- ✅ **Automatic Query Analysis**: Uses gpt-5.1 to understand your question
- ✅ **Intelligent Planning**: Determines what to extract and search for
- ✅ **Multi-Step Workflows**: Extract from docs → Search online → Combine results
- ✅ **No Configuration Needed**: Just ask your question!

### What Stays the Same
- ✅ **All existing search modes work unchanged**
- ✅ **Same models you're already using** (gpt-4.1, o4-mini, gpt-5-pro, o3, etc.)
- ✅ **Same parameters** (k_bm, k_jd, priority_order)
- ✅ **Same API and functions**

## Quick Start

### Option 1: Use Existing Search Modes (Unchanged!)

```python
from document_search import DocumentSearchSystem

search_system = DocumentSearchSystem(enable_logging=True)

# Mode: Internal docs only
result, _ = search_system.answer_with_search_ensemble(
    question="What is PPInnova's pipeline?",
    bm25_retriever=bm25_retriever,
    k_bm=50,
    db_jd=db_jd,
    k_jd=50,
    search_model="gpt-4.1",
    priority_order=["jarvis_docs"]
)

# Mode: Online search only
result, _ = search_system.answer_with_search_ensemble(
    question="Who are PPInnova's competitors?",
    bm25_retriever=bm25_retriever,
    k_bm=50,
    db_jd=db_jd,
    k_jd=50,
    search_model="o4-mini",
    priority_order=["online_search"]
)

# Mode: Both sources (you control priority)
result, _ = search_system.answer_with_search_ensemble(
    question="Market size for atopic dermatitis?",
    bm25_retriever=bm25_retriever,
    k_bm=50,
    db_jd=db_jd,
    k_jd=50,
    search_model="gpt-5-pro",
    priority_order=["jarvis_docs", "online_search"]
)
```

**All of these continue to work exactly as before!**

### Option 2: Use New Smart Mode (Automatic!)

```python
from document_search import DocumentSearchSystem

search_system = DocumentSearchSystem(enable_logging=True)

# Smart mode - automatically figures out what to do!
results = search_system.answer_with_smart_pipeline(
    question="Who are PPInnova's main competitors?",
    bm25_retriever=bm25_retriever,
    db_jd=db_jd,
    planning_model="gpt-5.1"  # Default, can change
)

# Get the answer
print(results["final_answer"])

# Optional: See what the system decided to do
print(f"Detected query type: {results['plan']['query_type']}")
```

## When to Use Each Mode

| Scenario | Recommended Mode | Why |
|----------|-----------------|-----|
| **Internal docs lookup** | Existing: `priority_order=["jarvis_docs"]` | Fastest, direct access |
| **Latest news/data** | Existing: `priority_order=["online_search"]` | Fastest for online info |
| **Known pattern** | Existing with your preferred settings | Full control, optimized |
| **Competitor analysis** | Smart mode ✨ | Extracts assets → Searches competitors |
| **Follow-up questions** | Smart mode ✨ | Extracts topics → Generates questions |
| **Market assessment** | Smart mode ✨ | Multi-dimensional analysis |
| **New query type** | Smart mode ✨ | Adapts automatically |

## Examples

### Example 1: Competitor Analysis (Smart Mode)

```python
results = search_system.answer_with_smart_pipeline(
    question="Who are PPInnova's competitors?",
    bm25_retriever=bm25_retriever,
    db_jd=db_jd,
    planning_model="gpt-5.1"
)

# The system automatically:
# 1. Extracts PPInnova's assets from internal docs
# 2. Searches online for competitors with same targets
# 3. Combines results into comprehensive answer

print(results["final_answer"])
```

### Example 2: KOL Follow-up Questions (Smart Mode)

```python
call_notes = """
Dr. Smith discussed Phase 2 results. Concerns about dosing.
Did not explore combination therapy.
"""

results = search_system.answer_with_smart_pipeline(
    question=f"Generate follow-up questions from: {call_notes}",
    bm25_retriever=bm25_retriever,
    db_jd=db_jd,
    planning_model="gpt-5.1"
)

# The system automatically:
# 1. Extracts topics, insights, concerns from notes
# 2. Generates thoughtful follow-up questions
# 3. Creates comprehensive follow-up report

print(results["final_answer"])
```

### Example 3: Simple Lookup (Existing Mode - Faster!)

```python
# For simple lookups, existing mode is faster
result, _ = search_system.answer_with_search_ensemble(
    question="What is the company's funding history?",
    bm25_retriever=bm25_retriever,
    k_bm=50,
    db_jd=db_jd,
    k_jd=50,
    search_model="gpt-4.1",
    priority_order=["jarvis_docs"]
)

print(result)
```

## Supported Models

Both modes support all the same models:

### For Planning (Smart mode only)
- **gpt-5.1** (default, 400k context) - Best reasoning
- **gpt-5-pro** (400k context) - Alternative
- **gpt-4o** (128k context) - Faster option

### For Search & Answer (Both modes)
- **gpt-5.1** (400k context)
- **gpt-5-pro** (400k context)
- **gpt-4.1** (128k context)
- **o4-mini** (128k context)
- **o3** (128k context)
- **gpt-4o** (128k context)
- And all other existing models...

## Performance

### Existing Modes
- ⚡ Latency: 5-15 seconds
- 💰 Cost: $0.005-0.02 per query
- ✅ Best for: Direct lookups, known patterns

### Smart Mode
- ⚡ Latency: 10-30 seconds (includes planning)
- 💰 Cost: $0.01-0.04 per query (includes planning overhead)
- ✅ Best for: Complex analysis, multi-step workflows

## Migration Notes

### ✅ No Migration Needed!

All your existing code continues to work:

```python
# This still works exactly as before
result, online_response = answer_with_search_ensemble(
    question, bm25_retriever, k_bm, db_jd, k_jd,
    search_model="o4-mini",
    priority_order=['online_search', 'jarvis_docs']
)
```

### ⭐ Try Smart Mode When Ready

When you want to try the new smart mode:

```python
# New smart mode (optional)
results = search_system.answer_with_smart_pipeline(
    question=question,
    bm25_retriever=bm25_retriever,
    db_jd=db_jd,
    planning_model="gpt-5.1"
)
answer = results["final_answer"]
```

## Troubleshooting

### Q: Will this break my existing code?
**A:** No! All existing functions work unchanged. Smart mode is a new optional feature.

### Q: Can I still use my existing models?
**A:** Yes! All models (gpt-4.1, o4-mini, gpt-5-pro, o3, etc.) work with both modes.

### Q: What if I don't want to use smart mode?
**A:** No problem! Just keep using `answer_with_search_ensemble()` as before.

### Q: Is smart mode slower?
**A:** Yes, by 5-10 seconds due to the planning step. Use existing modes for speed.

### Q: Which mode should I use?
**A:**
- **Simple lookups** → Existing mode (faster)
- **Known patterns** → Existing mode (full control)
- **Complex analysis** → Smart mode (automatic)
- **New query types** → Smart mode (adapts)

## Summary

✅ **Existing modes** continue to work exactly as before
✅ **New smart mode** available when you need automatic query analysis
✅ **Same models** work with both modes
✅ **No breaking changes** to your current code
✅ **Try it when ready** - completely optional!

For detailed examples, see `smart_search_examples.py`.

For technical details, see `SMART_PIPELINE_GUIDE.md`.
