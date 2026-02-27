"""
Confluence API integration for fetching IC meeting notes.

Connects to Atlassian Confluence REST API to pull meeting note pages
from a specified space or under a parent page.
"""
import requests
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from html import unescape

from backend.app.config import settings

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Client for Atlassian Confluence REST API (Cloud)."""

    def __init__(self):
        self.base_url = settings.CONFLUENCE_BASE_URL.rstrip("/")
        self.username = settings.CONFLUENCE_USERNAME
        self.api_token = settings.CONFLUENCE_API_TOKEN
        self.space_key = settings.CONFLUENCE_SPACE_KEY
        self.parent_page_id = settings.CONFLUENCE_PARENT_PAGE_ID

        if not self.base_url or not self.username or not self.api_token:
            raise ValueError(
                "Confluence configuration incomplete. "
                "Set CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, and CONFLUENCE_API_TOKEN."
            )

        self.session = requests.Session()
        self.session.auth = (self.username, self.api_token)
        self.session.headers.update({"Accept": "application/json"})

    def _api_get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to the Confluence REST API."""
        url = f"{self.base_url}/rest/api{path}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def test_connection(self) -> Dict:
        """Test the Confluence connection and return space info."""
        try:
            if self.space_key:
                data = self._api_get(f"/space/{self.space_key}")
                return {
                    "status": "connected",
                    "space_name": data.get("name", ""),
                    "space_key": data.get("key", ""),
                }
            else:
                data = self._api_get("/space", params={"limit": 1})
                return {"status": "connected", "spaces_available": data.get("size", 0)}
        except requests.exceptions.RequestException as e:
            logger.error(f"Confluence connection test failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_meeting_pages(self, limit: int = 200) -> List[Dict]:
        """
        Fetch IC meeting note pages from Confluence.

        If CONFLUENCE_PARENT_PAGE_ID is set, fetches child pages of that parent.
        Otherwise, fetches all pages in the configured space.

        Returns:
            List of page metadata dicts with keys: page_id, title, created, updated
        """
        pages = []
        start = 0
        page_size = 50

        while start < limit:
            fetch_size = min(page_size, limit - start)

            if self.parent_page_id:
                # Fetch child pages of the parent
                data = self._api_get(
                    f"/content/{self.parent_page_id}/child/page",
                    params={
                        "start": start,
                        "limit": fetch_size,
                        "expand": "version,history",
                    },
                )
            else:
                # Fetch all pages in the space
                cql = f'space="{self.space_key}" AND type=page'
                data = self._api_get(
                    "/content/search",
                    params={
                        "cql": cql,
                        "start": start,
                        "limit": fetch_size,
                        "expand": "version,history",
                    },
                )

            results = data.get("results", [])
            if not results:
                break

            for page in results:
                history = page.get("history", {})
                pages.append({
                    "page_id": page["id"],
                    "title": page["title"],
                    "created": history.get("createdDate", ""),
                    "updated": page.get("version", {}).get("when", ""),
                })

            start += len(results)
            if len(results) < fetch_size:
                break

        logger.info(f"Found {len(pages)} meeting pages in Confluence")
        return pages

    def get_page_content(self, page_id: str) -> Dict:
        """
        Fetch the full content (body) of a single Confluence page.

        Returns:
            Dict with page_id, title, body_html, body_text, created, updated
        """
        data = self._api_get(
            f"/content/{page_id}",
            params={"expand": "body.storage,version,history"},
        )

        body_html = data.get("body", {}).get("storage", {}).get("value", "")
        body_text = self._html_to_text(body_html)
        history = data.get("history", {})

        return {
            "page_id": data["id"],
            "title": data["title"],
            "body_html": body_html,
            "body_text": body_text,
            "created": history.get("createdDate", ""),
            "updated": data.get("version", {}).get("when", ""),
        }

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert Confluence storage-format HTML to plain text."""
        if not html:
            return ""

        text = html
        # Convert common block elements to newlines
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"</p>", "\n\n", text)
        text = re.sub(r"</li>", "\n", text)
        text = re.sub(r"</tr>", "\n", text)
        text = re.sub(r"</h[1-6]>", "\n\n", text)
        text = re.sub(r"</div>", "\n", text)
        text = re.sub(r"</td>", " | ", text)
        text = re.sub(r"</th>", " | ", text)
        # Strip remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Decode HTML entities
        text = unescape(text)
        # Normalize whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()


def parse_meeting_qna(text: str, title: str = "") -> List[Dict]:
    """
    Parse meeting note text into Q&A segments.

    Tries to identify question-answer patterns from IC meeting notes.
    Falls back to chunking the text if no clear Q&A structure is found.

    Returns:
        List of dicts with keys: question, answer, topic, raw_text
    """
    qna_pairs = []

    # Common patterns for IC meeting Q&A
    # Pattern 1: "Q:" / "A:" style
    qa_pattern = re.compile(
        r"(?:Q[:.]\s*|Question[:.]\s*)(.*?)(?:\n\s*(?:A[:.]\s*|Answer[:.]\s*)(.*?))"
        r"(?=\n\s*(?:Q[:.]\s*|Question[:.]\s*)|$)",
        re.DOTALL | re.IGNORECASE,
    )
    matches = qa_pattern.findall(text)

    if matches:
        for q, a in matches:
            q_clean = q.strip()
            a_clean = a.strip()
            if q_clean:
                qna_pairs.append({
                    "question": q_clean,
                    "answer": a_clean,
                    "topic": _extract_topic(q_clean),
                    "raw_text": f"Q: {q_clean}\nA: {a_clean}",
                })

    # Pattern 2: Numbered questions "1." / "2." followed by discussion/response
    if not qna_pairs:
        numbered_pattern = re.compile(
            r"(?:^|\n)\s*(\d+)\.\s+(.*?)(?=\n\s*\d+\.\s+|$)",
            re.DOTALL,
        )
        matches = numbered_pattern.findall(text)
        for num, content in matches:
            content_clean = content.strip()
            if len(content_clean) > 20:  # Skip very short items
                # Try to split into Q and A by looking for response indicators
                parts = re.split(
                    r"\n\s*(?:Response|Answer|Reply|Discussion|Comment)[:.]\s*",
                    content_clean,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )
                question = parts[0].strip()
                answer = parts[1].strip() if len(parts) > 1 else ""
                qna_pairs.append({
                    "question": question,
                    "answer": answer,
                    "topic": _extract_topic(question),
                    "raw_text": content_clean,
                })

    # Pattern 3: Bullet-point based discussion
    if not qna_pairs:
        bullet_pattern = re.compile(
            r"[-\u2022\u25CF]\s+(.*?)(?=\n\s*[-\u2022\u25CF]\s+|$)",
            re.DOTALL,
        )
        matches = bullet_pattern.findall(text)
        for content in matches:
            content_clean = content.strip()
            if len(content_clean) > 30 and "?" in content_clean:
                # Contains a question mark — likely a discussion point with a question
                qna_pairs.append({
                    "question": content_clean,
                    "answer": "",
                    "topic": _extract_topic(content_clean),
                    "raw_text": content_clean,
                })

    # Fallback: chunk the full text into segments for embedding
    if not qna_pairs:
        logger.info(f"No Q&A pattern found in '{title}', falling back to text chunking")
        chunks = _chunk_text(text, chunk_size=800, overlap=100)
        for i, chunk in enumerate(chunks):
            qna_pairs.append({
                "question": "",
                "answer": "",
                "topic": title,
                "raw_text": chunk,
            })

    return qna_pairs


def _extract_topic(text: str) -> str:
    """Extract a short topic label from question text."""
    # Take first sentence or first 100 chars
    first_sentence = re.split(r"[.?!\n]", text)[0].strip()
    if len(first_sentence) > 100:
        return first_sentence[:100] + "..."
    return first_sentence


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


# Singleton
_confluence_client = None


def get_confluence_client() -> ConfluenceClient:
    """Get or create the global Confluence client instance."""
    global _confluence_client
    if _confluence_client is None:
        _confluence_client = ConfluenceClient()
    return _confluence_client
