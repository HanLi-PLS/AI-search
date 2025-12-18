"""
Target Analyzer Parallel Endpoints - Split analysis into 3 focused API calls
This improves output quality by allowing each section group to get full model attention
"""
import logging
import json
from fastapi import APIRouter, Depends, HTTPException, status
from google import genai
from google.genai import types

from backend.app.config import settings
from backend.app.api.routes.auth import get_current_user
from backend.app.utils.aws_secrets import get_key
from backend.app.api.routes.target_analyzer import (
    TargetAnalysisRequest,
    CoreBiologyResponse,
    MarketCompetitionResponse,
    StrategyRiskResponse,
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


@router.post("/analyze-core-biology", response_model=CoreBiologyResponse)
async def analyze_core_biology(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze Core Biology: Biological Overview, Therapeutic Rationale, Pre-clinical Evidence
    This focused analysis allows for deeper, more thorough biological characterization
    """
    try:
        logger.info(f"Analyzing core biology for {request.target} in {request.indication}")
        client = get_gemini_client()

        # Focused schema for core biology sections only
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
                ),
            },
            required=["biological_overview", "therapeutic_rationale", "preclinical_evidence"]
        )

        # Focused prompt for core biology only
        prompt = f"""
You are a world-class drug development expert conducting deep BIOLOGICAL ANALYSIS for "{request.target}" inhibitor/modulator in "{request.indication}".

## CRITICAL METHODOLOGY - TWO-STAGE EXTRACTION:

**STAGE 1: EXTENSIVE RESEARCH**
Use 'google_search' tool extensively to find ALL relevant biological data about this target.

**STAGE 2: FOCUSED EXTRACTION**
Apply QUALITY GATES:
- **MATERIALITY**: Only insights that materially impact target assessment
- **SPECIFICITY**: Must be unique to THIS target (not generic observations)
- **QUANTIFICATION**: Demand numbers, percentages, fold-changes
- **ACTIONABILITY**: Drive specific diligence or decision-making

---

### 1. Biological Overview

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
- Include PubMed citations (PMIDs) for key steps

**Human Validation:**
Evidence from human studies/genetics that target modulation affects disease.
Provide PMID for strongest evidence.

**Species Conservation:**
Cross-species conservation analysis and implications for animal model translation.
Provide PMID if available.

---

### 2. Therapeutic Rationale

**EXTENSIVE RESEARCH:**
- Analyze complete disease pathway
- All potential intervention points
- Historical precedents for pathway modulation
- Compare ALL therapeutic modalities (small molecule, antibody, gene therapy, etc.)

**FOCUSED EXTRACTION:**

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

### 3. Pre-clinical Evidence

**EXTENSIVE RESEARCH - Genetic & Animal Evidence:**
Comprehensively search for ALL available evidence:
- Every published genetic association (GWAS, rare variants, monogenic)
- All animal knockout/knockin studies across species
- Historical precedents for similar targets
- Evidence quality and statistical rigor

**FOCUSED EXTRACTION - Evidence Benchmarking:**

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

## OUTPUT REQUIREMENTS:

**QUANTIFICATION**: Use numbers, not "better/worse"
**CITATIONS**: Include PMIDs for all scientific claims
**SPECIFICITY**: Everything must be specific to {request.target} in {request.indication}
**QUALITY RATINGS**: Rate evidence quality (High/Medium/Low) for transparency
**BENCHMARKING**: Compare to approved targets with quantified gaps

Analyze deeply and provide comprehensive, quantified, target-specific insights.
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
                detail="No response generated from Gemini"
            )

        data = json.loads(response.text)
        data['target'] = request.target
        data['indication'] = request.indication

        logger.info(f"Successfully completed core biology analysis for {request.target}")
        return CoreBiologyResponse(**data)

    except Exception as e:
        logger.error(f"Core biology analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/analyze-market-competition", response_model=MarketCompetitionResponse)
async def analyze_market_competition(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze Market & Competition: Drug/Trial Landscape, Patents, Indication Potential, Differentiation
    This focused analysis provides deeper competitive intelligence and market positioning
    """
    try:
        logger.info(f"Analyzing market/competition for {request.target} in {request.indication}")
        client = get_gemini_client()

        # Schema for market/competition sections
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
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
                        "score": types.Schema(type=types.Type.INTEGER),
                        "reasoning": types.Schema(type=types.Type.STRING),
                    },
                    required=["score", "reasoning"]
                ),
                "differentiation": types.Schema(
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
                ),
            },
            required=["drug_trial_landscape", "patent_ip", "indication_potential", "differentiation"]
        )

        prompt = f"""
You are a world-class competitive intelligence analyst conducting deep MARKET & COMPETITION ANALYSIS for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:
**STAGE 1**: Extensively research ALL competitive intelligence
**STAGE 2**: Apply quality gates for MATERIALITY, SPECIFICITY, QUANTIFICATION

---

### 1. Drug/Trial Landscape

**EXTENSIVE RESEARCH:**
Search for ALL clinical trials, approved drugs, and pipeline assets targeting this molecule or pathway.

**FOCUSED EXTRACTION:**
- Summary: Current competitive intensity (crowded/moderate/sparse)
- Top 8-12 competitive assets with: company, molecule name, phase, mechanism
- Phase distribution counts

---

### 2. Patent & IP Landscape

**EXTENSIVE RESEARCH:**
Search patent databases for recent filings related to this target.

**FOCUSED EXTRACTION:**
- Recent filings (5-8): assignee, year, focus area
- IP strategy implications for freedom to operate

---

### 3. Indication Potential

**EXTENSIVE RESEARCH:**
Analyze disease burden, addressable market, clinical precedent success rates for this target class.

**FOCUSED EXTRACTION:**
- Score 0-10 for target-indication attractiveness
- Reasoning with quantified metrics (prevalence, market size, precedent success rates)

---

### 4. Key Differentiation

**EXTENSIVE RESEARCH:**
Comprehensive competitive analysis across all dimensions:
- Mechanism differentiation
- Safety/efficacy profiles from preclinical/clinical data
- Patient population targeting
- Competitive scenarios and probabilities

**FOCUSED EXTRACTION:**

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

Output for: {request.target} in {request.indication}
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
        data['target'] = request.target
        data['indication'] = request.indication

        logger.info(f"Successfully completed market/competition analysis for {request.target}")
        return MarketCompetitionResponse(**data)

    except Exception as e:
        logger.error(f"Market/competition analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/analyze-strategy-risk", response_model=StrategyRiskResponse)
async def analyze_strategy_risk(
    request: TargetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze Strategy & Risk: Unmet Needs, Risks, Biomarker Strategy, BD Potential
    This focused analysis provides deeper risk assessment and strategic planning
    """
    try:
        logger.info(f"Analyzing strategy/risk for {request.target} in {request.indication}")
        client = get_gemini_client()

        # Schema for strategy/risk sections
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "unmet_needs": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "response_rates": types.Schema(type=types.Type.STRING),
                        "resistance": types.Schema(type=types.Type.STRING),
                        "safety_limitations": types.Schema(type=types.Type.STRING),
                        "adherence_challenges": types.Schema(type=types.Type.STRING),
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
                ),
                "biomarker_strategy": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "stratification_biomarkers": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(type=types.Type.STRING)
                        ),
                        "adaptive_design": types.Schema(type=types.Type.STRING),
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
            required=["unmet_needs", "indication_specific_analysis", "risks", "biomarker_strategy", "bd_potentials"]
        )

        prompt = f"""
You are a world-class strategy and risk analyst conducting deep STRATEGY & RISK ANALYSIS for "{request.target}" in "{request.indication}".

## TWO-STAGE EXTRACTION:
**STAGE 1**: Extensively research ALL strategic and risk dimensions
**STAGE 2**: Apply quality gates for MATERIALITY, SPECIFICITY, QUANTIFICATION

---

### 1. Unmet Medical Needs

**EXTENSIVE RESEARCH:**
Comprehensive analysis of current treatment landscape and gaps.

**FOCUSED EXTRACTION:**
For each dimension, provide quantified unmet needs:
- **Response Rates**: % of patients who don't respond to current therapies
- **Resistance**: Mechanisms and prevalence of treatment resistance
- **Safety Limitations**: % with severe AEs, monitoring burdens
- **Adherence Challenges**: Quantified compliance issues

---

### 2. Indication-Specific Analysis

**FOCUSED EXTRACTION:**
- **Therapeutic Classes**: 4-6 major drug classes with examples
- **Treatment Guidelines**: Current standard of care and sequencing

---

### 3. TARGET-SPECIFIC RISK ASSESSMENT

**EXTENSIVE RESEARCH:**
Exhaustively analyze ALL potential risks:
- Every mechanism-related safety concern from precedent targets
- All technical druggability challenges
- Complete competitive landscape threats
- Historical failure modes for this target class

**FOCUSED EXTRACTION - MATERIALITY GATES:**

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

### 4. Biomarker Strategy

**EXTENSIVE RESEARCH:**
Identify all potential stratification biomarkers and adaptive design opportunities.

**FOCUSED EXTRACTION:**
- **Stratification Biomarkers**: 3-6 biomarkers for patient selection
- **Adaptive Design**: Trial design considerations for biomarker-driven strategy

---

### 5. Business Development & Investment

**EXTENSIVE RESEARCH:**
Recent M&A, partnerships, investments in this space.

**FOCUSED EXTRACTION:**
- **Activities**: 4-6 recent BD activities with company and description
- **Interested Parties**: 5-8 companies/investors likely interested in this target

Output for: {request.target} in {request.indication}
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
        data['target'] = request.target
        data['indication'] = request.indication

        logger.info(f"Successfully completed strategy/risk analysis for {request.target}")
        return StrategyRiskResponse(**data)

    except Exception as e:
        logger.error(f"Strategy/risk analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
