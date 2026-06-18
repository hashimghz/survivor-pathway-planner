"""Contracts for the Survivor Career Pathway Planner.

FROZEN after Day 0. Changes require the `contract-change` PR label and
acknowledgment from all three agent owners. See models/AGENTS.md.

Every data object that crosses a layer boundary is defined here. No business
logic, no I/O, no imports from engine/, app/, core/, db/, or data/.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field, condecimal, conint


# =============================================================================
# Enums — exhaustive. If a real value isn't here, the pipeline fails loud.
# =============================================================================


class WorkAuthorization(str, Enum):
    YES = "yes"
    IN_PROCESS = "in_process"
    NO = "no"


class SafeContactMethod(str, Enum):
    PHONE = "phone"
    CASEWORKER_ONLY = "caseworker_only"


class Industry(str, Enum):
    """Controlled vocabulary used for both exclusion_industries and industries_of_interest."""

    HOSPITALITY = "hospitality"
    TRANSPORTATION = "transportation"
    AGRICULTURE = "agriculture"
    DOMESTIC_WORK = "domestic_work"
    SALON_NAIL = "salon_nail"
    MASSAGE_PARLOR = "massage_parlor"
    RESTAURANT_BACK_OF_HOUSE = "restaurant_back_of_house"
    RETAIL_OVERNIGHT = "retail_overnight"


class GradedConstraintLevel(str, Enum):
    TRIGGER = "trigger"
    AVOID = "avoid"
    OK = "ok"


class SkillCitability(str, Enum):
    """Caseworker's judgment of whether/how a skill can appear on a resume."""

    DIRECT = "direct"
    TRANSFERABLE = "transferable"
    UNSAFE = "unsafe"


class SkillSource(str, Enum):
    EXPLOITATION = "exploitation"
    PRIOR_EMPLOYMENT = "prior_employment"
    EDUCATION = "education"
    SELF_TAUGHT = "self_taught"
    OTHER = "other"


class RecordCategory(str, Enum):
    PROSTITUTION_RELATED = "prostitution_related"
    DRUG_POSSESSION = "drug_possession"
    THEFT_PROPERTY = "theft_property"
    OTHER = "other"


class EducationLevel(str, Enum):
    NONE = "none"
    SOME_HIGH_SCHOOL = "some_high_school"
    HIGH_SCHOOL_OR_GED = "high_school_or_ged"
    SOME_COLLEGE = "some_college"
    ASSOCIATES = "associates"
    BACHELORS = "bachelors"
    GRADUATE = "graduate"


class TrainingAppetite(str, Enum):
    NONE = "none"
    SHORT_COURSE = "short_course"  # under 3 months
    CERTIFICATE = "certificate"  # 3–12 months
    DEGREE = "degree"  # 1+ years


class Shift(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class ExclusionRule(str, Enum):
    """Named reasons a candidate can be excluded by L2.

    Every ExcludedCandidate must carry one of these. The UI's filtered-out
    panel groups by this enum. L5 iterates this enum for relaxation analysis.
    """

    GEOGRAPHY = "geography"
    INDUSTRY_EXCLUSION = "industry_exclusion"
    EMPLOYER_EXCLUSION = "employer_exclusion"
    DOCUMENTATION_BLOCKER = "documentation_blocker"
    WORK_AUTHORIZATION = "work_authorization"
    CRIMINAL_RECORD = "criminal_record"
    WAGE_FLOOR = "wage_floor"


# =============================================================================
# Type aliases for repeated constraints
# =============================================================================

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
Level1To5 = Annotated[int, Field(ge=1, le=5)]
HourlyWage = Annotated[Decimal, Field(gt=0, decimal_places=2)]


# =============================================================================
# Profile sub-types (input)
# =============================================================================


class Language(BaseModel):
    code: str = Field(description="ISO 639-1 code, e.g. 'en', 'es'")
    fluency_1_to_5: Level1To5


class ExclusionZone(BaseModel):
    """A geographic area to avoid (former trafficker territory, etc.)."""

    lat: float
    lng: float
    radius_mi: float = Field(gt=0)


class RawSkill(BaseModel):
    """A skill as the caseworker entered it, before L1 mapping.

    `citability`, `safe_framing`, and `source` are the caseworker's judgment.
    L1 does not override these — it only attaches an O*NET ID.
    """

    skill_id: str = Field(description="UUID for tracking this skill across the pipeline")
    text: str = Field(description="Free-text description from the caseworker")
    level_1_to_5: Level1To5
    citability: SkillCitability
    safe_framing: str = Field(description="Resume-safe rewording the caseworker approved")
    source: SkillSource


class HardConstraints(BaseModel):
    """Binary rules. L2 cuts on any failure. Re-evaluated by L5 under relaxation."""

    work_authorization: WorkAuthorization
    has_vehicle: bool
    has_valid_license: bool
    transit_access: bool
    exclusion_zones: list[ExclusionZone] = Field(default_factory=list)
    exclusion_industries: list[Industry] = Field(default_factory=list)
    exclusion_employers: list[str] = Field(
        default_factory=list, description="Employer IDs (free-form strings for the demo)"
    )
    requires_clean_record: bool
    requires_drivers_license: bool
    requires_ssn: bool
    requires_credit_check: bool


class GradedConstraints(BaseModel):
    """Soft constraints. L3 scores against these, never filters."""

    night_shift: GradedConstraintLevel
    isolated_workplace: GradedConstraintLevel
    customer_facing: GradedConstraintLevel
    male_dominated_team: GradedConstraintLevel
    uniformed_role: GradedConstraintLevel


class StabilityNeeds(BaseModel):
    """Practical preferences. L3 scores against these as fit dimensions."""

    requires_overnight_travel: GradedConstraintLevel
    max_commute_minutes: conint(gt=0)
    available_shifts: list[Shift] = Field(min_length=1)
    wage_minimum_hourly: HourlyWage


class LegalProfile(BaseModel):
    """Criminal-record context. Drives L2's criminal_record rule and L5's vacatur hint."""

    record_categories: list[RecordCategory] = Field(default_factory=list)
    expungement_eligible: list[RecordCategory] = Field(
        default_factory=list, description="Subset of record_categories eligible for vacatur"
    )
    jurisdiction: str = Field(description="State code, e.g. 'FL'")


class DocumentationStatus(BaseModel):
    """What the survivor has on hand. Drives L2's documentation_blocker rule."""

    state_id: bool
    drivers_license: bool
    ssn: bool
    work_authorization_doc: bool
    passport: bool
    professional_licenses: list[str] = Field(default_factory=list)


class Goals(BaseModel):
    industries_of_interest: list[Industry] = Field(default_factory=list)
    training_appetite: TrainingAppetite
    long_term_goal: str = Field(default="", description="Freetext aspiration")


# =============================================================================
# Profile (PII present; lives in db/ only)
# =============================================================================


class Profile(BaseModel):
    """Full survivor record. PII fields are AES-256-GCM encrypted at rest.

    NEVER leaves db/ and core/. The pipeline (L1-L5) operates on Ticket only.
    The UI fetches a Profile to render the entry form, but downstream of
    submission only the Ticket is in scope.
    """

    id: str = Field(description="Profile UUID")

    # PII (encrypted at rest in the DB layer)
    legal_name: str
    preferred_name: str
    pronouns: str
    dob: date
    safe_phone: str
    safe_contact_method: SafeContactMethod
    caseworker_notes: str = ""

    # Non-PII structured fields
    languages: list[Language]
    current_metro: str = Field(description="City/region. NOT street address.")
    education_highest: EducationLevel
    disabilities: list[str] = Field(default_factory=list)
    dependents: conint(ge=0, le=5)

    skills_raw: list[RawSkill]
    hard_constraints: HardConstraints
    graded_constraints: GradedConstraints
    stability_needs: StabilityNeeds
    legal_profile: LegalProfile
    documentation_status: DocumentationStatus
    goals: Goals


# =============================================================================
# Ticket (anonymous, flows through the pipeline)
# =============================================================================


class Ticket(BaseModel):
    """Anonymous payload produced by core.anonymizer.

    No PII. Stable ticket_id derived from HMAC-SHA-256(profile_uuid, pepper).
    Every downstream layer (L1-L5) operates on this object.
    """

    ticket_id: str = Field(description="HMAC-SHA-256 of profile UUID with project pepper")
    skills_raw: list[RawSkill]
    languages: list[Language]
    current_metro: str
    education_highest: EducationLevel
    hard_constraints: HardConstraints
    graded_constraints: GradedConstraints
    stability_needs: StabilityNeeds
    legal_profile: LegalProfile
    documentation_status: DocumentationStatus
    goals: Goals


# =============================================================================
# L1 output
# =============================================================================


class MappedSkill(BaseModel):
    """A skill enriched with its canonical O*NET ID by L1.

    `citability`, `safe_framing`, `source` pass through unchanged from RawSkill.
    """

    skill_id: str
    raw_text: str
    onet_skill_id: str = Field(description="O*NET skill identifier, e.g. '2.A.1.f'")
    canonical_name: str
    confidence: Confidence = Field(description="Cosine similarity to top-1 O*NET skill")
    level_1_to_5: Level1To5
    citability: SkillCitability
    safe_framing: str
    source: SkillSource


class LowConfidenceMapping(BaseModel):
    """Skill whose top-1 match fell below the L1 confidence threshold (0.6).

    Surfaced to the caseworker for manual disambiguation. NEVER silently dropped.
    """

    skill_id: str
    raw_text: str
    top_candidates: list[tuple[str, str, Confidence]] = Field(
        description="(onet_skill_id, canonical_name, confidence) for top-3 below threshold"
    )


class MappedTicket(Ticket):
    """Ticket after L1: original skills_raw plus mapped_skills and any low-confidence misses."""

    mapped_skills: list[MappedSkill]
    low_confidence_mappings: list[LowConfidenceMapping] = Field(default_factory=list)


# =============================================================================
# Occupation base record
# =============================================================================


class OccupationCandidate(BaseModel):
    """Base O*NET occupation record. Loaded from data/onet_catalog."""

    onet_code: str = Field(description="e.g. '43-4051.00'")
    title: str
    soc_major: str = Field(description="2-digit SOC group, e.g. '43'")
    median_hourly_wage: Optional[HourlyWage] = None
    projected_growth_pct: Optional[float] = None


# =============================================================================
# L2 output
# =============================================================================


class FilteredCandidate(BaseModel):
    """Occupation that survived L2's hard constraints."""

    occupation: OccupationCandidate


class ExcludedCandidate(BaseModel):
    """Occupation cut by L2, with the named rule that cut it.

    Feeds both the UI's filtered-out panel AND L5's sensitivity analysis.
    """

    occupation: OccupationCandidate
    failed_rule: ExclusionRule
    details: str = Field(
        description=(
            "Human-readable detail. E.g. 'hospitality' for industry_exclusion, "
            "'requires_drivers_license' for documentation_blocker."
        )
    )


# =============================================================================
# L3 output
# =============================================================================


class CriteriaBreakdown(BaseModel):
    """Per-dimension fit scores in [0, 1]. Every dimension is named.

    The UI renders this as a radar/bar chart so the caseworker can see WHY a
    candidate scored where it did. This is the explainability surface for L3.
    """

    skill_match: Confidence
    wage_fit: Confidence
    commute_fit: Confidence
    shift_fit: Confidence
    isolation_fit: Confidence
    customer_facing_fit: Confidence
    uniformed_role_fit: Confidence
    male_dominated_fit: Confidence
    schedule_fit: Confidence


class RankedCandidate(BaseModel):
    """Output of L3's fuzzy TOPSIS. The ranking L4 receives is the ranking L4 keeps."""

    occupation: OccupationCandidate
    topsis_score: Confidence
    criteria_breakdown: CriteriaBreakdown


# =============================================================================
# L4 output
# =============================================================================


class WageRange(BaseModel):
    """Computed from BLS data via data.bls_wage_lookup(onet_code). NEVER hardcoded."""

    p10_hourly: HourlyWage
    p50_hourly: HourlyWage
    p90_hourly: HourlyWage


class EnrichedCandidate(BaseModel):
    """RankedCandidate plus LLM-generated explanation.

    L4 produces this from the structured fields of RankedCandidate + the Ticket.
    The LLM never sees PII and never reorders the ranking.
    """

    occupation: OccupationCandidate
    topsis_score: Confidence
    criteria_breakdown: CriteriaBreakdown

    fit_explanation: str = Field(description="2-3 sentences explaining why this candidate scored well")
    safe_resume_framing: list[str] = Field(
        description="Resume bullets respecting each MappedSkill.citability and safe_framing"
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Caseworker-verifiable concerns, e.g. 'verify whether reception desk is street-facing'",
    )
    upskill_next_step: str = Field(default="", description="One concrete next training step, if any")
    wage_range: WageRange


# =============================================================================
# L5 output
# =============================================================================


class SensitivityEntry(BaseModel):
    constraint: str = Field(description="The hard constraint relaxed, e.g. 'requires_drivers_license'")
    jobs_unlocked: conint(ge=0)
    intervention_hint: str = Field(
        description="Caseworker action, e.g. 'DMV documentation pathway', or 'not actionable' for safety-critical"
    )
    actionable: bool = Field(
        description="False for safety-critical relaxations (industry exclusions, exclusion zones)"
    )


class SensitivityReport(BaseModel):
    """L5 output. Entries sorted by jobs_unlocked descending."""

    entries: list[SensitivityEntry]


# =============================================================================
# Final container handed to the UI
# =============================================================================


class PipelineResult(BaseModel):
    """The only thing engine.pipeline.run() returns. The UI's contract.

    Carries everything the four required UI panels need:
      - enriched_candidates → Results page
      - excluded_set → FilteredOut page
      - sensitivity_report → Sensitivity page
      - low_confidence_mappings → LowConfidence page
    """

    ticket_id: str
    enriched_candidates: list[EnrichedCandidate] = Field(description="Top-N after L4")
    excluded_set: list[ExcludedCandidate]
    sensitivity_report: SensitivityReport
    low_confidence_mappings: list[LowConfidenceMapping] = Field(default_factory=list)
