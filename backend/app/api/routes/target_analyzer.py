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
    human_validation_pmid: Optional[str] = None  # PubMed ID
    species_conservation: str
    species_conservation_pmid: Optional[str] = None  # PubMed ID
    mechanism_image: Optional[str] = None  # Base64 encoded image

class TherapeuticRationale(BaseModel):
    pathway_positioning: str
    specificity_vs_breadth: str
    modality_comparison: str

class MonogenicMutation(BaseModel):
    variant: str
    phenotype: str
    pmid: Optional[str] = None  # PubMed ID
    evidence_quality: Optional[str] = None  # High/Medium/Low confidence
    effect_size: Optional[str] = None  # e.g., "OR=3.2, penetrance=95%"
    benchmark_comparison: Optional[str] = None  # e.g., "2x larger effect than typical approved target"

class CommonVariant(BaseModel):
    variant: str
    association: str
    pmid: Optional[str] = None  # PubMed ID
    evidence_quality: Optional[str] = None  # High/Medium/Low
    statistical_significance: Optional[str] = None  # e.g., "p=3e-8, genome-wide significant"
    benchmark_comparison: Optional[str] = None  # e.g., "Top 10% of GWAS strength vs approved precedents"

class HumanGenetics(BaseModel):
    monogenic_mutations: list[MonogenicMutation]
    common_variants: list[CommonVariant]

class LossOfFunctionModel(BaseModel):
    model: str
    outcome: str
    pmid: Optional[str] = None  # PubMed ID
    evidence_quality: Optional[str] = None  # High/Medium/Low
    phenotype_magnitude: Optional[str] = None  # e.g., "60% disease reduction"
    benchmark_comparison: Optional[str] = None  # e.g., "2x stronger than approved precedent (30% typical)"

class GainOfFunctionModel(BaseModel):
    model: str
    outcome: str
    pmid: Optional[str] = None  # PubMed ID
    evidence_quality: Optional[str] = None  # High/Medium/Low
    benchmark_comparison: Optional[str] = None

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

class CompetitiveScenario(BaseModel):
    scenario: str = Field(..., description="e.g., 'Competitor X succeeds in Phase 3'")
    probability: str = Field(..., description="e.g., '40%'")
    impact: str = Field(..., description="Impact on our target positioning")
    strategic_response: str = Field(..., description="How to respond/differentiate")

class Differentiation(BaseModel):
    analysis: str = Field(..., description="Overall strategic competitive analysis")
    efficacy_safety_position: Optional[str] = None  # ON/ABOVE/BELOW competitive frontier
    quantified_gaps: list[str] = Field(default_factory=list, description="Specific quantified advantages with numbers")
    competitive_scenarios: Optional[list[CompetitiveScenario]] = None
    advantages: list[str]
    disadvantages: list[str]

class UnmetNeeds(BaseModel):
    response_rates: str
    resistance: str
    safety_limitations: str
    adherence_challenges: str

class RiskItem(BaseModel):
    category: str = Field(..., description="Clinical/Safety/Competitive/Technical/Regulatory")
    description: str = Field(..., description="Specific mechanism explaining WHY this risk exists for THIS target")
    probability: int = Field(..., description="0-100% probability of occurrence")
    impact: int = Field(..., description="0-100 impact score where 100=program-killing")
    timeline: str = Field(..., description="When risk could materialize")
    early_warning_signals: str = Field(..., description="Specific biomarkers/findings to monitor")
    mitigation_strategies: str = Field(..., description="Actionable steps to reduce risk")
    evidence_quality: str = Field(..., description="High/Medium/Low - quality of evidence supporting this risk")

class Risks(BaseModel):
    risk_items: list[RiskItem] = Field(..., description="5-10 deeply analyzed, target-specific risks")
    summary: str = Field(..., description="Executive summary highlighting what's UNIQUE about this risk profile")

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
                        "human_validation_pmid": types.Schema(type=types.Type.STRING),
                        "species_conservation": types.Schema(type=types.Type.STRING),
                        "species_conservation_pmid": types.Schema(type=types.Type.STRING),
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
                                            "pmid": types.Schema(type=types.Type.STRING),
                                            "evidence_quality": types.Schema(type=types.Type.STRING, description="High/Medium/Low confidence"),
                                            "effect_size": types.Schema(type=types.Type.STRING, description="e.g., OR=3.2, penetrance=95%"),
                                            "benchmark_comparison": types.Schema(type=types.Type.STRING, description="e.g., 2x larger effect than typical approved target"),
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
                                            "evidence_quality": types.Schema(type=types.Type.STRING, description="High/Medium/Low"),
                                            "statistical_significance": types.Schema(type=types.Type.STRING, description="e.g., p=3e-8, genome-wide significant"),
                                            "benchmark_comparison": types.Schema(type=types.Type.STRING, description="e.g., Top 10% of GWAS strength vs approved precedents"),
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
                                            "evidence_quality": types.Schema(type=types.Type.STRING, description="High/Medium/Low"),
                                            "phenotype_magnitude": types.Schema(type=types.Type.STRING, description="e.g., 60% disease reduction"),
                                            "benchmark_comparison": types.Schema(type=types.Type.STRING, description="e.g., 2x stronger than approved precedent"),
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
                                            "evidence_quality": types.Schema(type=types.Type.STRING, description="High/Medium/Low"),
                                            "benchmark_comparison": types.Schema(type=types.Type.STRING, description="Comparison to approved precedents"),
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
                        "efficacy_safety_position": types.Schema(type=types.Type.STRING, description="ON/ABOVE/BELOW competitive frontier"),
                        "quantified_gaps": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(type=types.Type.STRING),
                            description="Specific quantified advantages with numbers"
                        ),
                        "competitive_scenarios": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "scenario": types.Schema(type=types.Type.STRING, description="e.g., 'Competitor X succeeds in Phase 3'"),
                                    "probability": types.Schema(type=types.Type.STRING, description="e.g., '40%'"),
                                    "impact": types.Schema(type=types.Type.STRING, description="Impact on our target positioning"),
                                    "strategic_response": types.Schema(type=types.Type.STRING, description="How to respond/differentiate"),
                                },
                                required=["scenario", "probability", "impact", "strategic_response"]
                            )
                        ),
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
                        "risk_items": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "category": types.Schema(type=types.Type.STRING, description="Clinical/Safety/Competitive/Technical/Regulatory"),
                                    "description": types.Schema(type=types.Type.STRING, description="Specific mechanism explaining WHY this risk exists for THIS target"),
                                    "probability": types.Schema(type=types.Type.INTEGER, description="0-100% probability of occurrence"),
                                    "impact": types.Schema(type=types.Type.INTEGER, description="0-100 impact score where 100=program-killing"),
                                    "timeline": types.Schema(type=types.Type.STRING, description="When risk could materialize"),
                                    "early_warning_signals": types.Schema(type=types.Type.STRING, description="Specific biomarkers/findings to monitor"),
                                    "mitigation_strategies": types.Schema(type=types.Type.STRING, description="Actionable steps to reduce risk"),
                                    "evidence_quality": types.Schema(type=types.Type.STRING, description="High/Medium/Low - quality of evidence supporting this risk"),
                                },
                                required=["category", "description", "probability", "impact", "timeline", "early_warning_signals", "mitigation_strategies", "evidence_quality"]
                            ),
                            description="5-10 deeply analyzed, target-specific risks"
                        ),
                        "summary": types.Schema(type=types.Type.STRING, description="Executive summary highlighting what's UNIQUE about this risk profile"),
                    },
                    required=["risk_items", "summary"]
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
You are a world-class drug development expert conducting sophisticated target-indication analysis for "{request.target}" inhibitor/modulator in "{request.indication}".

## CRITICAL METHODOLOGY - TWO-STAGE EXTRACTION APPROACH:

**STAGE 1: EXTENSIVE RESEARCH (Be Comprehensive)**
For each analysis section, you will FIRST conduct exhaustive research:
- Use 'google_search' tool extensively to find ALL relevant data
- Explore every dimension of the analysis with sophisticated frameworks
- Be thorough, rigorous, and demonstrate analytical excellence
- Consider mechanism precedents, competitive landscape, clinical/preclinical evidence

**STAGE 2: FOCUSED EXTRACTION (Be Selective & Actionable)**
After comprehensive research, apply QUALITY GATES to extract insights:
- **MATERIALITY**: Only include insights that materially impact target assessment
- **SPECIFICITY**: Must be unique to THIS target/indication (not generic biotech observations)
- **QUANTIFICATION**: Demand numbers, percentages, fold-changes (not vague "better/worse")
- **ACTIONABILITY**: Each insight should drive specific diligence or decision-making

**QUALITY THRESHOLDS ACROSS ALL SECTIONS:**
- 5-10 deeply analyzed, specific insights > 20 generic observations
- Quantified claims with evidence > vague qualitative statements
- Mechanism-based analysis > superficial descriptions
- Each insight must pass: "Does this tell me something unique about THIS target?"

**SEARCH REQUIREMENTS - Use google_search extensively for:**
- Latest clinical trial data (ClinicalTrials.gov, published results)
- Genetic evidence (GWAS, rare variants, knockout studies)
- Mechanism precedents (approved/failed drugs with similar MOA)
- Competitive landscape (clinical-stage assets, approved drugs)
- Safety precedents (target class effects, expression patterns)
- Recent scientific publications with PubMed citations

## Analysis Framework:

### 1. Biological Overview
- **Structural & Functional Domains**: List key protein domains with specific functions
- **Key Mechanistic Insights**: Step-by-step mechanism of action (how the target works biologically)
- **Human Validation Evidence**: Evidence from human genetics, biomarkers, patient data. Include PubMed ID (PMID) in `human_validation_pmid` field if available.
- **Functional Conservation Across Species**: Evolutionary conservation and cross-species validation. Include PubMed ID (PMID) in `species_conservation_pmid` field if available.

### 2. Therapeutic Rationale
- **Convergent Pathway Node Positioning**: Where does this target sit in disease pathways? Is it a convergence point?
- **Downstream Specificity vs Upstream Breadth**: Does modulating this target affect narrow downstream effects or broad upstream cascades?
- **Degradation vs Inhibition Approaches**: Compare protein degradation (PROTACs, molecular glues) vs traditional inhibition

### 3. Pre-clinical Evidence

**EXTENSIVE RESEARCH PHASE - Genetic & Animal Evidence:**
Comprehensively search for and analyze ALL available evidence:
- Every published genetic association (GWAS, rare variants, monogenic mutations)
- All animal knockout/knockin studies across species
- Historical precedents for this target mechanism
- Evidence quality and statistical rigor for each finding

**FOCUSED EXTRACTION PHASE - Evidence Benchmarking & Quality Assessment:**

**Human Genetic Evidence:**
- **Monogenic Gain-of-Function Mutations**: Rare variants that cause disease
  * For each: variant ID, phenotype, effect size/penetrance, PMID
  * EVIDENCE QUALITY: Rate confidence (High/Medium/Low) based on replication, sample size
  * BENCHMARK: How does effect size compare to approved targets? (e.g., "2x larger odds ratio than typical approved target")

- **Common/Low-Frequency Variant Associations**: GWAS, rare variant associations
  * For each: variant/locus, association strength (OR, p-value), population, PMID
  * STATISTICAL RIGOR: Flag genome-wide significance (p<5e-8), replication status
  * BENCHMARK: "Top 10% of genetic evidence strength vs approved mechanism precedents"

**Preclinical Animal Studies:**
- **Loss-of-Function Models**: Knockout/knockdown studies
  * For each: model system, phenotype magnitude, disease relevance, PMID
  * QUANTIFY: "60% reduction in disease score vs 30% typical for approved targets (2x stronger signal)"
  * BENCHMARK: Compare phenotype strength to historical knockouts that led to approved drugs

- **Gain-of-Function Models**: Overexpression/activation studies
  * For each: model, phenotype, translational relevance, PMID
  * EVIDENCE QUALITY: Does model recapitulate human disease pathology?

**EFFICACY BAR ANALYSIS:**
Based on mechanism precedents (similar targets that succeeded/failed):
- Minimum genetic evidence bar for clinical success: [Quantified threshold]
- Minimum animal phenotype magnitude for translation: [Quantified threshold]
- This target's position: "Exceeds approval bar by [X]%" or "Falls short by [Y]%"
- Clear assessment: ABOVE BENCHMARK / AT BENCHMARK / BELOW BENCHMARK

**SPECIFICITY REQUIREMENT:** Evidence must be mechanistically relevant to {request.indication}.
Exclude generic target biology unless directly tied to disease mechanism.

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

**EXTENSIVE RESEARCH PHASE - Competitive Target Analysis:**
Comprehensively analyze competitive landscape:
- ALL approved drugs and mechanisms for {request.indication}
- ALL clinical-stage assets targeting same/similar mechanisms
- Efficacy and safety profiles across competitive targets
- Mechanism-based advantages and limitations of each approach

**FOCUSED EXTRACTION PHASE - Strategic Competitive Frameworks:**

**1. EFFICACY/SAFETY FRONTIER ANALYSIS:**
   - Plot this target vs competitors on efficacy/safety trade-off matrix
   - Position: ON frontier (optimal balance), ABOVE (superior), or BELOW (dominated)?
   - QUANTIFY competitive gap specifically:
     * ✅ "2x better efficacy in animal models (60% vs 30% disease reduction) but 20% more Grade 3/4 AEs predicted"
     * ❌ NOT "better efficacy" (too vague)

**2. MECHANISTIC WHITE SPACE MAPPING:**
   - What mechanisms are UNDEREXPLOITED for {request.indication}?
   - Quantify: "80% of approved drugs hit pathway X; pathway Y (our target) has 0 approved drugs despite genetic validation"
   - Barriers: Technical challenges, historical failures, biomarker requirements

**3. COMPETITIVE SCENARIOS WITH PROBABILITIES:**
   Model key competitive developments:

   SCENARIO: [Competitor's selective inhibitor] succeeds in Phase 3
   - Probability: [X]% (based on mechanism precedent, Phase 2 data)
   - Impact: If superior efficacy → our [approach] requires [specific repositioning]
   - Strategic response: Emphasize [specific advantage], different biomarker/patient strategy

**4. QUANTIFIED DIFFERENTIATION (NOT VAGUE CLAIMS):**
   Mechanism-level specificity:
   - "100x selectivity for target vs off-target A (competitor has 10x) → predicted 90% reduction in [specific side effect]"
   - "Pan-inhibition covers isoforms A+B+C vs competitor's isoform A-only → 40% broader patient coverage but [specific toxicity concern]"
   - "Degradation approach (complete target removal) vs inhibition (partial blockade) → [quantified advantage] but [specific risk]"

**EXCLUSION CRITERIA:**
❌ Generic statements: "better safety", "more selective", "novel mechanism"
✅ Required: Quantified, mechanism-specific differentiation with tradeoffs acknowledged

Focus on mechanism-based differentiation grounded in biology, not marketing claims.

### 8. Unmet Medical Needs in {request.indication}
- **Incomplete Response**: % of patients not responding to current drugs
- **Treatment Resistance & Refractory Populations**: Who fails current therapy?
- **Safety & Monitoring Limitations**: Toxicity, required monitoring, black box warnings
- **Adherence & Persistence Challenges**: Dosing frequency, routes, tolerability

### 9. Indication-Specific Analysis: {request.indication}
- **Current Therapeutic Classes**: List major drug classes with examples
- **Treatment Guidelines Summary**: Current standard of care per guidelines

### 10. Risks - TARGET-SPECIFIC RISK ASSESSMENT

**EXTENSIVE RESEARCH PHASE - Comprehensive Risk Identification:**
Exhaustively analyze ALL potential risks:
- Every mechanism-related safety concern from precedent targets
- All technical druggability challenges (PK/PD, tissue penetration, etc.)
- Complete competitive landscape threats
- Historical failure modes for this target class
- Preclinical to clinical translation gaps

**FOCUSED EXTRACTION PHASE - Materiality Gates & Quality Thresholds:**

**MATERIALITY GATES - ONLY EXTRACT RISKS IF:**
1. Probability >20% AND material impact on target viability/development success
   OR
2. Mechanism-breaking risk regardless of probability (e.g., on-target toxicity in essential tissue)

**SPECIFICITY REQUIREMENTS - MUST BE TARGET-SPECIFIC:**

❌ EXCLUDE GENERIC RISKS (these add no value):
- "Clinical trials may fail" (too generic)
- "Safety signals possible" (too vague)
- "Competition exists" (not specific)
- "Financing needed" (not target-related)
- "Regulatory approval uncertain" (applies to all drugs)

✅ INCLUDE ONLY TARGET/MECHANISM-SPECIFIC RISKS:
- "High target affinity (Kd=0.1nM) may limit tissue penetration in fibrotic tissue due to binding site barrier effect"
- "Prior Class X inhibitor (70% sequence homology) showed QT prolongation in 15% of patients; this target's cardiac expression raises similar concern"
- "Compensatory pathway Y upregulates 3-fold when target inhibited >80% (observed in 3 knockout models); may limit efficacy durability"
- "Biomarker Z required for patient selection but assay not yet standardized; regulatory path unclear"
- "Target expressed in developing neural tissue; pregnancy category concern based on knockout embryonic lethality"

**RISK QUANTIFICATION (0-100 scale):**
For each risk, provide:
- **Category**: Clinical/Safety/Competitive/Technical/Regulatory
- **Description**: SPECIFIC mechanism explaining WHY this risk exists for THIS target (not generic)
- **Probability**: 0-100% (must justify with precedent data, not speculation)
- **Impact**: 0-100 where 100=program-killing (quantify commercial/development impact)
- **Timeline**: When risk could materialize (specific catalyst/data readout)
- **Early Warning Signals**: Specific biomarkers, preclinical findings, competitor data to monitor
- **Mitigation Strategies**: Actionable steps (not "monitor closely")

**MECHANISM-BASED RISK ANALYSIS:**
- **On-target toxicity**: Based on target expression pattern, knockout phenotypes
- **Off-target toxicity**: Based on selectivity profile, structural homology to related proteins
- **Efficacy limitations**: Compensatory pathways, target engagement thresholds, patient heterogeneity
- **Competitive displacement**: Specific competitor profiles that could make this target obsolete

**QUALITY THRESHOLD:**
- Aim for 5-10 deeply analyzed, target-specific risks
- NOT 20+ generic biotech risks
- Each risk must pass: "Does this tell me something unique about THIS target that I wouldn't know from generic risk factors?"

**EVIDENCE QUALITY for each risk:**
- HIGH: Direct data from this target (knockout, clinical precedent, structural biology)
- MEDIUM: Inference from related targets (class effects, homology-based)
- LOW: Theoretical concern without precedent data

Demonstrate sophisticated risk assessment by explaining the MECHANISM behind each risk, not just listing concerns.

### 11. Biomarker Strategy
- **Stratification/Paradigm Biomarkers**: Which biomarkers could identify responders?
- **Adaptive Design Considerations**: Biomarker-driven trial designs

### 12. BD Potentials
- **Known Activities**: Recent deals, investments, partnerships involving this target
- **Interested Parties**: Which pharma/biotech companies are most likely interested based on their portfolios?

## Output Format & Quality Standards:

**EVIDENCE-BASED ANALYSIS:**
- Every claim must be supported by specific evidence (studies, precedents, data)
- Include PubMed citations (PMIDs) for key scientific claims
- Cite specific competitor drugs, molecules, companies by name
- Reference specific clinical trials (NCT numbers), genetic studies, animal models

**QUANTIFICATION REQUIREMENTS:**
- Use numbers, percentages, fold-changes, effect sizes (not "better/worse/higher/lower")
- Examples:
  * ✅ "2x stronger genetic association (OR=3.2) than typical approved target (OR=1.6)"
  * ❌ "Strong genetic association"
  * ✅ "60% disease reduction in knockout vs 30% for approved precedent (2x stronger signal)"
  * ❌ "Significant disease reduction"

**STRUCTURED DATA FORMAT:**
- Use arrays and objects over long narrative paragraphs
- Keep descriptions concise but information-dense
- Organize data in tables/lists where appropriate (genetic variants, competitors, risks)

**SCIENTIFIC RIGOR:**
- All data must be scientifically accurate and current (search for latest information)
- Flag confidence level for key claims (High/Medium/Low evidence quality)
- Acknowledge uncertainty and data gaps where they exist
- Distinguish direct data from inference or extrapolation

**TARGET-SPECIFIC FOCUS:**
- Every section must be specific to {request.target} in {request.indication}
- Exclude generic biotech/pharma observations
- Focus on mechanism-based insights grounded in biology
- Demonstrate sophisticated understanding of this specific target's unique characteristics
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
                        # The data is already base64 encoded
                        import base64
                        mime_type = part.inline_data.mime_type or "image/png"

                        # Check if data is bytes or string
                        if isinstance(part.inline_data.data, bytes):
                            image_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                        else:
                            image_b64 = part.inline_data.data

                        mechanism_image = f"data:{mime_type};base64,{image_b64}"
                        logger.info(f"Successfully generated mechanism diagram (mime: {mime_type}, data length: {len(image_b64)})")
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


# ============================================================================
# PARALLEL ANALYSIS ENDPOINTS - For Higher Quality Output
# ============================================================================

# Response models for parallel analysis
class CoreBiologyResponse(BaseModel):
    biological_overview: BiologicalOverview
    therapeutic_rationale: TherapeuticRationale
    preclinical_evidence: PreclinicalEvidence
    target: str
    indication: str

class MarketCompetitionResponse(BaseModel):
    drug_trial_landscape: DrugTrialLandscape
    patent_ip: PatentIP
    indication_potential: IndicationPotential
    differentiation: Differentiation
    target: str
    indication: str

class StrategyRiskResponse(BaseModel):
    unmet_needs: UnmetNeeds
    indication_specific_analysis: IndicationSpecificAnalysis
    risks: Risks
    biomarker_strategy: BiomarkerStrategy
    bd_potentials: BDPotentials
    target: str
    indication: str
