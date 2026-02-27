"""
IC Cognitive Extractor — Multi-pass intelligence extraction from IC meeting notes.

Implements a 4-pass extraction pipeline that distills decision-making intelligence
from historical IC meetings into reusable cognitive artifacts:

  Pass 1: Structural Extraction — parse each meeting into structured records
  Pass 2: Reasoning Extraction — infer underlying cognitive drivers behind questions
  Pass 3: Cross-Meeting Synthesis — build committee-level cognitive profile
  Pass 4: Calibration Set Creation — select exemplar meetings for in-context learning

Supports:
  - Date-range-based extraction (process meetings from a specific time frame)
  - Incremental updates (add new meetings without reprocessing everything)
  - Automatic versioning of cognitive profiles
"""
import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from backend.app.config import settings
from backend.app.core.ic_cognitive_store import (
    delete_meeting_extract,
    get_meeting_extracts_by_date,
    list_meeting_extracts,
    load_calibration_set,
    load_cognitive_profile,
    load_extraction_state,
    load_meeting_extract,
    save_calibration_set,
    save_cognitive_profile,
    save_extraction_state,
    save_meeting_extract,
)

logger = logging.getLogger(__name__)

# ── LLM helper ────────────────────────────────────────────────────────────

def _llm_call(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.2,
    response_format: Optional[str] = "json",
) -> str:
    """
    Make a single LLM call using the configured answer model.

    Args:
        system_prompt: System-level instructions
        user_message: The user message / content to analyze
        temperature: Sampling temperature
        response_format: If "json", request JSON output from the model

    Returns:
        The model's response text
    """
    api_key = settings.get_openai_api_key()
    client = OpenAI(api_key=api_key)

    kwargs: Dict[str, Any] = {
        "model": settings.ANSWER_MODEL,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    if response_format == "json":
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


def _parse_json_response(text: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        # Strip markdown code fences
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


# ── Pass 1: Structural Extraction ──────────────────────────────────────────

PASS1_SYSTEM_PROMPT = """\
You are an expert analyst extracting structured information from biotech/biopharma \
Investment Committee (IC) meeting notes.

Your task is to parse a single meeting's notes into a structured record. Extract \
every identifiable question-answer exchange, discussion point, and decision.

Return a JSON object with this exact structure:
{
  "meeting_summary": "2-3 sentence overview of the meeting",
  "deal_name": "Name of the company/deal being discussed (or 'Multiple' if several)",
  "deal_stage": "e.g., Preclinical, Phase 1, Phase 2, Commercial, Platform, etc.",
  "modality": "e.g., Small molecule, Antibody, Gene therapy, Cell therapy, Platform, etc.",
  "therapeutic_area": "e.g., Oncology, Rare disease, Neurology, Immunology, etc.",
  "outcome": "Funded / Passed / Tabled / Under review / Unknown",
  "qa_items": [
    {
      "question": "The exact or closely paraphrased question asked",
      "asked_by": "Name of the person who asked (if identifiable), or 'Unknown'",
      "answer_summary": "Summary of the response given",
      "had_followup": true/false,
      "followup_detail": "What the follow-up was about (if any)",
      "category": "One of: Science & Mechanism | Clinical Development | Competitive Landscape | Commercial & Market | Team & Execution | Financial & Valuation | IP & Regulatory | Manufacturing | Portfolio Fit | Risk Assessment | Other"
    }
  ],
  "key_concerns_raised": ["List of the main concerns/risks discussed"],
  "positive_signals": ["List of things the committee liked"],
  "decision_rationale": "Why the committee made their decision (if clear from notes)"
}

Important:
- Extract ALL questions/discussion points, not just the obvious ones
- If a person's name appears before a question (e.g., "Dr. Smith: What about..."), \
capture it in asked_by
- If no names are identifiable, use "Unknown" for asked_by
- Be precise with categories — use the exact categories listed above
- If the notes cover multiple deals, create separate qa_items for each but note the \
deal name in the question context
"""


def run_pass1(meeting_text: str, meeting_title: str, meeting_date: str) -> Dict[str, Any]:
    """
    Pass 1: Structural Extraction.

    Parse a single meeting's text into a structured record with all
    identifiable Q&A exchanges, metadata, and decisions.

    Args:
        meeting_text: Full text content of the meeting notes
        meeting_title: Title of the meeting
        meeting_date: ISO date string of the meeting

    Returns:
        Structured meeting extract dict
    """
    user_message = f"""## Meeting: {meeting_title}
## Date: {meeting_date}

{meeting_text}"""

    logger.info(f"Pass 1 (Structural Extraction): {meeting_title} ({len(meeting_text)} chars)")

    response = _llm_call(PASS1_SYSTEM_PROMPT, user_message)
    result = _parse_json_response(response)

    # Attach metadata
    result["meeting_title"] = meeting_title
    result["meeting_date"] = meeting_date

    return result


# ── Pass 2: Reasoning Extraction ──────────────────────────────────────────

PASS2_SYSTEM_PROMPT = """\
You are a senior biotech VC analyst performing deep reasoning analysis on IC meeting \
question-and-answer records.

For each question from an IC meeting, your job is to infer the UNDERLYING cognitive \
driver — the deeper concern that motivated the question. Surface-level questions often \
mask deeper strategic concerns.

Examples:
- "What's your patent landscape?" → Underlying concern: Defensibility & competitive moat
- "Walk me through the Phase 1 data" → Underlying concern: Management's ability to \
think critically about their own data; data maturity
- "What's the competitive landscape?" → Underlying concern: Whether the team has a \
realistic view of their competitive position and differentiation
- "How many FTEs on the team?" → Underlying concern: Execution capability and burn rate \
efficiency

You will receive a structured meeting extract. For each qa_item, add reasoning fields.

Return the SAME structure with these additional fields added to each qa_item:
{
  "qa_items": [
    {
      ... (all existing fields preserved),
      "underlying_concern": "The deeper cognitive driver behind this question",
      "concern_category": "One of: Defensibility | Data Quality | Execution Risk | \
Market Reality | Financial Discipline | Scientific Validity | Regulatory Risk | \
Portfolio Strategy | Management Quality | Technical Feasibility",
      "what_satisfies": "What kind of answer would resolve this concern",
      "what_triggers_deeper_probing": "What kind of answer would cause follow-up questions",
      "risk_signal_strength": "High | Medium | Low — how much this question signals the \
IC sees risk here"
    }
  ]
}

Also add a top-level field:
{
  "meeting_cognitive_summary": "3-5 sentences describing the IC's overall cognitive \
stance in this meeting — what they were most worried about, what they liked, and how \
their questioning pattern revealed their thinking"
}

Preserve ALL existing fields from the input. Only ADD the new fields.
"""


def run_pass2(pass1_extract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pass 2: Reasoning Extraction.

    For each Q&A item in a Pass 1 extract, infer the underlying cognitive
    driver, what satisfies the concern, and what triggers deeper probing.

    Args:
        pass1_extract: Output from run_pass1()

    Returns:
        Enriched extract with reasoning fields added to each qa_item
    """
    title = pass1_extract.get("meeting_title", "Unknown")
    logger.info(f"Pass 2 (Reasoning Extraction): {title}")

    user_message = json.dumps(pass1_extract, indent=2, ensure_ascii=False)
    response = _llm_call(PASS2_SYSTEM_PROMPT, user_message)
    result = _parse_json_response(response)

    # Preserve metadata from pass 1 that the LLM might have dropped
    result["meeting_title"] = pass1_extract.get("meeting_title", "")
    result["meeting_date"] = pass1_extract.get("meeting_date", "")

    return result


# ── Combined Pass 1+2 per meeting ─────────────────────────────────────────

def extract_single_meeting(
    meeting_text: str,
    meeting_title: str,
    meeting_date: str,
    page_id: str,
) -> Dict[str, Any]:
    """
    Run Pass 1 + Pass 2 on a single meeting and save the result.

    Args:
        meeting_text: Full text content of the meeting
        meeting_title: Title of the meeting
        meeting_date: ISO date string
        page_id: Unique identifier (Confluence page ID or upload file ID)

    Returns:
        The enriched meeting extract (Pass 1 + Pass 2 combined)
    """
    # Pass 1: Structural extraction
    pass1_result = run_pass1(meeting_text, meeting_title, meeting_date)

    # Pass 2: Reasoning extraction
    pass2_result = run_pass2(pass1_result)

    # Attach the page_id for tracking
    pass2_result["page_id"] = page_id

    # Save to disk
    save_meeting_extract(page_id, pass2_result)

    return pass2_result


# ── Pass 3: Cross-Meeting Synthesis ───────────────────────────────────────

PASS3_SYSTEM_PROMPT = """\
You are a senior biotech VC strategist synthesizing intelligence across multiple \
Investment Committee (IC) meetings to build a comprehensive cognitive profile of \
how this committee thinks and makes decisions.

You will receive structured extracts from multiple IC meetings, each containing \
questions asked, underlying concerns, and outcomes. Your job is to identify patterns \
ACROSS meetings and produce a committee-level cognitive profile.

Return a JSON object with this structure:
{
  "committee_mental_model": {
    "core_priorities": [
      {
        "priority": "Description of a core concern the committee consistently returns to",
        "frequency": "How often this comes up (e.g., 'Nearly every meeting', 'Most meetings', 'Occasionally')",
        "typical_questions": ["Example questions that express this priority"],
        "what_satisfies_them": "What kind of evidence/answer resolves this concern",
        "deal_breaker_threshold": "When does this concern become a deal-killer"
      }
    ],
    "decision_patterns": {
      "funded_signals": ["Patterns present in deals that got funded"],
      "passed_signals": ["Patterns present in deals that were passed on"],
      "tabled_signals": ["What leads to a 'table for later' decision"]
    },
    "questioning_style": "Description of the committee's overall questioning approach — \
are they collaborative, adversarial, data-driven, narrative-driven, etc."
  },
  "member_profiles": [
    {
      "name": "Member name (or 'Unknown Member A/B/C' if not identified)",
      "consistent_concerns": ["What this member always focuses on"],
      "conditional_patterns": [
        {
          "condition": "When the deal is [type/stage/area]...",
          "behavior": "This member tends to [focus on / push back on / probe]..."
        }
      ],
      "satisfaction_signals": "What makes this member comfortable with a deal",
      "risk_tolerance": "High / Medium / Low — relative to the committee"
    }
  ],
  "collective_patterns": {
    "kill_criteria": ["Combinations of concerns that consistently lead to a pass"],
    "must_haves": ["Things that must be present for a deal to move forward"],
    "evolution_over_time": "How has the committee's thinking shifted over the time \
period analyzed? Any notable changes in priorities or risk appetite?",
    "blind_spots": ["Areas the committee rarely probes but probably should"],
    "category_frequency": {
      "Science & Mechanism": "How often this category dominates (percentage or qualitative)",
      "Clinical Development": "...",
      "Competitive Landscape": "...",
      "Commercial & Market": "...",
      "Financial & Valuation": "...",
      "Team & Execution": "...",
      "IP & Regulatory": "...",
      "Manufacturing": "...",
      "Other": "..."
    }
  },
  "date_range": {
    "from": "Earliest meeting date in the dataset",
    "to": "Latest meeting date in the dataset"
  },
  "meetings_analyzed": 0,
  "total_qa_items_analyzed": 0
}

Be specific, evidence-based, and cite actual patterns you observe. Do not invent \
patterns that aren't supported by the data. If member attribution is not available, \
focus on committee-level patterns and note that member-level analysis requires \
attributed meeting notes.
"""


def run_pass3(
    extracts: List[Dict[str, Any]],
    existing_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Pass 3: Cross-Meeting Cognitive Synthesis.

    Analyze all meeting extracts to identify committee-level patterns,
    member-level profiles, and decision criteria.

    For large datasets (>15 meetings), uses a map-reduce approach:
    batch meetings into groups, synthesize each batch, then merge.

    Args:
        extracts: List of Pass 1+2 enriched meeting extracts
        existing_profile: Optional existing cognitive profile to merge with
                         (for incremental updates)

    Returns:
        Committee-level cognitive profile dict
    """
    if not extracts:
        raise ValueError("No meeting extracts provided for synthesis")

    total_meetings = len(extracts)
    logger.info(f"Pass 3 (Cross-Meeting Synthesis): {total_meetings} meetings")

    BATCH_SIZE = 15  # Process in batches to stay within context limits

    if total_meetings <= BATCH_SIZE:
        # Single-shot synthesis
        profile = _synthesize_batch(extracts)
    else:
        # Map-reduce: synthesize batches, then merge
        batch_profiles = []
        for i in range(0, total_meetings, BATCH_SIZE):
            batch = extracts[i : i + BATCH_SIZE]
            logger.info(
                f"Pass 3: Synthesizing batch {i // BATCH_SIZE + 1} "
                f"({len(batch)} meetings)"
            )
            batch_profile = _synthesize_batch(batch)
            batch_profiles.append(batch_profile)

        # Merge batch profiles
        profile = _merge_profiles(batch_profiles, total_meetings)

    # If we have an existing profile (incremental update), merge with it
    if existing_profile:
        profile = _merge_with_existing(profile, existing_profile)

    # Save the profile
    save_cognitive_profile(profile)

    return profile


def _synthesize_batch(extracts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Synthesize a batch of meeting extracts into a cognitive profile."""
    # Build a condensed representation of each meeting for the LLM
    meetings_summary = []
    total_qa = 0
    for ext in extracts:
        qa_items = ext.get("qa_items", [])
        total_qa += len(qa_items)
        meeting_block = {
            "meeting_title": ext.get("meeting_title", ""),
            "meeting_date": ext.get("meeting_date", ""),
            "deal_name": ext.get("deal_name", ""),
            "deal_stage": ext.get("deal_stage", ""),
            "modality": ext.get("modality", ""),
            "therapeutic_area": ext.get("therapeutic_area", ""),
            "outcome": ext.get("outcome", ""),
            "meeting_cognitive_summary": ext.get("meeting_cognitive_summary", ""),
            "key_concerns_raised": ext.get("key_concerns_raised", []),
            "positive_signals": ext.get("positive_signals", []),
            "decision_rationale": ext.get("decision_rationale", ""),
            "qa_items": qa_items,
        }
        meetings_summary.append(meeting_block)

    user_message = (
        f"Analyze the following {len(extracts)} IC meetings "
        f"({total_qa} total Q&A items) and build a cognitive profile:\n\n"
        + json.dumps(meetings_summary, indent=2, ensure_ascii=False)
    )

    response = _llm_call(PASS3_SYSTEM_PROMPT, user_message, temperature=0.1)
    profile = _parse_json_response(response)

    # Add metadata
    dates = [
        ext.get("meeting_date", "")
        for ext in extracts
        if ext.get("meeting_date")
    ]
    if dates:
        profile["date_range"] = {"from": min(dates), "to": max(dates)}
    profile["meetings_analyzed"] = len(extracts)
    profile["total_qa_items_analyzed"] = total_qa

    return profile


MERGE_SYSTEM_PROMPT = """\
You are synthesizing multiple partial IC cognitive profiles into a single unified \
profile. Each partial profile was built from a batch of meetings. Your job is to \
merge them into one coherent, comprehensive profile.

Rules:
- Combine similar priorities/patterns, noting when they appear across multiple batches
- Preserve ALL unique patterns — do not drop patterns that appear in only one batch
- When priorities conflict between batches, note the evolution or difference
- Update frequencies to reflect the full dataset
- Member profiles should be merged by name (combine observations about the same person)

Return the merged profile using the exact same JSON schema as the input profiles.
Also update meetings_analyzed and total_qa_items_analyzed to reflect the full dataset.
"""


def _merge_profiles(
    batch_profiles: List[Dict[str, Any]],
    total_meetings: int,
) -> Dict[str, Any]:
    """Merge multiple batch-synthesized profiles into one."""
    logger.info(f"Pass 3: Merging {len(batch_profiles)} batch profiles")

    user_message = (
        f"Merge these {len(batch_profiles)} partial cognitive profiles "
        f"(covering {total_meetings} total meetings):\n\n"
        + json.dumps(batch_profiles, indent=2, ensure_ascii=False)
    )

    response = _llm_call(MERGE_SYSTEM_PROMPT, user_message, temperature=0.1)
    merged = _parse_json_response(response)

    # Ensure correct totals
    total_qa = sum(p.get("total_qa_items_analyzed", 0) for p in batch_profiles)
    merged["meetings_analyzed"] = total_meetings
    merged["total_qa_items_analyzed"] = total_qa

    # Merge date ranges
    all_from = [
        p.get("date_range", {}).get("from", "")
        for p in batch_profiles
        if p.get("date_range", {}).get("from")
    ]
    all_to = [
        p.get("date_range", {}).get("to", "")
        for p in batch_profiles
        if p.get("date_range", {}).get("to")
    ]
    if all_from and all_to:
        merged["date_range"] = {"from": min(all_from), "to": max(all_to)}

    return merged


INCREMENTAL_MERGE_SYSTEM_PROMPT = """\
You are updating an existing IC committee cognitive profile with new intelligence \
from recently analyzed meetings.

You will receive:
1. The EXISTING cognitive profile (built from previously analyzed meetings)
2. A NEW partial profile (built from newly added meetings)

Your job is to MERGE them intelligently:
- Strengthen patterns that appear in both (increase confidence/frequency)
- Add new patterns discovered in the new meetings
- Note any evolution or shifts in committee behavior
- Update the "evolution_over_time" field to capture any changes
- Preserve the richness of the existing profile — don't dilute it

Return the merged profile using the exact same JSON schema.
Update meetings_analyzed and total_qa_items_analyzed to reflect the combined total.
"""


def _merge_with_existing(
    new_profile: Dict[str, Any],
    existing_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge a new profile with an existing one for incremental updates."""
    logger.info("Pass 3: Merging new profile with existing cognitive profile")

    user_message = (
        "## Existing Profile\n"
        + json.dumps(existing_profile, indent=2, ensure_ascii=False)
        + "\n\n## New Profile (from recently added meetings)\n"
        + json.dumps(new_profile, indent=2, ensure_ascii=False)
    )

    response = _llm_call(
        INCREMENTAL_MERGE_SYSTEM_PROMPT, user_message, temperature=0.1
    )
    merged = _parse_json_response(response)

    # Sum up totals
    merged["meetings_analyzed"] = (
        existing_profile.get("meetings_analyzed", 0)
        + new_profile.get("meetings_analyzed", 0)
    )
    merged["total_qa_items_analyzed"] = (
        existing_profile.get("total_qa_items_analyzed", 0)
        + new_profile.get("total_qa_items_analyzed", 0)
    )

    # Extend date range
    dates_from = [
        d
        for d in [
            existing_profile.get("date_range", {}).get("from"),
            new_profile.get("date_range", {}).get("from"),
        ]
        if d
    ]
    dates_to = [
        d
        for d in [
            existing_profile.get("date_range", {}).get("to"),
            new_profile.get("date_range", {}).get("to"),
        ]
        if d
    ]
    if dates_from and dates_to:
        merged["date_range"] = {"from": min(dates_from), "to": max(dates_to)}

    return merged


# ── Pass 4: Calibration Set Creation ──────────────────────────────────────

PASS4_SYSTEM_PROMPT = """\
You are selecting and annotating a calibration set of exemplar IC meetings. These \
examples will be used as in-context learning examples when simulating IC behavior \
for new deals.

From the meeting extracts provided, select 10-15 meetings that best represent the \
DIVERSITY of the IC's behavior. You should include:

1. A deal the committee clearly loved (enthusiastic funding)
2. A deal they killed quickly (clear red flags)
3. A contentious debate (split opinions, extended discussion)
4. A novel modality or therapeutic area they hadn't seen much of
5. Different therapeutic areas (oncology, rare disease, neuro, etc.)
6. Different deal stages (preclinical, clinical, commercial)
7. A deal where the questioning pattern was unusual or particularly revealing
8. At minimum, ensure variety across outcomes (funded, passed, tabled)

For each selected meeting, create a rich annotation explaining:
- WHY this example is in the calibration set
- What it reveals about the IC's thinking
- What patterns a simulation model should learn from this example

Return a JSON object:
{
  "selection_rationale": "Overall explanation of why these meetings were chosen",
  "examples": [
    {
      "page_id": "The page_id of the selected meeting",
      "meeting_title": "Title",
      "meeting_date": "Date",
      "deal_name": "Deal name",
      "deal_stage": "Stage",
      "modality": "Modality",
      "therapeutic_area": "Area",
      "outcome": "Outcome",
      "annotation": "2-3 paragraph explanation of what this example teaches about IC behavior",
      "key_lesson": "One-sentence summary of the key pattern this example demonstrates",
      "calibration_role": "One of: Enthusiastic_Approval | Quick_Rejection | Contentious_Debate | Novel_Territory | Deep_Science_Probe | Commercial_Focus | Risk_Dominated | Team_Assessment",
      "representative_qa_exchange": {
        "question": "The most revealing question from this meeting",
        "answer_summary": "The response",
        "underlying_concern": "The deeper driver",
        "outcome_impact": "How this exchange affected the committee's decision"
      }
    }
  ]
}
"""


def run_pass4(extracts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pass 4: Calibration Set Creation.

    Select and annotate 10-15 exemplar meetings that best represent
    the diversity of the IC's behavior for in-context learning.

    Args:
        extracts: All meeting extracts (Pass 1+2 outputs)

    Returns:
        Calibration set with annotated examples
    """
    logger.info(f"Pass 4 (Calibration Set): Selecting from {len(extracts)} meetings")

    # Build condensed summaries for selection
    summaries = []
    for ext in extracts:
        summaries.append({
            "page_id": ext.get("page_id", ""),
            "meeting_title": ext.get("meeting_title", ""),
            "meeting_date": ext.get("meeting_date", ""),
            "deal_name": ext.get("deal_name", ""),
            "deal_stage": ext.get("deal_stage", ""),
            "modality": ext.get("modality", ""),
            "therapeutic_area": ext.get("therapeutic_area", ""),
            "outcome": ext.get("outcome", ""),
            "meeting_cognitive_summary": ext.get("meeting_cognitive_summary", ""),
            "key_concerns_raised": ext.get("key_concerns_raised", []),
            "positive_signals": ext.get("positive_signals", []),
            "decision_rationale": ext.get("decision_rationale", ""),
            "num_questions": len(ext.get("qa_items", [])),
            # Include a few representative Q&A items
            "sample_questions": [
                {
                    "question": q.get("question", ""),
                    "underlying_concern": q.get("underlying_concern", ""),
                    "category": q.get("category", ""),
                    "risk_signal_strength": q.get("risk_signal_strength", ""),
                }
                for q in ext.get("qa_items", [])[:5]
            ],
        })

    user_message = (
        f"Select 10-15 calibration examples from these {len(summaries)} meetings:\n\n"
        + json.dumps(summaries, indent=2, ensure_ascii=False)
    )

    response = _llm_call(PASS4_SYSTEM_PROMPT, user_message, temperature=0.2)
    calibration = _parse_json_response(response)

    # Enrich each selected example with the full extract data
    page_id_map = {ext.get("page_id", ""): ext for ext in extracts}
    for example in calibration.get("examples", []):
        pid = example.get("page_id", "")
        if pid in page_id_map:
            full_ext = page_id_map[pid]
            example["full_qa_items"] = full_ext.get("qa_items", [])

    save_calibration_set(calibration)
    return calibration


# ── Full Pipeline Orchestration ───────────────────────────────────────────

def run_full_extraction(
    meetings: List[Dict[str, Any]],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    progress_callback=None,
) -> Dict[str, Any]:
    """
    Run the complete 4-pass extraction pipeline on a set of meetings.

    Args:
        meetings: List of dicts with keys:
            - page_id: Unique identifier
            - title: Meeting title
            - meeting_date: ISO date string
            - body_text: Full text content of the meeting
        date_from: Start of date range (for metadata, filtering already done by caller)
        date_to: End of date range (for metadata)
        progress_callback: Optional callable(stage, current, total, detail)
            for progress reporting

    Returns:
        Dict with pipeline results and summary
    """
    total = len(meetings)
    logger.info(f"Starting full extraction pipeline for {total} meetings")

    results = {
        "pass1_pass2_results": [],
        "pass3_profile": None,
        "pass4_calibration": None,
        "summary": {
            "total_meetings": total,
            "meetings_processed": 0,
            "total_qa_items": 0,
            "date_from": date_from,
            "date_to": date_to,
        },
    }

    # Track processed page IDs
    processed_ids = []

    # ── Pass 1 + Pass 2: Per-meeting extraction ──
    for i, meeting in enumerate(meetings):
        page_id = meeting["page_id"]
        if progress_callback:
            progress_callback(
                "pass1_pass2", i + 1, total,
                f"Extracting: {meeting.get('title', page_id)}"
            )

        try:
            extract = extract_single_meeting(
                meeting_text=meeting["body_text"],
                meeting_title=meeting.get("title", ""),
                meeting_date=meeting.get("meeting_date", ""),
                page_id=page_id,
            )
            results["pass1_pass2_results"].append(extract)
            results["summary"]["total_qa_items"] += len(
                extract.get("qa_items", [])
            )
            processed_ids.append(page_id)
        except Exception as e:
            logger.error(f"Failed to extract meeting {page_id}: {e}")

    results["summary"]["meetings_processed"] = len(results["pass1_pass2_results"])

    if not results["pass1_pass2_results"]:
        logger.error("No meetings were successfully extracted")
        return results

    # ── Pass 3: Cross-meeting synthesis ──
    if progress_callback:
        progress_callback("pass3", 0, 1, "Synthesizing cognitive profile...")

    try:
        all_extracts = results["pass1_pass2_results"]
        profile = run_pass3(all_extracts)
        results["pass3_profile"] = profile
    except Exception as e:
        logger.error(f"Pass 3 synthesis failed: {e}")

    if progress_callback:
        progress_callback("pass3", 1, 1, "Cognitive profile complete")

    # ── Pass 4: Calibration set ──
    if progress_callback:
        progress_callback("pass4", 0, 1, "Building calibration set...")

    try:
        all_extracts = results["pass1_pass2_results"]
        if len(all_extracts) >= 5:
            calibration = run_pass4(all_extracts)
            results["pass4_calibration"] = calibration
        else:
            logger.info(
                "Skipping Pass 4: need at least 5 meetings for calibration set"
            )
    except Exception as e:
        logger.error(f"Pass 4 calibration failed: {e}")

    if progress_callback:
        progress_callback("pass4", 1, 1, "Calibration set complete")

    # ── Save extraction state ──
    save_extraction_state({
        "processed_page_ids": processed_ids,
        "date_from": date_from,
        "date_to": date_to,
        "total_meetings": len(processed_ids),
        "total_qa_items": results["summary"]["total_qa_items"],
    })

    return results


# ── Incremental Update ────────────────────────────────────────────────────

def run_incremental_update(
    new_meetings: List[Dict[str, Any]],
    progress_callback=None,
) -> Dict[str, Any]:
    """
    Process newly added meetings and update the cognitive profile incrementally.

    This avoids reprocessing all historical meetings. It:
    1. Runs Pass 1+2 on the new meetings only
    2. Runs Pass 3 on the new extracts, then merges with the existing profile
    3. Re-runs Pass 4 on ALL extracts (existing + new) to update calibration set

    Args:
        new_meetings: List of new meeting dicts (same format as run_full_extraction)
        progress_callback: Optional callable(stage, current, total, detail)

    Returns:
        Dict with update results
    """
    existing_profile = load_cognitive_profile()
    existing_state = load_extraction_state()
    already_processed = set(
        existing_state.get("processed_page_ids", []) if existing_state else []
    )

    # Filter out already-processed meetings
    truly_new = [
        m for m in new_meetings if m["page_id"] not in already_processed
    ]

    if not truly_new:
        logger.info("No new meetings to process — all already extracted")
        return {
            "status": "no_new_meetings",
            "already_processed": len(already_processed),
        }

    total = len(truly_new)
    logger.info(
        f"Incremental update: {total} new meetings "
        f"({len(already_processed)} already processed)"
    )

    results = {
        "new_meetings_processed": 0,
        "new_qa_items": 0,
        "profile_updated": False,
        "calibration_updated": False,
    }

    # ── Pass 1 + 2 on new meetings only ──
    new_extracts = []
    for i, meeting in enumerate(truly_new):
        if progress_callback:
            progress_callback(
                "pass1_pass2", i + 1, total,
                f"Extracting: {meeting.get('title', meeting['page_id'])}"
            )
        try:
            extract = extract_single_meeting(
                meeting_text=meeting["body_text"],
                meeting_title=meeting.get("title", ""),
                meeting_date=meeting.get("meeting_date", ""),
                page_id=meeting["page_id"],
            )
            new_extracts.append(extract)
            results["new_qa_items"] += len(extract.get("qa_items", []))
        except Exception as e:
            logger.error(f"Failed to extract meeting {meeting['page_id']}: {e}")

    results["new_meetings_processed"] = len(new_extracts)

    if not new_extracts:
        return results

    # ── Pass 3: Synthesize new meetings, merge with existing profile ──
    if progress_callback:
        progress_callback("pass3", 0, 1, "Updating cognitive profile...")

    try:
        updated_profile = run_pass3(new_extracts, existing_profile=existing_profile)
        results["profile_updated"] = True
    except Exception as e:
        logger.error(f"Incremental Pass 3 failed: {e}")

    if progress_callback:
        progress_callback("pass3", 1, 1, "Cognitive profile updated")

    # ── Pass 4: Re-run calibration with ALL extracts ──
    if progress_callback:
        progress_callback("pass4", 0, 1, "Updating calibration set...")

    try:
        all_extracts_on_disk = get_meeting_extracts_by_date()
        if len(all_extracts_on_disk) >= 5:
            run_pass4(all_extracts_on_disk)
            results["calibration_updated"] = True
    except Exception as e:
        logger.error(f"Incremental Pass 4 failed: {e}")

    if progress_callback:
        progress_callback("pass4", 1, 1, "Calibration set updated")

    # ── Update extraction state ──
    new_processed_ids = [m.get("page_id", "") for m in new_extracts]
    all_processed = list(already_processed | set(new_processed_ids))

    old_qa = existing_state.get("total_qa_items", 0) if existing_state else 0
    save_extraction_state({
        "processed_page_ids": all_processed,
        "date_from": existing_state.get("date_from") if existing_state else None,
        "date_to": existing_state.get("date_to") if existing_state else None,
        "total_meetings": len(all_processed),
        "total_qa_items": old_qa + results["new_qa_items"],
        "last_incremental_update": True,
    })

    return results
