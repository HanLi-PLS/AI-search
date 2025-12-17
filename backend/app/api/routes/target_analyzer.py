"""
Target Analyzer API endpoints
Analyzes drug targets and indications using AI
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from openai import OpenAI
import json

from backend.app.config import settings
from backend.app.api.routes.auth import get_current_user

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
    Analyze a drug target and indication pair

    This endpoint generates a comprehensive analysis report including:
    - Biological overview and mechanism of action
    - Therapeutic rationale
    - Pre-clinical evidence
    - Competitive landscape
    - Risk assessment
    - Business development opportunities

    Args:
        request: Target and indication to analyze
        current_user: Authenticated user

    Returns:
        Comprehensive analysis report
    """
    try:
        logger.info(f"Starting target analysis for {request.target} in {request.indication}")

        # Initialize OpenAI client
        api_key = settings.get_openai_api_key()
        client = OpenAI(api_key=api_key)

        # Create the analysis prompt
        prompt = f"""
Conduct a deep comprehensive research analysis for the drug target "{request.target}" specifically for the indication "{request.indication}".

Fill out the response following the JSON schema provided.
Focus on structured data (arrays, lists) suitable for visualization rather than long paragraphs.
Keep text descriptions concise and high-density.

Specific Instructions:
- 'structural_domains': List key domains (e.g., Kinase domain, CARD domain) and a brief 1-sentence description of their function.
- 'mechanistic_insights': Provide a step-by-step breakdown of the mechanism as an ordered list of strings.
- 'preclinical_evidence': Break down into specific models and outcomes.
- 'patent_ip.recent_filings': List top 3-5 relevant recent patent assignees/years.

**Indication Potential Scoring Criteria (STABILITY REQUIRED):**
To determine the 'indication_potential.score' (0-10), strictly evaluate the following 5 dimensions. Assign 0-2 points for each, then sum them up:
1. **Unmet Need**: (0=Low, 2=High/Critical)
2. **Scientific Rationale**: (0=Weak link, 2=Strong genetic/mechanistic validation)
3. **Competition**: (0=Crowded/Commoditized, 2=First-in-class/Best-in-class opportunity)
4. **Clinical Feasibility**: (0=Hard endpoints/High failure rate, 2=Clear path)
5. **Commercial Size**: (0=Niche, 2=Blockbuster potential)
Sum these values to get the final score. Explain this calculation in the 'reasoning' field.

- 'risks': Provide numerical scores 0-100.

Ensure all data is scientific and actionable. Use real-world data where possible.
        """

        # Use structured outputs with OpenAI
        # Use o4-mini for complex analysis with web search capabilities
        response = client.chat.completions.create(
            model="o4-mini",  # Use reasoning model with web search
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert biotech analyst specializing in drug target analysis and competitive intelligence. Provide comprehensive, data-driven analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "target_analysis",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "biological_overview": {
                                "type": "object",
                                "properties": {
                                    "structural_domains": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "description": {"type": "string"}
                                            },
                                            "required": ["name", "description"],
                                            "additionalProperties": False
                                        }
                                    },
                                    "mechanistic_insights": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "human_validation": {"type": "string"},
                                    "species_conservation": {"type": "string"}
                                },
                                "required": ["structural_domains", "mechanistic_insights", "human_validation", "species_conservation"],
                                "additionalProperties": False
                            },
                            "therapeutic_rationale": {
                                "type": "object",
                                "properties": {
                                    "pathway_positioning": {"type": "string"},
                                    "specificity_vs_breadth": {"type": "string"},
                                    "modality_comparison": {"type": "string"}
                                },
                                "required": ["pathway_positioning", "specificity_vs_breadth", "modality_comparison"],
                                "additionalProperties": False
                            },
                            "preclinical_evidence": {
                                "type": "object",
                                "properties": {
                                    "human_genetics": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "variant": {"type": "string"},
                                                "significance": {"type": "string"}
                                            },
                                            "required": ["variant", "significance"],
                                            "additionalProperties": False
                                        }
                                    },
                                    "animal_models": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "model": {"type": "string"},
                                                "outcome": {"type": "string"}
                                            },
                                            "required": ["model", "outcome"],
                                            "additionalProperties": False
                                        }
                                    }
                                },
                                "required": ["human_genetics", "animal_models"],
                                "additionalProperties": False
                            },
                            "drug_trial_landscape": {
                                "type": "object",
                                "properties": {
                                    "summary": {"type": "string"},
                                    "competitors": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "company": {"type": "string"},
                                                "molecule_name": {"type": "string"},
                                                "phase": {"type": "string"},
                                                "mechanism": {"type": "string"}
                                            },
                                            "required": ["company", "molecule_name", "phase", "mechanism"],
                                            "additionalProperties": False
                                        }
                                    },
                                    "phase_count": {
                                        "type": "object",
                                        "properties": {
                                            "preclinical": {"type": "integer"},
                                            "phase1": {"type": "integer"},
                                            "phase2": {"type": "integer"},
                                            "phase3": {"type": "integer"},
                                            "approved": {"type": "integer"}
                                        },
                                        "required": ["preclinical", "phase1", "phase2", "phase3", "approved"],
                                        "additionalProperties": False
                                    }
                                },
                                "required": ["summary", "competitors", "phase_count"],
                                "additionalProperties": False
                            },
                            "patent_ip": {
                                "type": "object",
                                "properties": {
                                    "recent_filings": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "assignee": {"type": "string"},
                                                "year": {"type": "string"},
                                                "focus": {"type": "string"}
                                            },
                                            "required": ["assignee", "year", "focus"],
                                            "additionalProperties": False
                                        }
                                    },
                                    "strategy": {"type": "string"}
                                },
                                "required": ["recent_filings", "strategy"],
                                "additionalProperties": False
                            },
                            "indication_potential": {
                                "type": "object",
                                "properties": {
                                    "score": {"type": "integer"},
                                    "reasoning": {"type": "string"}
                                },
                                "required": ["score", "reasoning"],
                                "additionalProperties": False
                            },
                            "differentiation": {
                                "type": "object",
                                "properties": {
                                    "analysis": {"type": "string"},
                                    "advantages": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "disadvantages": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["analysis", "advantages", "disadvantages"],
                                "additionalProperties": False
                            },
                            "unmet_needs": {
                                "type": "object",
                                "properties": {
                                    "response_rates": {"type": "string"},
                                    "resistance": {"type": "string"},
                                    "safety_limitations": {"type": "string"}
                                },
                                "required": ["response_rates", "resistance", "safety_limitations"],
                                "additionalProperties": False
                            },
                            "indication_specific_analysis": {"type": "string"},
                            "risks": {
                                "type": "object",
                                "properties": {
                                    "clinical": {"type": "integer"},
                                    "safety": {"type": "integer"},
                                    "competitive": {"type": "integer"},
                                    "technical": {"type": "integer"},
                                    "risk_analysis": {"type": "string"}
                                },
                                "required": ["clinical", "safety", "competitive", "technical", "risk_analysis"],
                                "additionalProperties": False
                            },
                            "biomarker_strategy": {"type": "string"},
                            "bd_potentials": {
                                "type": "object",
                                "properties": {
                                    "activities": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "company": {"type": "string"},
                                                "description": {"type": "string"}
                                            },
                                            "required": ["company", "description"],
                                            "additionalProperties": False
                                        }
                                    },
                                    "interested_parties": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["activities", "interested_parties"],
                                "additionalProperties": False
                            }
                        },
                        "required": [
                            "biological_overview",
                            "therapeutic_rationale",
                            "preclinical_evidence",
                            "drug_trial_landscape",
                            "patent_ip",
                            "indication_potential",
                            "differentiation",
                            "unmet_needs",
                            "indication_specific_analysis",
                            "risks",
                            "biomarker_strategy",
                            "bd_potentials"
                        ],
                        "additionalProperties": False
                    }
                }
            }
        )

        # Parse the response
        content = response.choices[0].message.content
        if not content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated from AI model"
            )

        analysis_data = json.loads(content)

        # Add target and indication to response
        analysis_data['target'] = request.target
        analysis_data['indication'] = request.indication

        logger.info(f"Successfully completed target analysis for {request.target}")

        return TargetAnalysisResponse(**analysis_data)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {str(e)}")
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
