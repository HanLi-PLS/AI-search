# Sequential Analysis - Advanced Document Search

## Overview

The Sequential Analysis feature provides a systematic, multi-step approach to answering complex queries that require:
1. First extracting specific information from your uploaded documents
2. Then using that extracted information to search online for comparative, competitive, or supplementary data

This is particularly useful for queries where you need to know what's in your documents before you can effectively search online.

## How It Works

### Architecture

The sequential analysis mode uses a **4-step process**:

```
Step 0: Query Analysis (NEW)
    ↓
    Analyzes the user's query using few-shot prompting
    Determines what information needs to be extracted from documents
    Identifies the use case pattern and online search strategy

Step 1: Guided Information Extraction
    ↓
    Extracts specific information from documents based on Step 0's analysis
    Uses structured extraction guided by the query analysis

Step 2: Guided Online Search
    ↓
    Performs online search using the extracted information
    Follows the search strategy determined in Step 0

Step 3: Synthesis
    ↓
    Combines extracted document data and online search results
    Provides comprehensive answer structured by use case type
```

### Use Case Patterns

The system recognizes and handles multiple use case patterns:

#### 1. **Competitive Analysis**
Extract your company's products/assets, then search for competitors with similar offerings.

**Example Query:**
> "What are the competitors of PPInnova?"

**What it does:**
- Extracts PPInnova's assets (drug names, compounds)
- Extracts indications and targets for each asset
- Searches online for companies with assets targeting the same indications/targets
- Returns competitive landscape analysis

#### 2. **Follow-up Questions**
Extract existing questions from documents, then generate thoughtful follow-up questions.

**Example Query:**
> "Based on this KOL call note, what follow-up questions should we ask besides the ones already discussed?"

**What it does:**
- Extracts all questions already asked in the document
- Extracts key topics and KOL responses
- Searches online for best practices in KOL engagement
- Generates non-redundant, contextually relevant follow-up questions

#### 3. **Benchmarking**
Extract your metrics from documents, then search for industry standards or competitor data.

**Example Query:**
> "How does our drug's efficacy compare to industry standards?"

**What it does:**
- Extracts your product's efficacy metrics from documents
- Extracts study design and patient population details
- Searches online for industry benchmarks and competitor results
- Provides comparative analysis

#### 4. **Market Intelligence**
Extract your pipeline/capabilities from documents, then search for partnership or market opportunities.

**Example Query:**
> "What partnerships should we explore based on our pipeline?"

**What it does:**
- Extracts pipeline assets and development stages
- Extracts therapeutic areas and capabilities
- Searches online for complementary partners and recent deals
- Identifies strategic opportunities

#### 5. **Custom Use Cases**
The system can handle other patterns dynamically using the same framework.

## Usage

### API Request

```json
POST /api/search

{
  "query": "What are the competitors of PPInnova?",
  "search_mode": "sequential_analysis",
  "reasoning_mode": "non_reasoning",
  "top_k": 10
}
```

### Search Modes

- `files_only` - Search only in uploaded documents
- `online_only` - Search only online
- `both` - Search files and online in parallel
- `sequential_analysis` - **Use this for the advanced sequential workflow**
- `auto` - Let the AI classify and choose the best mode

### Reasoning Modes

- `non_reasoning` - Fast, uses GPT-4.1 (default)
- `reasoning` - More thorough, uses o4-mini
- `reasoning_gpt5` - Advanced reasoning, uses GPT-5-pro
- `deep_research` - Comprehensive research, uses o3-deep-research

### Response Structure

```json
{
  "success": true,
  "query": "What are the competitors of PPInnova?",
  "answer": "Comprehensive answer synthesizing document and online data...",
  "extracted_info": "Information extracted from documents in Step 1...",
  "online_search_response": "Results from online search in Step 2...",
  "selected_mode": "sequential_analysis",
  "results": [...],
  "processing_time": 15.3
}
```

## Key Features

### 1. **Dynamic Query Analysis**
- Uses GPT-5.1 to intelligently analyze each query
- Adapts extraction strategy to the specific question
- No hardcoded extraction patterns

### 2. **Few-Shot Learning**
- Includes multiple example use cases in the prompt
- Helps the AI understand different query patterns
- Guides extraction and search strategies

### 3. **Structured Extraction**
- Extracts only what's needed for the query
- Organizes extracted data clearly
- Explicitly notes missing information

### 4. **Guided Online Search**
- Online search is informed by extracted document data
- More targeted and relevant results
- Avoids generic searches that miss the context

### 5. **Use Case-Aware Synthesis**
- Final answer is structured based on the use case type
- Competitive analysis emphasizes competitors
- Follow-up questions focus on generating questions
- Benchmarking highlights comparisons

### 6. **Comprehensive Logging**
- Detailed performance metrics for each step
- Clear indication of use case type detected
- Easy debugging and monitoring

## Performance

Typical processing time for sequential analysis:
- **Step 0 (Query Analysis):** 2-4 seconds
- **Step 1 (Extraction):** 3-8 seconds
- **Step 2 (Online Search):** 5-15 seconds (varies by search complexity)
- **Step 3 (Synthesis):** 3-8 seconds
- **Total:** 15-35 seconds (depending on complexity)

## When to Use Sequential Analysis

**✅ Use sequential_analysis when:**
- You need to compare your data with external/competitor data
- The online search should be guided by specific information in your documents
- You're asking about competitors, benchmarks, or comparative analysis
- You need to extract structured information first, then use it for further research

**❌ Don't use sequential_analysis when:**
- You only need information from your documents (use `files_only`)
- You only need online/current information (use `online_only`)
- Document and online data can be retrieved independently (use `both`)
- Simple factual queries that don't require multi-step reasoning

## Examples

### Example 1: Competitor Analysis

**Query:**
```
"What are the competitors of our lead asset mentioned in the pipeline document?"
```

**Process:**
1. **Analysis:** Identifies this as competitive_analysis
2. **Extraction:** Extracts lead asset name, indication, target, stage
3. **Online Search:** Searches for companies with assets in same indication/target
4. **Synthesis:** Lists competitors with details about their competing assets

### Example 2: KOL Follow-up

**Query:**
```
"Based on the KOL call notes with Dr. Smith, what additional questions should we ask in the follow-up meeting?"
```

**Process:**
1. **Analysis:** Identifies this as follow_up_questions
2. **Extraction:** Extracts existing questions, topics discussed, KOL responses, gaps
3. **Online Search:** Searches for KOL engagement best practices, recent developments
4. **Synthesis:** Provides 5-10 thoughtful follow-up questions with rationale

### Example 3: Efficacy Benchmarking

**Query:**
```
"How does our Phase 2 efficacy data compare to competitors in the same indication?"
```

**Process:**
1. **Analysis:** Identifies this as benchmarking
2. **Extraction:** Extracts our efficacy metrics, endpoints, patient population
3. **Online Search:** Searches for competitor Phase 2 results in same indication
4. **Synthesis:** Provides detailed comparison table and analysis

## Configuration

The sequential analysis feature uses these models (configurable in `backend/app/config.py`):

```python
# Query Analysis (Step 0)
QUERY_ANALYSIS_MODEL = "gpt-5.1"

# Extraction and Synthesis (Steps 1 & 3)
ANSWER_MODEL = "gpt-4.1"

# Online Search (Step 2)
ONLINE_SEARCH_MODEL = "o4-mini"  # Can be overridden by reasoning_mode
```

## Error Handling

If any step fails, the system:
- Logs detailed error information
- Returns what was successfully completed
- Provides fallback extraction plan if query analysis fails
- Continues with available data even if online search fails

## Extending the System

To add new use case patterns:

1. Add example to the few-shot prompt in `analyze_query_for_extraction()`
2. Include the use case type in the JSON schema
3. Update the synthesis prompt in Step 3 to handle the new pattern
4. Test with representative queries

## Technical Details

**Implementation:** `/backend/app/core/answer_generator.py`

**Key Methods:**
- `analyze_query_for_extraction()` - Step 0: Query analysis with few-shot prompting
- `generate_answer()` - Main orchestrator, handles all search modes including sequential_analysis

**Dependencies:**
- OpenAI API (GPT-4.1, GPT-5.1, o4-mini)
- Vector store (Qdrant) for document search
- Web search tool for online search

## Limitations

1. **Processing Time:** Sequential analysis takes longer (15-35s) than other modes
2. **API Costs:** Makes multiple LLM calls, higher cost per query
3. **Document Quality:** Extraction quality depends on document clarity and completeness
4. **Online Search Scope:** Limited by what's publicly available online

## Future Enhancements

Potential improvements for future versions:
- Cache query analysis results for similar queries
- Parallel execution where possible (e.g., multiple online searches)
- User-defined use case templates
- Feedback loop to improve extraction patterns
- Support for iterative refinement (multi-turn extraction)
