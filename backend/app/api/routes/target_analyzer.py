"""
Target Analyzer API endpoints
Analyzes drug targets and indications using Gemini AI with search and image generation
"""
import logging
import json
import base64
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from backend.app.config import settings
from backend.app.api.routes.auth import get_current_user
from backend.app.utils.aws_secrets import get_key

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class TargetAnalysisRequest(BaseModel):
    """Request model for target analysis"""
    target: str = Field(..., description="Target molecule (e.g., RIPK2, JAK1)")
    indication: str = Field(..., description="Disease indication (e.g., Ulcerative Colitis)")

class Domain(BaseModel):
    name: str
    description: str

class BiologicalOverview(BaseModel):
    structural_domains: list[Domain]
    mechanistic_insights: list[str]
    human_validation: str
    species_conservation: str
    mechanism_image: Optional[str] = None  # Base64 encoded image

class TherapeuticRationale(BaseModel):
    pathway_positioning: str
    specificity_vs_breadth: str
    modality_comparison: str

class GeneticEvidence(BaseModel):
    variant: str
    significance: str

class AnimalModel(BaseModel):
    model: str
    outcome: str

class PreClinicalEvidence(BaseModel):
    human_genetics: list[GeneticEvidence]
    animal_models: list[AnimalModel]

class Competitor(BaseModel):
    company: str
    molecule_name: str
    phase: str
    mechanism: str

class PhaseCount(BaseModel):
    preclinical: int
    phase1: int
    phase2: int
    phase3: int
    approved: int

class DrugTrialLandscape(BaseModel):
    summary: str
    competitors: list[Competitor]
    phase_count: PhaseCount

class PatentFiling(BaseModel):
    assignee: str
    year: str
    focus: str

class PatentIP(BaseModel):
    recent_filings: list[PatentFiling]
    strategy: str

class Differentiation(BaseModel):
    analysis: str
    advantages: list[str]
    disadvantages: list[str]

class UnmetNeeds(BaseModel):
    response_rates: str
    resistance: str
    safety_limitations: str

class Risks(BaseModel):
    clinical: int = Field(..., description="0-100")
    safety: int = Field(..., description="0-100")
    competitive: int = Field(..., description="0-100")
    technical: int = Field(..., description="0-100")
    risk_analysis: str

class BDActivity(BaseModel):
    company: str
    description: str

class IndicationPotential(BaseModel):
    score: int = Field(..., description="0-10")
    reasoning: str

class BDPotentials(BaseModel):
    activities: list[BDActivity]
    interested_parties: list[str]

class TargetAnalysisResponse(BaseModel):
    """Response model for target analysis"""
    target: str
    indication: str
    biological_overview: BiologicalOverview
    therapeutic_rationale: TherapeuticRationale
    preclinical_evidence: PreClinicalEvidence
    drug_trial_landscape: DrugTrialLandscape
    patent_ip: PatentIP
    indication_potential: IndicationPotential
    differentiation: Differentiation
    unmet_needs: UnmetNeeds
    indication_specific_analysis: str
    risks: Risks
    biomarker_strategy: str
    bd_potentials: BDPotentials


@router.post("/analyze", response_model=TargetAnalysisResponse)
async def analyze_target(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze a drug target and indication pair using Gemini AI with search
    """
    try:
        logger.info(f"Starting target analysis for {request.target} in {request.indication}")

        # Initialize Gemini client - try AWS Secrets Manager first, then fall back to env var
        gemini_api_key = None
        try:
            # Try to get from AWS Secrets Manager (same as Unified AI Search)
            gemini_api_key = get_key("googleai-api-key", settings.AWS_REGION)
            logger.info("Using Gemini API key from AWS Secrets Manager")
        except Exception as e:
            logger.warning(f"Could not load Gemini API key from AWS Secrets Manager: {str(e)}")
            # Fall back to environment variable
            gemini_api_key = settings.GEMINI_API_KEY
            if gemini_api_key:
                logger.info("Using Gemini API key from environment variable")

        if not gemini_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gemini API key not configured. Set GEMINI_API_KEY in .env or add 'googleai-api-key' to AWS Secrets Manager"
            )

        client = genai.Client(api_key=gemini_api_key)

        # Define JSON schema for structured output
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "biological_overview": types.Schema(
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
                        "species_conservation": types.Schema(type=types.Type.STRING),
                    },
                    required=["structural_domains", "mechanistic_insights", "human_validation", "species_conservation"]
                ),
                "therapeutic_rationale": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pathway_positioning": types.Schema(type=types.Type.STRING),
                        "specificity_vs_breadth": types.Schema(type=types.Type.STRING),
                        "modality_comparison": types.Schema(type=types.Type.STRING),
                    },
                    required=["pathway_positioning", "specificity_vs_breadth", "modality_comparison"]
                ),
                "preclinical_evidence": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "human_genetics": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "variant": types.Schema(type=types.Type.STRING),
                                    "significance": types.Schema(type=types.Type.STRING),
                                },
                                required=["variant", "significance"]
                            )
                        ),
                        "animal_models": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "model": types.Schema(type=types.Type.STRING),
                                    "outcome": types.Schema(type=types.Type.STRING),
                                },
                                required=["model", "outcome"]
                            )
                        ),
                    },
                    required=["human_genetics", "animal_models"]
                ),
                "drug_trial_landscape": types.Schema(
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
                ),
                "patent_ip": types.Schema(
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
                ),
                "indication_potential": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "score": types.Schema(type=types.Type.INTEGER, description="Score from 0 to 10"),
                        "reasoning": types.Schema(type=types.Type.STRING),
                    },
                    required=["score", "reasoning"]
                ),
                "differentiation": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "analysis": types.Schema(type=types.Type.STRING),
                        "advantages": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                        "disadvantages": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                    },
                    required=["analysis", "advantages", "disadvantages"]
                ),
                "unmet_needs": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "response_rates": types.Schema(type=types.Type.STRING),
                        "resistance": types.Schema(type=types.Type.STRING),
                        "safety_limitations": types.Schema(type=types.Type.STRING),
                    },
                    required=["response_rates", "resistance", "safety_limitations"]
                ),
                "indication_specific_analysis": types.Schema(type=types.Type.STRING),
                "risks": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "clinical": types.Schema(type=types.Type.INTEGER, description="Risk score 0-100"),
                        "safety": types.Schema(type=types.Type.INTEGER, description="Risk score 0-100"),
                        "competitive": types.Schema(type=types.Type.INTEGER, description="Risk score 0-100"),
                        "technical": types.Schema(type=types.Type.INTEGER, description="Risk score 0-100"),
                        "risk_analysis": types.Schema(type=types.Type.STRING),
                    },
                    required=["clinical", "safety", "competitive", "technical", "risk_analysis"]
                ),
                "biomarker_strategy": types.Schema(type=types.Type.STRING),
                "bd_potentials": types.Schema(
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
                ),
            },
            required=[
                "biological_overview", "therapeutic_rationale", "preclinical_evidence",
                "drug_trial_landscape", "patent_ip", "indication_potential",
                "differentiation", "unmet_needs", "indication_specific_analysis",
                "risks", "biomarker_strategy", "bd_potentials"
            ]
        )

        # Create the analysis prompt
        prompt = f"""
Conduct a deep comprehensive research analysis for the drug target "{request.target}" specifically for the indication "{request.indication}".

You must use the 'google_search' tool to find the most recent clinical trials, patent filings, and business development news.

Fill out the response following the JSON schema provided.
Focus on structured data (arrays, lists) suitable for visualization rather than long paragraphs.
Keep text descriptions concise and high-density.

Specific Instructions:
- 'structural_domains': List key domains (e.g., Kinase domain, CARD domain) and a brief 1-sentence description of their function.
- 'mechanistic_insights': Provide a step-by-step breakdown of the mechanism as an ordered list of strings.
- 'preclinical_evidence': Break down into specific models and outcomes.
- 'patent_ip.recent_filings': List top 3-5 relevant recent patent assignees/years.

**Indication Potential Scoring Criteria:**
To determine the 'indication_potential.score' (0-10), strictly evaluate the following 5 dimensions. Assign 0-2 points for each, then sum them up:
1. **Unmet Need**: (0=Low, 2=High/Critical)
2. **Scientific Rationale**: (0=Weak link, 2=Strong genetic/mechanistic validation)
3. **Competition**: (0=Crowded/Commoditized, 2=First-in-class/Best-in-class opportunity)
4. **Clinical Feasibility**: (0=Hard endpoints/High failure rate, 2=Clear path)
5. **Commercial Size**: (0=Niche, 2=Blockbuster potential)
Sum these values to get the final score. Explain this calculation in the 'reasoning' field.

- 'risks': Provide numerical scores 0-100.

Ensure all data is scientific and actionable.
        """

        # Use Gemini with search
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )

        # Parse the response
        if not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated from Gemini"
            )

        analysis_data = json.loads(response.text)

        # Generate mechanism diagram using Gemini image generation
        mechanism_image = None
        try:
            mechanism_text = " → ".join(analysis_data["biological_overview"]["mechanistic_insights"])
            image_prompt = f"""Scientific schematic diagram illustrating the biological mechanism of action for {request.target}.
Steps to illustrate: {mechanism_text}.
Style: Clean, professional, textbook medical illustration, white background, high resolution, schematic.
Labels should be legible and use standard scientific font."""

            try:
                # Generate mechanism diagram with Gemini image model
                image_response = client.models.generate_content(
                    model="gemini-3-pro-image-preview",
                    contents=image_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                    )
                )

                # Extract image from response
                for part in image_response.candidates[0].content.parts:
                    if part.inline_data:
                        mechanism_image = f"data:{part.inline_data.mime_type};base64,{part.inline_data.data}"
                        logger.info("Successfully generated mechanism diagram")
                        break
            except Exception as e:
                logger.warning(f"Failed to generate mechanism diagram: {e}")

        except Exception as e:
            logger.warning(f"Failed to prepare mechanism diagram: {e}")

        # Add mechanism image to biological overview
        analysis_data["biological_overview"]["mechanism_image"] = mechanism_image

        # Add target and indication to response
        analysis_data['target'] = request.target
        analysis_data['indication'] = request.indication

        logger.info(f"Successfully completed target analysis for {request.target}")

        return TargetAnalysisResponse(**analysis_data)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse AI response: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Target analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
