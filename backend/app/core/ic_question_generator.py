"""
IC Question Generator — uses RAG over historical IC meeting Q&A
to anticipate what the Investment Committee would likely ask about
new project materials.
"""
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI

from backend.app.config import settings
from backend.app.core.ic_meeting_store import get_ic_meeting_store

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
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


def generate_ic_questions(
    project_description: str,
    uploaded_doc_texts: Optional[List[str]] = None,
    top_k_history: int = 20,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate anticipated IC questions for new project materials.

    Args:
        project_description: Text description or summary of the project
        uploaded_doc_texts: Optional list of extracted texts from uploaded documents
        top_k_history: Number of historical Q&A segments to retrieve
        date_from: Only use IC meetings on or after this date (ISO, e.g. "2024-01-01")
        date_to: Only use IC meetings on or before this date (ISO, e.g. "2025-12-31")

    Returns:
        Dict with keys: questions_markdown, historical_references, metadata
    """
    # 1. Build the project context from description + uploaded docs
    project_context_parts = []
    if project_description:
        project_context_parts.append(project_description)
    if uploaded_doc_texts:
        for i, text in enumerate(uploaded_doc_texts, 1):
            # Truncate very long docs to avoid token limits
            truncated = text[:8000] if len(text) > 8000 else text
            project_context_parts.append(f"--- Uploaded Document {i} ---\n{truncated}")

    project_context = "\n\n".join(project_context_parts)

    if not project_context.strip():
        return {
            "questions_markdown": "Please provide a project description or upload project documents.",
            "historical_references": [],
            "metadata": {"error": "No project context provided"},
        }

    # 2. Retrieve relevant historical IC Q&A from vector store
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

    # 3. Call LLM to generate anticipated questions
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
        f"Generating IC questions. Project context: {len(project_context)} chars, "
        f"Historical refs: {len(historical_results)}"
    )

    response = client.chat.completions.create(
        model=settings.ANSWER_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    answer = response.choices[0].message.content

    # 4. Build references list for the frontend
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
            "model": settings.ANSWER_MODEL,
            "project_context_length": len(project_context),
            "historical_segments_used": len(historical_results),
            "date_from": date_from,
            "date_to": date_to,
        },
    }
