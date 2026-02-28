"""
IC Question Generator — two-mode question generation:

  Mode 1 (Legacy/Fallback): RAG-based generation using vector search over
    historical IC meeting Q&A segments. Used when no cognitive profile exists.

  Mode 2 (Cognitive Simulation): Two-stage deep simulation using pre-extracted
    cognitive profiles. This is the primary mode when profiles are available:

    Stage A: Deal Decomposition — analyze the incoming materials to identify
             claims, evidence gaps, risks, and deal archetype
    Stage B: IC Simulation — use the cognitive profile + calibration set to
             simulate committee behavior with follow-up trees

Automatically selects Mode 2 when a cognitive profile exists, falls back to Mode 1.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from backend.app.config import settings
from backend.app.core.ic_cognitive_store import (
    load_calibration_set,
    load_cognitive_profile,
)
from backend.app.core.ic_meeting_store import get_ic_meeting_store

logger = logging.getLogger(__name__)

# ── Mode 1: Legacy RAG-based system prompt (kept as fallback) ─────────────

LEGACY_SYSTEM_PROMPT = """\
You are an expert Investment Committee (IC) question simulator for a biotech/biopharma \
venture capital firm. Your job is to anticipate the questions that IC members would \
raise when reviewing new project materials.

You have access to historical IC meeting Q&A records that show the actual questions \
previously asked by IC members and the discussions that followed. Use these records \
to understand:
- The IC's recurring areas of concern (e.g., clinical risk, competitive landscape, \
IP strength, commercial viability, team quality, valuation)
- The depth and style of questioning
- Follow-up patterns and probing tendencies

Based on the new project materials provided by the user, generate a comprehensive \
list of anticipated IC questions. For each question:
1. State the question clearly
2. Explain why the IC would likely ask this (referencing historical patterns where relevant)
3. Suggest what a strong answer should address
4. Rate the priority (High / Medium / Low) based on how frequently similar questions \
appeared in historical meetings

Organize questions by category (e.g., Science & Mechanism, Clinical Development, \
Competitive Landscape, Commercial Potential, Team & Execution, Financial & Valuation, \
IP & Regulatory).

Be specific, not generic. Tailor questions to the actual content of the project materials.\
"""


# ── Mode 2: Stage A — Deal Decomposition ─────────────────────────────────

STAGE_A_SYSTEM_PROMPT = """\
You are a senior biotech VC analyst performing a thorough pre-IC analysis of new \
deal materials. Your job is to decompose the deal into its component parts so that \
the IC simulation can respond to the SPECIFIC strengths and weaknesses of THIS deal.

Analyze the provided materials and produce a structured assessment:

1. **Key Claims Being Made** — What is the deal team asserting? (efficacy claims, \
market size claims, competitive advantage claims, etc.)

2. **Evidence Assessment** — For each claim, how strong is the supporting evidence? \
What data is provided vs. what's asserted without evidence?

3. **Conspicuous Absences** — What's NOT in the materials that should be? What topics \
are suspiciously missing or underaddressed?

4. **Obvious Risks** — The risks anyone would see

5. **Non-Obvious Risks** — Risks that require deeper domain knowledge to spot \
(regulatory pathway issues, manufacturing scalability concerns, competitive threats \
not mentioned, market access barriers, etc.)

6. **Deal Archetype** — How does this deal compare to common deal archetypes? \
(e.g., "early-stage platform with limited clinical data", "clinical-stage with \
strong data but crowded space", "commercial-stage acquisition with integration risk")

7. **Red Flags** — Specific elements that would trigger IC scrutiny

Be thorough, specific, and cite specific passages from the materials. This analysis \
will directly drive what the simulated IC focuses on.\
"""


STAGE_B_SYSTEM_PROMPT_TEMPLATE = """\
You are simulating the Investment Committee (IC) of a biotech/biopharma venture capital \
firm. You have deeply internalized how this specific committee thinks, what they care \
about, and how they make decisions.

## Your IC Cognitive Profile

{cognitive_profile}

## Calibration Examples

The following are real examples of how this IC has behaved in past meetings. Use them \
to calibrate your questioning style, depth, and priorities:

{calibration_examples}

## Your Task

You have received a deal decomposition analysis of new project materials. Based on \
your deep understanding of how this IC thinks and operates, generate:

### 1. Opening Reactions
What would each known IC member (or the committee collectively if member attribution \
is not available) likely focus on FIRST when they see these materials? What jumps out \
at them based on their known priorities?

### 2. Primary Questions (8-12)
The questions with the highest probability of being asked. For each:
- **The Question**: Stated as the IC member would phrase it
- **Who Would Ask It**: Which member (or "Committee") based on their known focus areas
- **Why They'd Ask It**: Reference the specific cognitive pattern from the profile \
that drives this question, AND the specific element in this deal that triggers it
- **Priority**: High / Medium / Low based on historical frequency and this deal's specifics
- **What a Strong Answer Covers**: Specific elements the answer must address
- **Confidence**: Your confidence (0-100%) that this question would actually be asked

### 3. Follow-Up Trees (for top 5 questions)
For each of the 5 highest-priority questions:
- **If the team answers well**: What's the likely follow-up?
- **If the team answers poorly**: What escalation or deeper probe follows?
- **The underlying concern being tested**: What cognitive driver is at work?

### 4. The Meta-Read
- **Overall Sentiment**: Where does this deal land on the spectrum from "easy yes" to \
"hard pass"? What's the likely initial temperature of the room?
- **Swing Factors**: What 2-3 things could move the needle in either direction?
- **Prediction**: Funded / Passed / Tabled, with reasoning
- **Preparation Priority**: What should the deal team prepare MOST carefully for?

Be specific, sharp, and grounded in the cognitive profile. Avoid generic questions \
that any IC would ask — focus on questions that THIS specific IC would ask based on \
THEIR patterns, triggered by THIS specific deal's characteristics.\
"""


def _build_stage_b_system_prompt(
    profile: Dict[str, Any],
    calibration: Optional[Dict[str, Any]],
) -> str:
    """Build the Stage B system prompt with embedded cognitive profile and calibration."""
    # Format cognitive profile — include the key sections
    profile_sections = []

    cm = profile.get("committee_mental_model", {})
    if cm:
        profile_sections.append("### Committee Mental Model")
        if cm.get("core_priorities"):
            profile_sections.append("**Core Priorities:**")
            for p in cm["core_priorities"]:
                profile_sections.append(
                    f"- {p.get('priority', '')} "
                    f"(Frequency: {p.get('frequency', 'Unknown')})"
                )
                if p.get("typical_questions"):
                    for q in p["typical_questions"]:
                        profile_sections.append(f"  - Example: \"{q}\"")
                if p.get("what_satisfies_them"):
                    profile_sections.append(
                        f"  - Satisfied by: {p['what_satisfies_them']}"
                    )
                if p.get("deal_breaker_threshold"):
                    profile_sections.append(
                        f"  - Deal-breaker: {p['deal_breaker_threshold']}"
                    )

        dp = cm.get("decision_patterns", {})
        if dp:
            profile_sections.append("\n**Decision Patterns:**")
            if dp.get("funded_signals"):
                profile_sections.append(
                    f"- Funded signals: {', '.join(dp['funded_signals'])}"
                )
            if dp.get("passed_signals"):
                profile_sections.append(
                    f"- Pass signals: {', '.join(dp['passed_signals'])}"
                )
            if dp.get("tabled_signals"):
                profile_sections.append(
                    f"- Tabled signals: {', '.join(dp['tabled_signals'])}"
                )

        if cm.get("questioning_style"):
            profile_sections.append(
                f"\n**Questioning Style:** {cm['questioning_style']}"
            )

    # Member profiles
    members = profile.get("member_profiles", [])
    if members:
        profile_sections.append("\n### IC Member Profiles")
        for m in members:
            profile_sections.append(f"\n**{m.get('name', 'Unknown')}**")
            if m.get("consistent_concerns"):
                profile_sections.append(
                    f"- Always focuses on: {', '.join(m['consistent_concerns'])}"
                )
            if m.get("conditional_patterns"):
                for cp in m["conditional_patterns"]:
                    profile_sections.append(
                        f"- When {cp.get('condition', '...')}: "
                        f"{cp.get('behavior', '...')}"
                    )
            if m.get("risk_tolerance"):
                profile_sections.append(
                    f"- Risk tolerance: {m['risk_tolerance']}"
                )

    # Collective patterns
    cp = profile.get("collective_patterns", {})
    if cp:
        profile_sections.append("\n### Collective Patterns")
        if cp.get("kill_criteria"):
            profile_sections.append(
                f"- Kill criteria: {', '.join(cp['kill_criteria'])}"
            )
        if cp.get("must_haves"):
            profile_sections.append(
                f"- Must-haves: {', '.join(cp['must_haves'])}"
            )
        if cp.get("evolution_over_time"):
            profile_sections.append(
                f"- Evolution: {cp['evolution_over_time']}"
            )
        if cp.get("blind_spots"):
            profile_sections.append(
                f"- Blind spots: {', '.join(cp['blind_spots'])}"
            )

    cognitive_profile_text = "\n".join(profile_sections)

    # Format calibration examples
    calibration_text = "No calibration examples available."
    if calibration and calibration.get("examples"):
        cal_parts = []
        for i, ex in enumerate(calibration["examples"], 1):
            cal_block = (
                f"**Example {i}: {ex.get('deal_name', 'Unknown Deal')}** "
                f"({ex.get('deal_stage', '')}, {ex.get('therapeutic_area', '')}) "
                f"→ Outcome: {ex.get('outcome', 'Unknown')}\n"
                f"Role: {ex.get('calibration_role', '')}\n"
                f"Key Lesson: {ex.get('key_lesson', '')}\n"
            )
            rep = ex.get("representative_qa_exchange", {})
            if rep:
                cal_block += (
                    f"Representative Exchange:\n"
                    f"  Q: {rep.get('question', '')}\n"
                    f"  Underlying: {rep.get('underlying_concern', '')}\n"
                    f"  Impact: {rep.get('outcome_impact', '')}\n"
                )
            # Include full Q&A items if available (condensed)
            full_qa = ex.get("full_qa_items", [])
            if full_qa:
                cal_block += f"Full Q&A ({len(full_qa)} items):\n"
                for qi in full_qa[:8]:  # Limit to 8 per example to save tokens
                    cal_block += (
                        f"  - Q: {qi.get('question', '')[:150]}\n"
                        f"    Concern: {qi.get('underlying_concern', '')[:100]}\n"
                    )
            cal_parts.append(cal_block)
        calibration_text = "\n---\n".join(cal_parts)

    return STAGE_B_SYSTEM_PROMPT_TEMPLATE.format(
        cognitive_profile=cognitive_profile_text,
        calibration_examples=calibration_text,
    )


# ── Main entry point ─────────────────────────────────────────────────────

def generate_ic_questions(
    project_description: str,
    uploaded_doc_texts: Optional[List[str]] = None,
    top_k_history: int = 20,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    mode: str = "auto",
) -> Dict[str, Any]:
    """
    Generate anticipated IC questions for new project materials.

    Args:
        project_description: Text description or summary of the project
        uploaded_doc_texts: Optional list of extracted texts from uploaded documents
        top_k_history: Number of historical Q&A segments to retrieve (Legacy mode only)
        date_from: Only use IC meetings on or after this date
        date_to: Only use IC meetings on or before this date
        mode: "auto" (default), "cognitive", or "legacy"
              - auto: Use cognitive simulation if profile exists, else legacy RAG
              - cognitive: Force cognitive simulation (fails if no profile)
              - legacy: Force legacy RAG mode

    Returns:
        Dict with keys: questions_markdown, historical_references, metadata
    """
    # Build project context — NO truncation for cognitive mode
    project_context = _build_project_context(project_description, uploaded_doc_texts)

    if not project_context.strip():
        return {
            "questions_markdown": "Please provide a project description or upload project documents.",
            "historical_references": [],
            "metadata": {"error": "No project context provided"},
        }

    # Load cognitive profile
    profile = load_cognitive_profile()
    calibration = load_calibration_set()

    # Mode selection
    if mode == "cognitive":
        if not profile:
            return {
                "questions_markdown": (
                    "**Cognitive Simulation mode selected but no profile exists yet.**\n\n"
                    "Please run the extraction pipeline first (sync meetings, then wait for "
                    "auto-extraction to complete), or switch to Legacy RAG mode."
                ),
                "historical_references": [],
                "metadata": {"error": "No cognitive profile available", "mode": "cognitive"},
            }
        logger.info("Mode explicitly set to Cognitive Simulation")
        return _generate_cognitive_mode(project_context, profile, calibration)

    elif mode == "legacy":
        logger.info("Mode explicitly set to Legacy RAG")
        return _generate_legacy_mode(project_context, top_k_history, date_from, date_to)

    else:  # auto
        if profile:
            logger.info("Cognitive profile found — using Mode 2 (Cognitive Simulation)")
            return _generate_cognitive_mode(project_context, profile, calibration)
        else:
            logger.info("No cognitive profile — falling back to Mode 1 (Legacy RAG)")
            return _generate_legacy_mode(project_context, top_k_history, date_from, date_to)


def _build_project_context(
    project_description: str,
    uploaded_doc_texts: Optional[List[str]] = None,
) -> str:
    """Build project context from description + uploaded docs. No truncation."""
    parts = []
    if project_description:
        parts.append(project_description)
    if uploaded_doc_texts:
        for i, text in enumerate(uploaded_doc_texts, 1):
            parts.append(f"--- Uploaded Document {i} ---\n{text}")
    return "\n\n".join(parts)


# ── Mode 2: Cognitive Simulation ──────────────────────────────────────────

def _generate_cognitive_mode(
    project_context: str,
    profile: Dict[str, Any],
    calibration: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Two-stage cognitive simulation:
    Stage A: Decompose the deal materials
    Stage B: Simulate IC behavior using cognitive profile
    """
    api_key = settings.get_openai_api_key()
    client = OpenAI(api_key=api_key)

    # ── Stage A: Deal Decomposition ──
    logger.info(
        f"Stage A (Deal Decomposition): {len(project_context)} chars of materials"
    )

    stage_a_response = client.chat.completions.create(
        model=settings.ANSWER_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": STAGE_A_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "## Project Materials for IC Review\n\n"
                    + project_context
                    + "\n\n---\n"
                    "Produce a thorough deal decomposition analysis."
                ),
            },
        ],
    )

    deal_decomposition = stage_a_response.choices[0].message.content
    logger.info(f"Stage A complete: {len(deal_decomposition)} chars of analysis")

    # ── Stage B: IC Simulation ──
    logger.info("Stage B (IC Simulation): generating questions from cognitive profile")

    stage_b_system = _build_stage_b_system_prompt(profile, calibration)

    stage_b_response = client.chat.completions.create(
        model=settings.ANSWER_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": stage_b_system},
            {
                "role": "user",
                "content": (
                    "## Deal Decomposition Analysis\n\n"
                    + deal_decomposition
                    + "\n\n## Original Project Materials (for reference)\n\n"
                    + project_context[:30000]  # Include materials for grounding
                    + "\n\n---\n"
                    "Based on the deal decomposition and your deep understanding "
                    "of this IC's cognitive patterns, generate your full IC simulation "
                    "with opening reactions, primary questions, follow-up trees, "
                    "and meta-read."
                ),
            },
        ],
    )

    simulation_output = stage_b_response.choices[0].message.content

    return {
        "questions_markdown": simulation_output,
        "deal_decomposition": deal_decomposition,
        "historical_references": [],
        "metadata": {
            "mode": "cognitive_simulation",
            "model": settings.ANSWER_MODEL,
            "project_context_length": len(project_context),
            "profile_version": profile.get("version"),
            "profile_meetings_analyzed": profile.get("meetings_analyzed", 0),
            "calibration_examples_used": (
                len(calibration.get("examples", []))
                if calibration
                else 0
            ),
            "stage_a_length": len(deal_decomposition),
        },
    }


# ── Mode 1: Legacy RAG ───────────────────────────────────────────────────

def _generate_legacy_mode(
    project_context: str,
    top_k_history: int,
    date_from: Optional[str],
    date_to: Optional[str],
) -> Dict[str, Any]:
    """Original RAG-based question generation (fallback when no profile exists)."""
    # Retrieve relevant historical IC Q&A from vector store
    ic_store = get_ic_meeting_store()
    historical_results = ic_store.search(
        project_context[:2000],
        top_k=top_k_history,
        date_from=date_from,
        date_to=date_to,
    )

    # Build historical context string
    historical_context = ""
    if historical_results:
        history_parts = []
        for i, result in enumerate(historical_results, 1):
            part = f"[Historical Q&A #{i}]"
            if result.get("meeting_title"):
                part += f" Meeting: {result['meeting_title']}"
            if result.get("meeting_date"):
                part += f" ({result['meeting_date'][:10]})"
            part += f"\n{result['content']}"
            history_parts.append(part)
        historical_context = "\n\n".join(history_parts)

    # Call LLM
    api_key = settings.get_openai_api_key()
    client = OpenAI(api_key=api_key)

    user_message_parts = [
        "## New Project Materials\n",
        project_context,
    ]

    if historical_context:
        user_message_parts.append(
            "\n\n## Historical IC Meeting Q&A (for reference)\n"
        )
        user_message_parts.append(historical_context)

    user_message_parts.append(
        "\n\n---\n"
        "Based on the project materials above and the historical IC Q&A patterns, "
        "generate a comprehensive list of anticipated IC questions organized by category. "
        "For each question, include the priority level, rationale, and guidance on "
        "what a strong answer should cover."
    )

    user_message = "\n".join(user_message_parts)

    logger.info(
        f"Generating IC questions (legacy mode). "
        f"Project context: {len(project_context)} chars, "
        f"Historical refs: {len(historical_results)}"
    )

    response = client.chat.completions.create(
        model=settings.ANSWER_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": LEGACY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    answer = response.choices[0].message.content

    # Build references list
    references = []
    for r in historical_results[:10]:
        references.append({
            "meeting_title": r.get("meeting_title", ""),
            "meeting_date": r.get("meeting_date", ""),
            "question": r.get("question", ""),
            "topic": r.get("topic", ""),
            "score": round(r.get("score", 0), 3),
        })

    return {
        "questions_markdown": answer,
        "historical_references": references,
        "metadata": {
            "mode": "legacy_rag",
            "model": settings.ANSWER_MODEL,
            "project_context_length": len(project_context),
            "historical_segments_used": len(historical_results),
            "date_from": date_from,
            "date_to": date_to,
        },
    }
