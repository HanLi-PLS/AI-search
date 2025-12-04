# Conversation Memory Analysis - All Search Modes

## Summary: ✅ Memory is Properly Configured

Conversation memory is **correctly implemented** across all search modes. The system only stores and uses **questions and answers**, NOT raw file chunks or source documents.

---

## How Conversation Memory Works

### 1. Frontend: Data Storage vs API Transmission

**What's Stored Locally** (for UI display):
```javascript
const newTurn = {
  query: queryText,
  answer: result.answer,
  extracted_info: result.extracted_info,        // ← NOT sent to API
  online_search_response: result.online_search_response,  // ← NOT sent to API
  results: result.results,                      // ← NOT sent to API (raw chunks!)
  search_params: { ... }                        // ← NOT sent to API
};
```

**What's Sent to API** (for memory context):
```javascript
// Lines 551-556 in AISearch.jsx
const conversationHistoryForAPI = conversationHistory.map(turn => ({
  query: turn.query,      // ✅ Only question
  answer: turn.answer     // ✅ Only final answer
}));
```

**Comment in Code**:
```javascript
// Only send query and answer in conversation history (not results/sources)
// to avoid bloating the API request with source chunks
```

---

### 2. Backend: API Schema Validation

**Schema Definition** (`backend/app/models/schemas.py` lines 55-58):
```python
class ConversationTurn(BaseModel):
    """Single turn in conversation history"""
    query: str = Field(..., description="User's query")
    answer: str = Field(..., description="AI's answer")
```

**What This Means**:
- The API will **reject** any conversation history that includes extra fields like `results`, `extracted_info`, etc.
- Only `query` and `answer` are accepted ✅

---

### 3. Backend: Memory Formatting

**Method: `format_conversation_history()`** (lines 343-363):
```python
def format_conversation_history(self, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
    if not conversation_history or len(conversation_history) == 0:
        return ""

    formatted = "\n**Previous Conversation**:\n"
    for i, turn in enumerate(conversation_history[-5:], 1):  # Last 5 turns only
        formatted += f"\nTurn {i}:\n"
        formatted += f"User: {turn.get('query', '')}\n"
        formatted += f"Assistant: {turn.get('answer', '')[:500]}...\n"  # Truncate to 500 chars

    formatted += "\n**Current Question** (use the context above to understand references like 'it', 'that', 'them'):\n"
    return formatted
```

**Key Features**:
- ✅ Only uses `query` and `answer` from each turn
- ✅ Limits to last 5 turns (to avoid token limits)
- ✅ Truncates long answers to 500 characters
- ✅ Does NOT include results, sources, or raw chunks
- ✅ Provides context instruction for follow-up questions

---

## Memory Usage Across All Search Modes

### Mode 1: Files Only ✅

**Line 446** (`backend/app/core/answer_generator.py`):
```python
prompt = f"""You are an expert in bioventure investing.{conversation_context}

**Question**: {query}
**Knowledge Base**:
1. Files:
{context}
...
"""
```

- ✅ Uses `conversation_context` (formatted history)
- ✅ Only includes query + answer from previous turns
- ✅ Does NOT include previous file chunks in memory

---

### Mode 2: Online Only ✅ (FIXED in latest commit)

**Line 414** (`backend/app/core/answer_generator.py`):
```python
if search_mode == "online_only":
    online_search_response = self.answer_online_search(
        query,
        model=search_model,
        conversation_context=conversation_context  # ✅ Now includes memory
    )
```

**Line 327** (inside `answer_online_search`):
```python
# Build full prompt with conversation context
full_prompt = f"{conversation_context}{prompt}" if conversation_context else prompt
```

- ✅ Uses `conversation_context`
- ✅ Maintains memory of previous Q&A
- ✅ Was broken before (no memory), now fixed ✅

---

### Mode 3: Both (Files + Online) ✅

**Line 643** (online search part):
```python
if 'online_search' in priority_order:
    online_search_response = self.answer_online_search(
        query,
        model=search_model,
        conversation_context=conversation_context  # ✅ Has memory
    )
```

**Line 688** (final synthesis):
```python
prompt = f"""{conversation_context}  # ✅ Has memory

**Analysis Directive**: Answer using this priority sequence: {', '.join(priority_order).upper()}

**Knowledge Base**:
{joined_priority_context}
...
"""
```

- ✅ Both online search AND final synthesis use conversation_context
- ✅ Memory preserved throughout

---

### Mode 4: Sequential Analysis ✅

**Step 0 - Query Analysis** (Line 138):
```python
conversation_context = self.format_conversation_history(conversation_history)
analysis_prompt = f"""...{conversation_context}..."""
```

**Step 1 - Extraction** (Line 518):
```python
extraction_prompt = f"""You are an expert in bioventure investing.{conversation_context}
...
"""
```

**Step 2 - Online Search** (Line 578):
```python
online_search_response = self.answer_online_search(
    online_search_prompt,
    model=search_model,
    conversation_context=conversation_context  # ✅ Has memory
)
```

**Step 3 - Final Synthesis** (Line 586):
```python
final_prompt = f"""You are an expert in bioventure investing.{conversation_context}
...
"""
```

- ✅ ALL 4 steps use conversation_context
- ✅ Memory preserved throughout the entire sequential process

---

## What Gets Remembered vs What Doesn't

### ✅ What IS Remembered (Included in Memory)
- User's questions (query)
- AI's final answers (answer)
- Last 5 conversation turns
- Truncated to 500 characters per answer

### ❌ What is NOT Remembered (Excluded from Memory)
- Raw file chunks (`results`)
- Source document references
- Extracted information (`extracted_info`)
- Online search responses (`online_search_response`)
- Search parameters (`search_params`)
- File metadata

---

## Example: How Memory Works

### Conversation Flow:

**Turn 1:**
```
User: "What are the assets of PPInnova?"
AI: "PPInnova has the following assets: Drug A (Phase 2), Drug B (Phase 1)..."

Stored locally:
{
  query: "What are the assets of PPInnova?",
  answer: "PPInnova has the following assets...",
  results: [...1000s of characters of raw chunks...],  // NOT sent to API
  extracted_info: "...",                               // NOT sent to API
}

Sent to API for next turn:
{
  query: "What are the assets of PPInnova?",
  answer: "PPInnova has the following assets..."      // Only this!
}
```

**Turn 2:**
```
User: "What are the competitors for Drug A?"

API receives:
conversation_history: [
  {
    query: "What are the assets of PPInnova?",
    answer: "PPInnova has the following assets: Drug A (Phase 2)..."  // Truncated to 500 chars
  }
]

Formatted context sent to AI:
"
**Previous Conversation**:

Turn 1:
User: What are the assets of PPInnova?
Assistant: PPInnova has the following assets: Drug A (Phase 2), Drug B (Phase 1)...

**Current Question** (use the context above to understand references like 'it', 'that', 'them'):
What are the competitors for Drug A?
"
```

AI now knows:
- ✅ "Drug A" refers to PPInnova's asset
- ✅ Context from previous answer
- ❌ NOT burdened with raw file chunks from Turn 1

---

## Benefits of This Design

### 1. **Token Efficiency** 💰
- Only sends essential context (Q&A)
- Avoids sending thousands of tokens of raw chunks
- Truncates long answers to 500 chars
- Limits to last 5 turns

### 2. **Maintains Context** 🧠
- Understands follow-up questions
- Resolves references ("it", "that", "them")
- Knows what was discussed before

### 3. **Clean Separation** 🏗️
- UI stores full data for display
- API only receives clean Q&A for context
- No confusion between display data and memory data

### 4. **All Modes Consistent** ✅
- Every search mode uses the same memory format
- No mode-specific bugs or inconsistencies

---

## Testing Conversation Memory

### Test Case 1: Files Only
```
1. Upload a document about Company X
2. Ask: "What products does Company X have?"
   Expected: Lists products from document
3. Ask: "What's the revenue of the second product?"
   Expected: ✅ Should understand "second product" from previous answer
```

### Test Case 2: Online Only
```
1. Ask: "Who is the CEO of Pfizer?"
   Expected: "Albert Bourla"
2. Ask: "What's his background?"
   Expected: ✅ Should understand "his" = Albert Bourla
```

### Test Case 3: Sequential Analysis
```
1. Upload document with drug efficacy data
2. Ask: "Compare our drug efficacy with competitors"
   Expected: Extracts from doc, then searches online
3. Ask: "What about safety profile?"
   Expected: ✅ Should remember which drug we're discussing
```

### Test Case 4: Both Mode
```
1. Upload financial report
2. Ask: "What's our revenue and how does it compare to industry average?"
   Expected: Revenue from file, industry average from online
3. Ask: "Is that growth rate sustainable?"
   Expected: ✅ Should remember "that" = the growth rate mentioned before
```

---

## Verification Commands

### Check Frontend is Stripping Correctly:
```bash
# In browser console while searching:
# Look for the API request payload
# conversation_history should only have query + answer fields
```

### Check Backend is Receiving Correctly:
```bash
# Check backend logs:
tail -f /opt/ai-search/logs/backend-out.log | grep "conversation_history"
```

### Check Memory Formatting:
```bash
# Search for the formatted context in logs:
grep "Previous Conversation" /opt/ai-search/logs/backend-out.log
```

---

## Conclusion

✅ **All search modes properly maintain conversation memory**
✅ **Only questions and answers are stored, NOT raw chunks**
✅ **Token-efficient design (last 5 turns, 500 char limit per answer)**
✅ **Consistent across all modes: files_only, online_only, both, sequential_analysis**

The system is working as designed and optimized for both performance and user experience.
