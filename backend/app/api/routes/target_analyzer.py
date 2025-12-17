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

class MonogenicMutation(BaseModel):
    variant: str
    phenotype: str

class CommonVariant(BaseModel):
    variant: str
    association: str

class HumanGenetics(BaseModel):
    monogenic_mutations: list[MonogenicMutation]
    common_variants: list[CommonVariant]

class LossOfFunctionModel(BaseModel):
    model: str
    outcome: str

class GainOfFunctionModel(BaseModel):
    model: str
    outcome: str

class AnimalModels(BaseModel):
    loss_of_function: list[LossOfFunctionModel]
    gain_of_function: list[GainOfFunctionModel]

class PreClinicalEvidence(BaseModel):
    human_genetics: HumanGenetics
    animal_models: AnimalModels

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
    adherence_challenges: str

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

class TherapeuticClass(BaseModel):
    class_name: str
    examples: str

class IndicationSpecificAnalysis(BaseModel):
    therapeutic_classes: list[TherapeuticClass]
    treatment_guidelines: str

class BiomarkerStrategy(BaseModel):
    stratification_biomarkers: list[str]
    adaptive_design: str

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
    indication_specific_analysis: IndicationSpecificAnalysis
    risks: Risks
    biomarker_strategy: BiomarkerStrategy
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
                            type=types.Type.OBJECT,
                            properties={
                                "monogenic_mutations": types.Schema(
                                    type=types.Type.ARRAY,
                                    items=types.Schema(
                                        type=types.Type.OBJECT,
                                        properties={
                                            "variant": types.Schema(type=types.Type.STRING),
                                            "phenotype": types.Schema(type=types.Type.STRING),
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
                                        },
                                        required=["model", "outcome"]
                                    )
                                ),
                            },
                            required=["loss_of_function", "gain_of_function"]
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
                        "response_rates": types.Schema(type=types.Type.STRING, description="Incomplete response to existing drugs"),
                        "resistance": types.Schema(type=types.Type.STRING, description="Treatment resistance & refractory populations"),
                        "safety_limitations": types.Schema(type=types.Type.STRING, description="Safety & monitoring limitations"),
                        "adherence_challenges": types.Schema(type=types.Type.STRING, description="Adherence & persistence challenges"),
                    },
                    required=["response_rates", "resistance", "safety_limitations", "adherence_challenges"]
                ),
                "indication_specific_analysis": types.Schema(
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
                ),
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
                "biomarker_strategy": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "stratification_biomarkers": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(type=types.Type.STRING)
                        ),
                        "adaptive_design": types.Schema(type=types.Type.STRING, description="Adaptive design considerations"),
                    },
                    required=["stratification_biomarkers", "adaptive_design"]
                ),
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
Conduct a deep comprehensive drug development potential analysis for "{request.target}" inhibitor/modulator in "{request.indication}".

**CRITICAL**: You MUST use the 'google_search' tool extensively to find:
- Latest clinical trial data (ClinicalTrials.gov, published results)
- Recent patent filings and IP landscape
- Business development news and partnerships
- Recent scientific publications and genetic evidence
- Competitive landscape and market data

## Analysis Framework:

### 1. Biological Overview
- **Structural & Functional Domains**: List key protein domains with specific functions
- **Key Mechanistic Insights**: Step-by-step mechanism of action (how the target works biologically)
- **Human Validation Evidence**: Evidence from human genetics, biomarkers, patient data
- **Functional Conservation Across Species**: Evolutionary conservation and cross-species validation

### 2. Therapeutic Rationale
- **Convergent Pathway Node Positioning**: Where does this target sit in disease pathways? Is it a convergence point?
- **Downstream Specificity vs Upstream Breadth**: Does modulating this target affect narrow downstream effects or broad upstream cascades?
- **Degradation vs Inhibition Approaches**: Compare protein degradation (PROTACs, molecular glues) vs traditional inhibition

### 3. Pre-clinical Evidence
**Human Genetic Evidence:**
- **Monogenic Gain-of-Function Mutations**: Rare variants that cause disease
- **Common/Low-Frequency Variant Associations**: GWAS, rare variant associations

**Preclinical Animal Studies:**
- **Loss-of-Function Models**: Knockout/knockdown studies and phenotypes
- **Gain-of-Function Models**: Overexpression studies and disease models

### 4. Drug/Trial Landscape
- Provide detailed competitive landscape overview
- List specific companies, molecules, phases, and mechanisms
- Calculate phase distribution counts

### 5. Patent & IP Landscape
- Recent patent filings (last 3-5 years)
- Key assignees and their strategic focus
- IP strategy considerations for entering this space

### 6. Indication Potential in {request.indication}
**Scoring Criteria (0-10):**
1. **Unmet Need** (0-2 points): Current treatment gaps
2. **Scientific Rationale** (0-2 points): Strength of genetic/mechanistic validation
3. **Competition** (0-2 points): First-in-class vs crowded space
4. **Clinical Feasibility** (0-2 points): Clear endpoints, feasible trials
5. **Commercial Size** (0-2 points): Market potential and addressable population
Sum these to get final score. Provide detailed reasoning.

### 7. Key Differentiation vs Existing Drugs
- Compare against current standard of care drug classes in {request.indication}
- List specific advantages and disadvantages
- Focus on mechanism-based differentiation

### 8. Unmet Medical Needs in {request.indication}
- **Incomplete Response**: % of patients not responding to current drugs
- **Treatment Resistance & Refractory Populations**: Who fails current therapy?
- **Safety & Monitoring Limitations**: Toxicity, required monitoring, black box warnings
- **Adherence & Persistence Challenges**: Dosing frequency, routes, tolerability

### 9. Indication-Specific Analysis: {request.indication}
- **Current Therapeutic Classes**: List major drug classes with examples
- **Treatment Guidelines Summary**: Current standard of care per guidelines

### 10. Risks
Provide 0-100 risk scores and detailed analysis for:
- **Clinical Development Risks**: Trial design, endpoint challenges, historical failure rates
- **Long-term Safety Concerns**: Known or predicted on-target/off-target toxicities
- **Competitive Positioning Challenges**: How crowded is the space?
- **Technical Risks**: Druggability, delivery, bioavailability issues

### 11. Biomarker Strategy
- **Stratification/Paradigm Biomarkers**: Which biomarkers could identify responders?
- **Adaptive Design Considerations**: Biomarker-driven trial designs

### 12. BD Potentials
- **Known Activities**: Recent deals, investments, partnerships involving this target
- **Interested Parties**: Which pharma/biotech companies are most likely interested based on their portfolios?

## Output Format:
- Use structured data (arrays, objects) over long paragraphs
- Be specific: cite studies, patents, companies, molecules by name
- Keep descriptions concise but information-dense
- All data must be scientifically accurate and current (search for latest information)
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
                # Note: Image generation is experimental and may not always work
                image_response = client.models.generate_content(
                    model="gemini-3-pro-image-preview",
                    contents=image_prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}]
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
