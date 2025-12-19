"""
Target Analyzer Individual Section Endpoints - 12 independent endpoints for maximum flexibility
Each section can be called independently for iterative improvements and updates
"""
import logging
import json
import base64
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from google import genai
from google.genai import types

from backend.app.config import settings
from backend.app.api.routes.auth import get_current_user
from backend.app.utils.aws_secrets import get_key
from backend.app.api.routes.target_analyzer import (
    TargetAnalysisRequest,
    BiologicalOverview,
    TherapeuticRationale,
    PreClinicalEvidence,
    DrugTrialLandscape,
    PatentIP,
    IndicationPotential,
    Differentiation,
    UnmetNeeds,
    IndicationSpecificAnalysis,
    Risks,
    BiomarkerStrategy,
    BDPotentials,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Standard citation requirements for all prompts
CITATION_REQUIREMENTS = """
## CITATION INSTRUCTIONS:

**You may include citations to support your claims. Citations can be:**
- PubMed IDs (PMID: 12345678)
- DOIs
- arXiv IDs
- Other scientific references

**For PubMed citations:**
- Use google_search to find relevant papers
- Include inline citations in format: "Statement (PMID: 12345678)"
- Citations will be automatically validated for relevance

**Quality over quantity - only cite if you have strong supporting evidence.**
"""


def fetch_paper_details(pmid: str) -> dict:
    """
    Fetch paper title and abstract from PubMed via NCBI E-utilities API.
    Returns dict with title, abstract, and authors.
    """
    if not pmid or not pmid.strip() or not pmid.isdigit():
        return None

    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": pmid.strip(),
            "retmode": "xml",
            "email": "api@example.com"
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            # Parse XML to extract title and abstract
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)

            # Extract title
            title_elem = root.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "No title found"

            # Extract abstract
            abstract_parts = root.findall(".//AbstractText")
            abstract = " ".join([part.text for part in abstract_parts if part.text]) if abstract_parts else "No abstract available"

            # Extract first author
            first_author_elem = root.find(".//Author[1]/LastName")
            first_author = first_author_elem.text if first_author_elem is not None else "Unknown"

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "first_author": first_author
            }
        else:
            logger.warning(f"Failed to fetch PMID {pmid}: HTTP {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching paper details for PMID {pmid}: {e}")
        return None


def audit_citation(claim: str, pmid: str, paper_details: dict, gemini_client) -> dict:
    """
    Use Gemini 3 Flash to validate if a PMID actually supports the claim.
    Returns dict with 'valid' (bool), 'reason' (str), and 'confidence' (str).
    """
    if not paper_details:
        return {"valid": False, "reason": "Paper not found in PubMed", "confidence": "high"}

    try:
        audit_prompt = f"""You are a STRICT scientific fact-checking bot. Your job is to validate citations with HIGH STANDARDS.

**User's Claim:** "{claim}"

**Proposed Citation:** PMID: {pmid}

**Actual Paper Details from PubMed API:**
- Title: {paper_details['title']}
- First Author: {paper_details['first_author']}
- Abstract: {paper_details['abstract'][:800]}

**STRICT VALIDATION RULES:**
1. The paper must DIRECTLY support the ENTIRE claim, not just part of it
2. If the claim has multiple parts (e.g., "X is conserved AND Y shows efficacy"), the paper must address ALL parts
3. General papers about the topic are NOT sufficient - must be SPECIFIC to this exact claim
4. Review papers that mention the topic in passing are NOT sufficient
5. Papers about related proteins/pathways are NOT sufficient unless they specifically discuss this target

**Classification (choose ONE):**
- VALID: Paper directly and specifically supports THE ENTIRE claim
- INVALID_PARTIAL: Paper supports only PART of a multi-part claim (reject these)
- INVALID_UNRELATED: Paper is about a completely different topic
- INVALID_TANGENTIAL: Paper mentions the topic but doesn't support this specific claim
- INVALID_GENERAL: General review, not specific primary evidence

**Output ONLY a JSON object:**
{{"valid": true/false, "reason": "explain what paper discusses vs what claim states", "confidence": "high/medium/low"}}

Be STRICT. When in doubt, mark as INVALID."""

        response = gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=audit_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1  # Low temperature for consistency
            )
        )

        if response.text:
            result = json.loads(response.text)
            return result
        else:
            return {"valid": False, "reason": "Auditor failed to respond", "confidence": "low"}

    except Exception as e:
        logger.error(f"Error auditing citation PMID {pmid}: {e}")
        return {"valid": False, "reason": f"Audit error: {str(e)}", "confidence": "low"}


def validate_and_audit_pmids(text: str, context: str, gemini_client) -> str:
    """
    Extract PMIDs from text, validate and audit them, remove invalid ones.
    Returns cleaned text with only valid PMIDs.
    """
    import re

    # Find all PMIDs in format (PMID: 12345678) or PMID: 12345678
    pmid_pattern = r'\(?\s*PMID:\s*(\d+)\s*\)?'
    matches = list(re.finditer(pmid_pattern, text, re.IGNORECASE))

    if not matches:
        return text  # No PMIDs to validate

    # Process each PMID
    cleaned_text = text
    for match in reversed(matches):  # Reverse to maintain string positions
        pmid = match.group(1)

        # Extract the claim (sentence containing the PMID)
        # Find sentence boundaries
        sentence_start = text.rfind('.', 0, match.start()) + 1
        sentence_end = text.find('.', match.end())
        if sentence_end == -1:
            sentence_end = len(text)
        claim = text[sentence_start:sentence_end].strip()

        # Fetch paper details
        paper_details = fetch_paper_details(pmid)

        if not paper_details:
            # PMID doesn't exist - remove it
            logger.warning(f"Removing non-existent PMID {pmid} from text")
            cleaned_text = cleaned_text[:match.start()] + cleaned_text[match.end():]
            continue

        # Audit the citation
        audit_result = audit_citation(claim, pmid, paper_details, gemini_client)

        if not audit_result.get('valid', False):
            logger.warning(f"Removing invalid PMID {pmid}: {audit_result.get('reason')}")
            cleaned_text = cleaned_text[:match.start()] + cleaned_text[match.end():]
        else:
            logger.info(f"✓ PMID {pmid} validated: {audit_result.get('reason')}")

    return cleaned_text


def validate_pmid(pmid: str) -> bool:
    """
    Validate that a PMID exists in PubMed.
    Returns True if valid, False otherwise.
    """
    if not pmid or not pmid.strip() or not pmid.isdigit():
        return True  # Empty or non-numeric PMIDs pass (will be filtered later)

    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {
            "db": "pubmed",
            "id": pmid.strip(),
            "retmode": "json",
            "email": "api@example.com"  # NCBI requests an email for API usage
        }
        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            # Check if the PMID exists (no error in response)
            if "error" in data:
                logger.warning(f"Invalid PMID {pmid}: {data['error']}")
                return False
            if "result" in data and pmid in data["result"]:
                return True
            logger.warning(f"PMID {pmid} not found in PubMed")
            return False
    except Exception as e:
        logger.error(f"Error validating PMID {pmid}: {e}")
        # On error, assume valid to avoid blocking (but log the error)
        return True

    return False


def get_gemini_client():
    """Helper to initialize Gemini client"""
    gemini_api_key = None
    try:
        gemini_api_key = get_key("googleai-api-key", settings.AWS_REGION)
        logger.info("Using Gemini API key from AWS Secrets Manager")
    except Exception as e:
        logger.warning(f"Could not load Gemini API key from AWS Secrets Manager: {str(e)}")
        gemini_api_key = settings.GEMINI_API_KEY
        if gemini_api_key:
            logger.info("Using Gemini API key from environment variable")

    if not gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API key not configured"
        )

    return genai.Client(api_key=gemini_api_key)


# Response models for individual sections
class BiologicalOverviewResponse(BaseModel):
    biological_overview: BiologicalOverview
    target: str
    indication: str


class TherapeuticRationaleResponse(BaseModel):
    therapeutic_rationale: TherapeuticRationale
    target: str
    indication: str


class PreclinicalEvidenceResponse(BaseModel):
    preclinical_evidence: PreClinicalEvidence
    target: str
    indication: str


class DrugTrialLandscapeResponse(BaseModel):
    drug_trial_landscape: DrugTrialLandscape
    target: str
    indication: str


class PatentIPResponse(BaseModel):
    patent_ip: PatentIP
    target: str
    indication: str


class IndicationPotentialResponse(BaseModel):
    indication_potential: IndicationPotential
    target: str
    indication: str


class DifferentiationResponse(BaseModel):
    differentiation: Differentiation
    target: str
    indication: str


class UnmetNeedsResponse(BaseModel):
    unmet_needs: UnmetNeeds
    target: str
    indication: str


class IndicationSpecificAnalysisResponse(BaseModel):
    indication_specific_analysis: IndicationSpecificAnalysis
    target: str
    indication: str


class RisksResponse(BaseModel):
    risks: Risks
    target: str
    indication: str


class BiomarkerStrategyResponse(BaseModel):
    biomarker_strategy: BiomarkerStrategy
    target: str
    indication: str


class BDPotentialsResponse(BaseModel):
    bd_potentials: BDPotentials
    target: str
    indication: str


# Endpoint 1: Biological Overview
@router.post("/biological-overview", response_model=BiologicalOverviewResponse)
async def analyze_biological_overview(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Biological Overview: Structure, mechanism, validation, conservation"""
    try:
        logger.info(f"Analyzing biological overview for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "structural_domains": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "name": types.Schema(type=types.Type.STRING),
                            "description": types.Schema(type=types.Type.STRING),
                        },
                        required=["name", "description"]
                    )
                ),
                "mechanistic_insights": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING)
                ),
                "human_validation": types.Schema(type=types.Type.STRING),
                "human_validation_pmid": types.Schema(type=types.Type.STRING),
                "species_conservation": types.Schema(type=types.Type.STRING),
                "species_conservation_pmid": types.Schema(type=types.Type.STRING),
            },
            required=["structural_domains", "mechanistic_insights", "human_validation", "species_conservation"]
        )

        prompt = f"""
You are a world-class drug development expert analyzing BIOLOGICAL OVERVIEW for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Use 'google_search' tool extensively to find ALL relevant biological data.

**STAGE 2: FOCUSED EXTRACTION**
Apply QUALITY GATES: MATERIALITY, SPECIFICITY, QUANTIFICATION, ACTIONABILITY

---

### Biological Overview

**EXTENSIVE RESEARCH - Target Structure & Mechanism:**
- Complete protein structure, all functional domains
- Full mechanism of action pathway
- All interacting proteins and downstream effects
- Tissue expression patterns and cellular localization

**FOCUSED EXTRACTION:**

**Structural Domains** (3-5 key domains):
For each domain provide:
- Domain name
- Functional role and druggability assessment

**Mechanistic Insights** (4-6 sequential steps):
Provide step-by-step mechanism in causality chain format. Each step should be:
- Specific molecular event (not vague)
- Quantified where possible (e.g., "50% reduction in...")
- Include inline PubMed citations in format: "Statement (PMID: 12345678)" for key steps
- ONLY cite if google_search returned this specific paper for this specific claim

**Human Validation:**
Evidence from human studies/genetics that target modulation affects disease.
Use google_search to find the PRIMARY research paper that demonstrates this.
Provide PMID only if you found it via google_search and verified it discusses this specific finding.

**Species Conservation:**
Cross-species conservation analysis and implications for animal model translation.
Provide PMID only if google_search returned a paper specifically about conservation of THIS target.

---
{CITATION_REQUIREMENTS}
---

## OUTPUT REQUIREMENTS:
- **QUANTIFICATION**: Use numbers, not "better/worse"
- **CITATIONS**: Include PMIDs ONLY when you have verified them via google_search
- **SPECIFICITY**: Everything must be specific to {request.target} in {request.indication}

## SELF-VERIFICATION STEP (MANDATORY):
Before finalizing your response, perform this sanity check:
1. For each PMID you listed, verify: Did google_search return this PMID for THIS specific claim?
2. Does the paper's title/abstract directly discuss the EXACT claim you're making?
3. If you're unsure or if the paper is only tangentially related, REMOVE the PMID and leave it empty.
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        # STEP 2 & 3: Validate and Audit PMIDs using Writer-Auditor pattern
        logger.info("Starting PMID validation and auditing...")

        # Audit mechanistic insights (inline PMIDs in text)
        if data.get("mechanistic_insights"):
            audited_insights = []
            for insight in data["mechanistic_insights"]:
                context = f"Mechanism of action for {request.target} in {request.indication}"
                cleaned_insight = validate_and_audit_pmids(insight, context, client)
                audited_insights.append(cleaned_insight)
            data["mechanistic_insights"] = audited_insights

        # Audit human_validation_pmid
        if data.get("human_validation_pmid"):
            pmid = data["human_validation_pmid"]
            paper_details = fetch_paper_details(pmid)
            if paper_details:
                claim = data.get("human_validation", "Human validation of target")
                audit_result = audit_citation(claim, pmid, paper_details, client)
                if not audit_result.get('valid', False):
                    logger.warning(f"Removing invalid human_validation_pmid {pmid}: {audit_result.get('reason')}")
                    data["human_validation_pmid"] = ""
                else:
                    logger.info(f"✓ human_validation_pmid {pmid} validated")
            else:
                logger.warning(f"Removing non-existent human_validation_pmid {pmid}")
                data["human_validation_pmid"] = ""

        # Audit species_conservation_pmid
        if data.get("species_conservation_pmid"):
            pmid = data["species_conservation_pmid"]
            paper_details = fetch_paper_details(pmid)
            if paper_details:
                claim = data.get("species_conservation", "Species conservation of target")
                audit_result = audit_citation(claim, pmid, paper_details, client)
                if not audit_result.get('valid', False):
                    logger.warning(f"Removing invalid species_conservation_pmid {pmid}: {audit_result.get('reason')}")
                    data["species_conservation_pmid"] = ""
                else:
                    logger.info(f"✓ species_conservation_pmid {pmid} validated")
            else:
                logger.warning(f"Removing non-existent species_conservation_pmid {pmid}")
                data["species_conservation_pmid"] = ""

        logger.info("PMID validation and auditing complete")

        # Generate mechanism diagram
        mechanism_image = None
        try:
            mechanism_text = " → ".join(data["mechanistic_insights"])
            image_prompt = f"""Scientific schematic diagram illustrating the biological mechanism of action for {request.target}.
Steps to illustrate: {mechanism_text}.
Style: Clean, professional, textbook medical illustration, white background, high resolution, schematic.
Labels should be legible and use standard scientific font."""

            try:
                image_response = client.models.generate_content(
                    model="gemini-3-pro-image-preview",
                    contents=image_prompt
                )

                if image_response and hasattr(image_response, 'candidates'):
                    for candidate in image_response.candidates:
                        if hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'inline_data'):
                                    mechanism_image = base64.b64encode(part.inline_data.data).decode('utf-8')
                                    mechanism_image = f"data:{part.inline_data.mime_type};base64,{mechanism_image}"
                                    logger.info("Successfully generated mechanism diagram")
                                    break
                        if mechanism_image:
                            break
            except Exception as e:
                logger.warning(f"Failed to generate mechanism diagram: {e}")

        except Exception as e:
            logger.warning(f"Failed to prepare mechanism diagram: {e}")

        data["mechanism_image"] = mechanism_image

        result = {
            "biological_overview": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed biological overview for {request.target}")
        return BiologicalOverviewResponse(**result)

    except Exception as e:
        logger.error(f"Biological overview analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 2: Therapeutic Rationale
@router.post("/therapeutic-rationale", response_model=TherapeuticRationaleResponse)
async def analyze_therapeutic_rationale(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Therapeutic Rationale: Pathway positioning, specificity, modality comparison"""
    try:
        logger.info(f"Analyzing therapeutic rationale for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "pathway_positioning": types.Schema(type=types.Type.STRING),
                "specificity_vs_breadth": types.Schema(type=types.Type.STRING),
                "modality_comparison": types.Schema(type=types.Type.STRING),
            },
            required=["pathway_positioning", "specificity_vs_breadth", "modality_comparison"]
        )

        prompt = f"""
You are a world-class drug development expert analyzing THERAPEUTIC RATIONALE for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
- Analyze complete disease pathway
- All potential intervention points
- Historical precedents for pathway modulation
- Compare ALL therapeutic modalities (small molecule, antibody, gene therapy, etc.)

**STAGE 2: FOCUSED EXTRACTION**

**Pathway Positioning:**
Where in disease cascade does this target act? How upstream/downstream?
Compare to approved drugs - is positioning more optimal?

**Specificity vs Breadth:**
Target selectivity trade-offs. Specific advantages/disadvantages vs broader targets.
Quantify: "10x more selective than [competitor]" not "very selective"

**Modality Comparison:**
Why small molecule vs antibody vs other modalities for THIS target?
Specific PK/PD, tissue penetration, or mechanism rationale.

---
{CITATION_REQUIREMENTS}
---

## OUTPUT REQUIREMENTS:
- **QUANTIFICATION**: Use numbers, not "better/worse"
- **CITATIONS**: Include PMIDs ONLY when verified via google_search
- **SPECIFICITY**: Everything must be specific to {request.target} in {request.indication}
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "therapeutic_rationale": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed therapeutic rationale for {request.target}")
        return TherapeuticRationaleResponse(**result)

    except Exception as e:
        logger.error(f"Therapeutic rationale analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 3: Preclinical Evidence
@router.post("/preclinical-evidence", response_model=PreclinicalEvidenceResponse)
async def analyze_preclinical_evidence(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Preclinical Evidence: Human genetics and animal models"""
    try:
        logger.info(f"Analyzing preclinical evidence for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "human_genetics": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "monogenic_mutations": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "variant": types.Schema(type=types.Type.STRING),
                                    "phenotype": types.Schema(type=types.Type.STRING),
                                    "pmid": types.Schema(type=types.Type.STRING),
                                    "evidence_quality": types.Schema(type=types.Type.STRING),
                                    "effect_size": types.Schema(type=types.Type.STRING),
                                    "benchmark_comparison": types.Schema(type=types.Type.STRING),
                                },
                                required=["variant", "phenotype"]
                            )
                        ),
                        "common_variants": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "variant": types.Schema(type=types.Type.STRING),
                                    "association": types.Schema(type=types.Type.STRING),
                                    "pmid": types.Schema(type=types.Type.STRING),
                                    "evidence_quality": types.Schema(type=types.Type.STRING),
                                    "statistical_significance": types.Schema(type=types.Type.STRING),
                                    "benchmark_comparison": types.Schema(type=types.Type.STRING),
                                },
                                required=["variant", "association"]
                            )
                        ),
                    },
                    required=["monogenic_mutations", "common_variants"]
                ),
                "animal_models": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "loss_of_function": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "model": types.Schema(type=types.Type.STRING),
                                    "outcome": types.Schema(type=types.Type.STRING),
                                    "pmid": types.Schema(type=types.Type.STRING),
                                    "evidence_quality": types.Schema(type=types.Type.STRING),
                                    "phenotype_magnitude": types.Schema(type=types.Type.STRING),
                                    "benchmark_comparison": types.Schema(type=types.Type.STRING),
                                },
                                required=["model", "outcome"]
                            )
                        ),
                        "gain_of_function": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "model": types.Schema(type=types.Type.STRING),
                                    "outcome": types.Schema(type=types.Type.STRING),
                                    "pmid": types.Schema(type=types.Type.STRING),
                                    "evidence_quality": types.Schema(type=types.Type.STRING),
                                    "benchmark_comparison": types.Schema(type=types.Type.STRING),
                                },
                                required=["model", "outcome"]
                            )
                        ),
                    },
                    required=["loss_of_function", "gain_of_function"]
                ),
            },
            required=["human_genetics", "animal_models"]
        )

        prompt = f"""
You are a world-class drug development expert analyzing PRECLINICAL EVIDENCE for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH - Genetic & Animal Evidence:**
Comprehensively search for ALL available evidence:
- Every published genetic association (GWAS, rare variants, monogenic)
- All animal knockout/knockin studies across species
- Historical precedents for similar targets
- Evidence quality and statistical rigor

**STAGE 2: FOCUSED EXTRACTION - Evidence Benchmarking:**

**Human Genetic Evidence:**

*Monogenic Gain-of-Function Mutations:*
For each variant provide:
- variant ID, phenotype, PMID
- **EVIDENCE QUALITY**: High/Medium/Low (based on replication, sample size)
- **EFFECT SIZE**: e.g., "OR=3.2, penetrance=95%"
- **BENCHMARK**: How does effect size compare to approved targets? "2x larger than typical"

*Common/Low-Frequency Variant Associations:*
For each provide:
- variant, association, PMID
- **EVIDENCE QUALITY**: High/Medium/Low
- **STATISTICAL SIGNIFICANCE**: e.g., "p=3e-8, genome-wide significant"
- **BENCHMARK**: e.g., "Top 10% of GWAS strength vs approved precedents"

**Preclinical Animal Studies:**

*Loss-of-Function Models:*
For each provide:
- model, outcome, PMID
- **EVIDENCE QUALITY**: High/Medium/Low
- **PHENOTYPE MAGNITUDE**: e.g., "60% disease reduction"
- **BENCHMARK**: e.g., "2x stronger than approved precedent (30% typical)"

*Gain-of-Function Models:*
For each provide:
- model, outcome, PMID
- **EVIDENCE QUALITY**: High/Medium/Low
- **BENCHMARK**: Comparison to approved precedents

**EFFICACY BAR ANALYSIS:**
Based on mechanism precedents (similar targets that succeeded/failed):
- Minimum genetic evidence bar for clinical success
- Minimum animal phenotype magnitude for translation
- This target's position: "Exceeds bar by X%" or "Falls short by Y%"
- Assessment: ABOVE BENCHMARK / AT BENCHMARK / BELOW BENCHMARK

---
{CITATION_REQUIREMENTS}
---

## OUTPUT REQUIREMENTS:
- **QUANTIFICATION**: Use numbers, not "better/worse"
- **CITATIONS**: Include PMIDs ONLY when you have verified them via google_search
- **SPECIFICITY**: Everything must be specific to {request.target} in {request.indication}
- **QUALITY RATINGS**: Rate evidence quality (High/Medium/Low)
- **BENCHMARKING**: Compare to approved targets with quantified gaps
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        # Validate all PMIDs in preclinical evidence
        for mutation in data.get("human_genetics", {}).get("monogenic_mutations", []):
            if mutation.get("pmid") and not validate_pmid(mutation["pmid"]):
                logger.warning(f"Removing invalid PMID: {mutation['pmid']}")
                mutation["pmid"] = ""

        for variant in data.get("human_genetics", {}).get("common_variants", []):
            if variant.get("pmid") and not validate_pmid(variant["pmid"]):
                logger.warning(f"Removing invalid PMID: {variant['pmid']}")
                variant["pmid"] = ""

        for model in data.get("animal_models", {}).get("loss_of_function", []):
            if model.get("pmid") and not validate_pmid(model["pmid"]):
                logger.warning(f"Removing invalid PMID: {model['pmid']}")
                model["pmid"] = ""

        for model in data.get("animal_models", {}).get("gain_of_function", []):
            if model.get("pmid") and not validate_pmid(model["pmid"]):
                logger.warning(f"Removing invalid PMID: {model['pmid']}")
                model["pmid"] = ""

        result = {
            "preclinical_evidence": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed preclinical evidence for {request.target}")
        return PreclinicalEvidenceResponse(**result)

    except Exception as e:
        logger.error(f"Preclinical evidence analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 4: Drug Trial Landscape
@router.post("/drug-trial-landscape", response_model=DrugTrialLandscapeResponse)
async def analyze_drug_trial_landscape(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Drug Trial Landscape: Competitive trials and pipeline"""
    try:
        logger.info(f"Analyzing drug trial landscape for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "summary": types.Schema(type=types.Type.STRING),
                "competitors": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "company": types.Schema(type=types.Type.STRING),
                            "molecule_name": types.Schema(type=types.Type.STRING),
                            "phase": types.Schema(type=types.Type.STRING),
                            "mechanism": types.Schema(type=types.Type.STRING),
                        },
                        required=["company", "molecule_name", "phase", "mechanism"]
                    )
                ),
                "phase_count": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "preclinical": types.Schema(type=types.Type.INTEGER),
                        "phase1": types.Schema(type=types.Type.INTEGER),
                        "phase2": types.Schema(type=types.Type.INTEGER),
                        "phase3": types.Schema(type=types.Type.INTEGER),
                        "approved": types.Schema(type=types.Type.INTEGER),
                    },
                    required=["preclinical", "phase1", "phase2", "phase3", "approved"]
                ),
            },
            required=["summary", "competitors", "phase_count"]
        )

        prompt = f"""
You are a world-class competitive intelligence analyst analyzing DRUG/TRIAL LANDSCAPE for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Search for ALL clinical trials, approved drugs, and pipeline assets targeting this molecule or pathway.

**STAGE 2: FOCUSED EXTRACTION**

**Summary:**
Current competitive intensity (crowded/moderate/sparse)

**Competitors:**
Top 8-12 competitive assets with:
- Company name
- Molecule name
- Development phase
- Mechanism of action

**Phase Distribution:**
Count of assets in each phase:
- Preclinical
- Phase 1
- Phase 2
- Phase 3
- Approved

---

## OUTPUT REQUIREMENTS:
- **QUANTIFICATION**: Specific numbers
- **SPECIFICITY**: Focus on {request.target} in {request.indication}
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "drug_trial_landscape": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed drug trial landscape for {request.target}")
        return DrugTrialLandscapeResponse(**result)

    except Exception as e:
        logger.error(f"Drug trial landscape analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 5: Patent IP
@router.post("/patent-ip", response_model=PatentIPResponse)
async def analyze_patent_ip(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Patent & IP Landscape: Recent filings and strategy"""
    try:
        logger.info(f"Analyzing patent IP for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "recent_filings": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "assignee": types.Schema(type=types.Type.STRING),
                            "year": types.Schema(type=types.Type.STRING),
                            "focus": types.Schema(type=types.Type.STRING),
                        },
                        required=["assignee", "year", "focus"]
                    )
                ),
                "strategy": types.Schema(type=types.Type.STRING),
            },
            required=["recent_filings", "strategy"]
        )

        prompt = f"""
You are a world-class IP analyst analyzing PATENT & IP LANDSCAPE for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Search patent databases for recent filings related to this target.

**STAGE 2: FOCUSED EXTRACTION**

**Recent Filings:**
5-8 recent patent filings with:
- Assignee (company/institution)
- Year filed
- Focus area (what the patent covers)

**IP Strategy:**
Implications for freedom to operate.
Are there blocking patents? Clear IP space? Crowded landscape?

---

## OUTPUT REQUIREMENTS:
- **SPECIFICITY**: Focus on {request.target} in {request.indication}
- **ACTIONABILITY**: What does this mean for IP strategy?
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "patent_ip": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed patent IP for {request.target}")
        return PatentIPResponse(**result)

    except Exception as e:
        logger.error(f"Patent IP analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 6: Indication Potential
@router.post("/indication-potential", response_model=IndicationPotentialResponse)
async def analyze_indication_potential(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Indication Potential: Market attractiveness score"""
    try:
        logger.info(f"Analyzing indication potential for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "score": types.Schema(type=types.Type.INTEGER),
                "reasoning": types.Schema(type=types.Type.STRING),
            },
            required=["score", "reasoning"]
        )

        prompt = f"""
You are a world-class market analyst analyzing INDICATION POTENTIAL for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Analyze disease burden, addressable market, clinical precedent success rates for this target class.

**STAGE 2: FOCUSED EXTRACTION**

**Score:**
0-10 for target-indication attractiveness
(0=not viable, 5=moderate, 10=exceptional)

**Reasoning:**
Quantified metrics:
- Disease prevalence (number of patients)
- Market size ($ billions)
- Current treatment gaps
- Precedent success rates for this target class
- Regulatory pathway clarity

---

## OUTPUT REQUIREMENTS:
- **QUANTIFICATION**: Use specific numbers
- **SPECIFICITY**: Focus on {request.target} in {request.indication}
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "indication_potential": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed indication potential for {request.target}")
        return IndicationPotentialResponse(**result)

    except Exception as e:
        logger.error(f"Indication potential analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 7: Differentiation
@router.post("/differentiation", response_model=DifferentiationResponse)
async def analyze_differentiation(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Key Differentiation: Competitive advantages and positioning"""
    try:
        logger.info(f"Analyzing differentiation for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "analysis": types.Schema(type=types.Type.STRING),
                "efficacy_safety_position": types.Schema(type=types.Type.STRING),
                "quantified_gaps": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING)
                ),
                "competitive_scenarios": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "scenario": types.Schema(type=types.Type.STRING),
                            "probability": types.Schema(type=types.Type.STRING),
                            "impact": types.Schema(type=types.Type.STRING),
                            "strategic_response": types.Schema(type=types.Type.STRING),
                        },
                        required=["scenario", "probability", "impact", "strategic_response"]
                    )
                ),
                "advantages": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "disadvantages": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
            },
            required=["analysis", "advantages", "disadvantages"]
        )

        prompt = f"""
You are a world-class competitive analyst analyzing KEY DIFFERENTIATION for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Comprehensive competitive analysis across all dimensions:
- Mechanism differentiation
- Safety/efficacy profiles from preclinical/clinical data
- Patient population targeting
- Competitive scenarios and probabilities

**STAGE 2: FOCUSED EXTRACTION**

**1. EFFICACY/SAFETY FRONTIER ANALYSIS:**
Position on efficacy/safety trade-off matrix:
- **Position**: ON/ABOVE/BELOW competitive frontier
- **QUANTIFIED GAPS**: e.g., "2x better efficacy (60% vs 30%) but 20% more Grade 3/4 AEs"

**2. QUANTIFIED COMPETITIVE GAPS:**
List 3-5 specific quantified advantages:
- ✅ "2x better tissue penetration (IC50=0.5nM vs 1.2nM for [competitor])"
- ❌ NOT "Better tissue penetration"

**3. COMPETITIVE SCENARIOS:**
Model 2-4 key competitive developments:
- Scenario: "[Competitor X] succeeds in Phase 3"
- Probability: "40%" (based on mechanism precedent, Phase 2 data)
- Impact: Specific impact on positioning
- Strategic Response: How to differentiate

**4. ADVANTAGES/DISADVANTAGES:**
- Advantages: 3-5 specific differentiators
- Disadvantages: 3-5 specific challenges vs competition

---

## OUTPUT REQUIREMENTS:
- **QUANTIFICATION**: Use numbers, not "better/worse"
- **SPECIFICITY**: Focus on {request.target} in {request.indication}
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "differentiation": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed differentiation for {request.target}")
        return DifferentiationResponse(**result)

    except Exception as e:
        logger.error(f"Differentiation analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 8: Unmet Needs
@router.post("/unmet-needs", response_model=UnmetNeedsResponse)
async def analyze_unmet_needs(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Unmet Medical Needs: Treatment gaps"""
    try:
        logger.info(f"Analyzing unmet needs for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "response_rates": types.Schema(type=types.Type.STRING),
                "resistance": types.Schema(type=types.Type.STRING),
                "safety_limitations": types.Schema(type=types.Type.STRING),
                "adherence_challenges": types.Schema(type=types.Type.STRING),
            },
            required=["response_rates", "resistance", "safety_limitations", "adherence_challenges"]
        )

        prompt = f"""
You are a world-class clinical analyst analyzing UNMET MEDICAL NEEDS for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Comprehensive analysis of current treatment landscape and gaps.

**STAGE 2: FOCUSED EXTRACTION**

For each dimension, provide quantified unmet needs:

**Response Rates:**
% of patients who don't respond to current therapies
Specific numbers and benchmarks

**Resistance:**
Mechanisms and prevalence of treatment resistance
How many patients develop resistance? How quickly?

**Safety Limitations:**
% with severe adverse events
Monitoring burdens
Dose-limiting toxicities

**Adherence Challenges:**
Quantified compliance issues
Barriers to adherence (dosing frequency, route, monitoring)

---

## OUTPUT REQUIREMENTS:
- **QUANTIFICATION**: Use specific numbers and percentages
- **SPECIFICITY**: Focus on {request.target} in {request.indication}
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "unmet_needs": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed unmet needs for {request.target}")
        return UnmetNeedsResponse(**result)

    except Exception as e:
        logger.error(f"Unmet needs analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 9: Indication Specific Analysis
@router.post("/indication-specific-analysis", response_model=IndicationSpecificAnalysisResponse)
async def analyze_indication_specific(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Indication Specific Analysis: Therapeutic classes and guidelines"""
    try:
        logger.info(f"Analyzing indication specific for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "therapeutic_classes": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "class_name": types.Schema(type=types.Type.STRING),
                            "examples": types.Schema(type=types.Type.STRING),
                        },
                        required=["class_name", "examples"]
                    )
                ),
                "treatment_guidelines": types.Schema(type=types.Type.STRING),
            },
            required=["therapeutic_classes", "treatment_guidelines"]
        )

        prompt = f"""
You are a world-class clinical analyst analyzing INDICATION-SPECIFIC landscape for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Comprehensive analysis of therapeutic landscape and treatment guidelines.

**STAGE 2: FOCUSED EXTRACTION**

**Therapeutic Classes:**
4-6 major drug classes currently used with:
- Class name
- Example drugs

**Treatment Guidelines:**
Current standard of care and sequencing
1st line, 2nd line, 3rd line treatments
Which guidelines? (NCCN, ASCO, etc.)

---

## OUTPUT REQUIREMENTS:
- **SPECIFICITY**: Focus on {request.indication}
- **CLINICAL RELEVANCE**: Real-world practice patterns
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "indication_specific_analysis": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed indication specific for {request.target}")
        return IndicationSpecificAnalysisResponse(**result)

    except Exception as e:
        logger.error(f"Indication specific analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 10: Risks
@router.post("/risks", response_model=RisksResponse)
async def analyze_risks(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Target-Specific Risks: Comprehensive risk assessment"""
    try:
        logger.info(f"Analyzing risks for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "risk_items": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "category": types.Schema(type=types.Type.STRING),
                            "description": types.Schema(type=types.Type.STRING),
                            "probability": types.Schema(type=types.Type.INTEGER),
                            "impact": types.Schema(type=types.Type.INTEGER),
                            "timeline": types.Schema(type=types.Type.STRING),
                            "early_warning_signals": types.Schema(type=types.Type.STRING),
                            "mitigation_strategies": types.Schema(type=types.Type.STRING),
                            "evidence_quality": types.Schema(type=types.Type.STRING),
                        },
                        required=["category", "description", "probability", "impact", "timeline", "early_warning_signals", "mitigation_strategies", "evidence_quality"]
                    )
                ),
                "summary": types.Schema(type=types.Type.STRING),
            },
            required=["risk_items", "summary"]
        )

        prompt = f"""
You are a world-class risk analyst conducting TARGET-SPECIFIC RISK ASSESSMENT for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Exhaustively analyze ALL potential risks:
- Every mechanism-related safety concern from precedent targets
- All technical druggability challenges
- Complete competitive landscape threats
- Historical failure modes for this target class

**STAGE 2: FOCUSED EXTRACTION - MATERIALITY GATES**

**ONLY EXTRACT RISKS IF:**
1. Probability >20% AND material impact on viability
   OR
2. Mechanism-breaking risk regardless of probability

**SPECIFICITY - MUST BE TARGET-SPECIFIC:**

❌ EXCLUDE GENERIC RISKS:
- "Clinical trials may fail"
- "Safety signals possible"
- "Competition exists"

✅ INCLUDE ONLY TARGET/MECHANISM-SPECIFIC RISKS:
- "High affinity (Kd=0.1nM) may limit tissue penetration"
- "Prior Class X inhibitor showed QT prolongation in 15%"
- "Compensatory pathway Y upregulates 3-fold when target inhibited >80%"

**QUALITY THRESHOLD:**
Aim for 5-10 deeply analyzed, target-specific risks (NOT 20+ generic ones)

For each risk provide:
- **Category**: Clinical/Safety/Competitive/Technical/Regulatory
- **Description**: Specific mechanism explaining WHY this risk exists for THIS target
- **Probability**: 0-100% probability of occurrence
- **Impact**: 0-100 impact score (100=program-killing)
- **Timeline**: When risk could materialize
- **Early Warning Signals**: Specific biomarkers/findings to monitor
- **Mitigation Strategies**: Actionable steps to reduce risk
- **Evidence Quality**: High/Medium/Low

**Summary**: Executive summary highlighting what's UNIQUE about this risk profile

---

## OUTPUT REQUIREMENTS:
- **QUANTIFICATION**: Use specific probabilities and impact scores
- **SPECIFICITY**: Only target-specific risks, NO generic risks
- **ACTIONABILITY**: Clear mitigation strategies
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "risks": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed risks for {request.target}")
        return RisksResponse(**result)

    except Exception as e:
        logger.error(f"Risks analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 11: Biomarker Strategy
@router.post("/biomarker-strategy", response_model=BiomarkerStrategyResponse)
async def analyze_biomarker_strategy(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Biomarker Strategy: Patient stratification and trial design"""
    try:
        logger.info(f"Analyzing biomarker strategy for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "stratification_biomarkers": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING)
                ),
                "adaptive_design": types.Schema(type=types.Type.STRING),
            },
            required=["stratification_biomarkers", "adaptive_design"]
        )

        prompt = f"""
You are a world-class clinical development expert analyzing BIOMARKER STRATEGY for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Identify all potential stratification biomarkers and adaptive design opportunities.

**STAGE 2: FOCUSED EXTRACTION**

**Stratification Biomarkers:**
3-6 biomarkers for patient selection:
- Biomarker name
- What it measures
- Why it predicts response
- Validation status (exploratory/validated)

**Adaptive Design:**
Trial design considerations for biomarker-driven strategy:
- Enrichment strategies
- Basket/umbrella trial opportunities
- Adaptive randomization approaches
- Companion diagnostic requirements

---

## OUTPUT REQUIREMENTS:
- **SPECIFICITY**: Focus on {request.target} in {request.indication}
- **ACTIONABILITY**: Practical trial design recommendations
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "biomarker_strategy": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed biomarker strategy for {request.target}")
        return BiomarkerStrategyResponse(**result)

    except Exception as e:
        logger.error(f"Biomarker strategy analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# Endpoint 12: BD Potentials
@router.post("/bd-potentials", response_model=BDPotentialsResponse)
async def analyze_bd_potentials(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze Business Development & Investment: M&A and partnership opportunities"""
    try:
        logger.info(f"Analyzing BD potentials for {request.target} in {request.indication}")
        client = get_gemini_client()

        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "activities": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "company": types.Schema(type=types.Type.STRING),
                            "description": types.Schema(type=types.Type.STRING),
                        },
                        required=["company", "description"]
                    )
                ),
                "interested_parties": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
            },
            required=["activities", "interested_parties"]
        )

        prompt = f"""
You are a world-class business development analyst analyzing BD & INVESTMENT for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Recent M&A, partnerships, investments in this space.

**STAGE 2: FOCUSED EXTRACTION**

**Recent BD Activities:**
4-6 recent activities with:
- Company involved
- Description (acquisition, partnership, investment, etc.)
- Deal value if available
- Strategic rationale

**Interested Parties:**
5-8 companies/investors likely interested in this target:
- Big pharma with strategic fit
- Specialty pharma in this therapeutic area
- VCs active in this space
- Why they'd be interested

---

## OUTPUT REQUIREMENTS:
- **SPECIFICITY**: Focus on {request.target} in {request.indication}
- **STRATEGIC INSIGHT**: Why would they be interested?
"""

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated"
            )

        data = json.loads(response.text)

        result = {
            "bd_potentials": data,
            "target": request.target,
            "indication": request.indication
        }

        logger.info(f"Successfully completed BD potentials for {request.target}")
        return BDPotentialsResponse(**result)

    except Exception as e:
        logger.error(f"BD potentials analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
