"""Contracts for the Pathway Planner.

FROZEN after Day 0. Changes require the `contract-change` PR label and
acknowledgment from all three agent owners. See models/AGENTS.md.

Every data object that crosses a layer boundary lives here. No business
logic, no I/O, no imports from engine/, app/, core/, db/, or data/.

Naming: the UI surface uses domain terms (Candidate, Excluded, Intervention),
never internal pipeline language. Internal pipeline modules may still organise
themselves as L1-L5 in code, but the contracts themselves carry no layer names.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, conint


# =============================================================================
# Enums — match the values that appear in the teammate's data exactly.
# =============================================================================


class WorkAuthorization(str, Enum):
    YES = "yes"
    IN_PROCESS = "in_process"
    NO = "no"


class SafeContactMethod(str, Enum):
    PHONE = "phone"
    CASEWORKER_ONLY = "caseworker_only"


class Industry(str, Enum):
    """Used for both exclusion_industries and industries_of_interest."""

    HOSPITALITY = "hospitality"
    TRANSPORTATION = "transportation"
    AGRICULTURE = "agriculture"
    DOMESTIC_WORK = "domestic_work"
    SALON_NAIL = "salon_nail"
    MASSAGE_PARLOR = "massage_parlor"
    RESTAURANT_BACK_OF_HOUSE = "restaurant_back_of_house"
    RETAIL_OVERNIGHT = "retail_overnight"


class GradedLevel(str, Enum):
    TRIGGER = "trigger"
    AVOID = "avoid"
    OK = "ok"


class SkillCitability(str, Enum):
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
    SOME_HS = "some_hs"
    GED = "ged"
    SOME_COLLEGE = "some_college"
    ASSOCIATES = "associates"
    BACHELORS = "bachelors"
    GRADUATE = "graduate"


class TrainingAppetite(str, Enum):
    NONE = "none"
    SHORT = "short"
    MODERATE = "moderate"
    EXTENSIVE = "extensive"


class ExclusionRule(str, Enum):
    """Named reasons a candidate can be excluded.

    The UI groups the Excluded panel by these values. Internally, the engine's
    veto step assigns one of these to every excluded occupation.
    """

    GEOGRAPHY = "geography"
    INDUSTRY = "industry"
    EMPLOYER = "employer"
    DOCUMENTATION = "documentation"
    WORK_AUTHORIZATION = "work_authorization"
    CRIMINAL_RECORD = "criminal_record"
    WAGE_FLOOR = "wage_floor"


# =============================================================================
# Type aliases for repeated constraints
# =============================================================================

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
Level1To5 = Annotated[int, Field(ge=1, le=5)]
HourlyWage = Annotated[Decimal, Field(gt=0, decimal_places=2)]
WorkContextRating = Annotated[float, Field(ge=1.0, le=5.0)]


# =============================================================================
# Profile sub-types (matching teammate's survivors.json shape)
# =============================================================================


class Identity(BaseModel):
    """PII grouped together. Encrypted at rest. Stripped at the anonymiser."""

    legal_name: str
    preferred_name: str
    pronouns: str
    dob: date
    safe_phone: str
    safe_contact_method: SafeContactMethod
    caseworker_notes: str = ""


class Language(BaseModel):
    code: str = Field(description="ISO 639-1, e.g. 'en', 'so', 'es'")
    fluency_1_to_5: Level1To5


class Skill(BaseModel):
    """A skill, already mapped to its O*NET id.

    The teammate's survivors.json provides skills pre-mapped, so there is no
    free-text-to-O*NET embedding step in the pipeline. Citability and
    safe_framing are the caseworker's judgement; the engine does not override
    them.
    """

    skill_id: str = Field(description="O*NET skill id, e.g. '2.A.1.d'")
    skill_name: str = Field(description="O*NET canonical skill name")
    level_1_to_5: Level1To5
    citability: SkillCitability
    safe_framing: str = Field(description="Resume-safe rewording the caseworker approved")
    source: SkillSource


class ExclusionZone(BaseModel):
    lat: float
    lng: float
    radius_mi: float = Field(gt=0)


class DocumentationBlockers(BaseModel):
    """Job-side requirements that may exclude the survivor.

    These are the requirements typical postings impose. The veto step checks
    them against `documents_held` and `legal_profile`.
    """

    requires_clean_record: bool
    requires_drivers_license: bool
    requires_ssn: bool
    requires_credit_check: bool


class GradedConstraints(BaseModel):
    """Soft constraints. Scored in the fit calculation; never used as filters.

    `requires_overnight_travel` is here (not in stability fields) because the
    teammate's data places it here.
    """

    night_shift: GradedLevel
    isolated_workplace: GradedLevel
    customer_facing: GradedLevel
    male_dominated_team: GradedLevel
    uniformed_role: GradedLevel
    requires_overnight_travel: GradedLevel


class AvailableShifts(BaseModel):
    morning: bool
    afternoon: bool
    evening: bool


class LegalProfile(BaseModel):
    """Criminal-record context. Drives the criminal_record veto and vacatur hints."""

    record_categories: list[RecordCategory] = Field(default_factory=list)
    expungement_eligible: list[RecordCategory] = Field(
        default_factory=list,
        description="Subset of record_categories eligible for vacatur",
    )
    jurisdiction: str = Field(description="State code, e.g. 'WA'")


class DocumentsHeld(BaseModel):
    """What the survivor has on hand."""

    state_id: bool
    drivers_license: bool
    ssn: bool
    work_authorization_doc: bool
    passport: bool
    professional_licenses: list[str] = Field(default_factory=list)


# =============================================================================
# Profile (PII included; lives only in db/ and core/)
# =============================================================================


class Profile(BaseModel):
    """Full survivor record. PII (in `identity`) is encrypted at rest.

    Never leaves db/ and core/. Pipeline operates on Ticket only.
    Matches the shape of the teammate's survivors.json exactly.
    """

    model_config = ConfigDict(populate_by_name=True)

    identity: Identity

    languages: list[Language]
    current_metro: str = Field(description="City/region; not street address")
    work_authorization: WorkAuthorization
    has_vehicle: bool
    has_valid_license: bool
    transit_access: bool
    education_highest: EducationLevel
    disabilities: list[str] = Field(default_factory=list)
    dependents: conint(ge=0, le=10)

    skills: list[Skill] = Field(default_factory=list)

    # Free-text skill strings entered by the caseworker.
    existing_skills: list[str] = Field(default_factory=list)

    exclusion_zones: list[ExclusionZone] = Field(default_factory=list)
    exclusion_industries: list[Industry] = Field(default_factory=list)
    exclusion_employers: list[str] = Field(default_factory=list)

    documentation_blockers: DocumentationBlockers
    graded_constraints: GradedConstraints

    max_commute_minutes: conint(gt=0)
    available_shifts: AvailableShifts

    legal_profile: LegalProfile
    documents_held: DocumentsHeld

    industries_of_interest: list[Industry] = Field(default_factory=list)
    wage_minimum_hourly: HourlyWage
    training_appetite: TrainingAppetite
    long_term_goal: str = ""

    # Caseworker curation of engine output. Never read by the engine and
    # never carried onto Ticket (see core/anonymizer.py's exclude set) —
    # this is purely "which results did the caseworker flag," not survivor
    # intake data, so it has no business crossing into the pipeline.
    saved_candidate_codes: list[str] = Field(
        default_factory=list,
        description="O*NET-SOC codes of candidates the caseworker saved for follow-up.",
    )


# =============================================================================
# Ticket (anonymous; what flows through the pipeline)
# =============================================================================


class Ticket(BaseModel):
    """Anonymous payload produced by the anonymiser.

    No PII. Stable ticket_id derived from HMAC-SHA-256(profile_uuid, pepper).
    """

    ticket_id: str = Field(description="HMAC of the profile UUID with the project pepper")

    languages: list[Language]
    current_metro: str
    work_authorization: WorkAuthorization
    has_vehicle: bool
    has_valid_license: bool
    transit_access: bool
    education_highest: EducationLevel
    disabilities: list[str]
    dependents: conint(ge=0, le=10)

    skills: list[Skill]

    # Free-text skill strings entered by the caseworker (Phase 4 form).
    existing_skills: list[str] = Field(default_factory=list)
    # L1 mapper output: each entry has "input", "matches" with onet_id/onet_name/confidence.
    mapped_skills: list[dict] = Field(default_factory=list)

    exclusion_zones: list[ExclusionZone]
    exclusion_industries: list[Industry]
    exclusion_employers: list[str]

    documentation_blockers: DocumentationBlockers
    graded_constraints: GradedConstraints

    max_commute_minutes: conint(gt=0)
    available_shifts: AvailableShifts

    legal_profile: LegalProfile
    documents_held: DocumentsHeld

    industries_of_interest: list[Industry]
    wage_minimum_hourly: HourlyWage
    training_appetite: TrainingAppetite
    long_term_goal: str = ""


# =============================================================================
# Occupation (matches the teammate's occupations.csv columns)
# =============================================================================


class OccupationSkill(BaseModel):
    """A skill an O*NET occupation calls for."""

    id: str = Field(description="O*NET skill id")
    name: str


class Occupation(BaseModel):
    """An O*NET occupation with the work-context fields the engine uses.

    Field names match the columns in the teammate's occupations.csv.
    """

    code: str = Field(description="O*NET-SOC code, e.g. '29-2071.00'")
    title: str
    description: str = ""

    job_zone: Optional[float] = Field(default=None, description="1-5; training/experience intensity")
    education_level: Optional[float] = Field(default=None, description="1-12 O*NET education enum")

    contact_with_others: Optional[WorkContextRating] = None
    physical_proximity: Optional[WorkContextRating] = None
    violence_exposure: Optional[WorkContextRating] = None
    public_facing: Optional[WorkContextRating] = None
    schedule_irregularity: Optional[WorkContextRating] = None

    isolated_workplace: bool = False
    high_surveillance: bool = False

    median_wage_annual: Optional[float] = None
    wage_pct10_annual: Optional[float] = None
    wage_pct90_annual: Optional[float] = None
    median_wage_hourly: Optional[HourlyWage] = None
    total_employment: Optional[float] = None

    skills: list[OccupationSkill] = Field(default_factory=list)
    training_required: Optional[str] = None


# =============================================================================
# Fit dimensions and Candidate output (no layer names in these types)
# =============================================================================


class CriteriaBreakdown(BaseModel):
    """Per-dimension fit scores in [0, 1]. The UI renders these as bars."""

    skill_match: Confidence
    wage_fit: Confidence
    commute_fit: Confidence
    shift_fit: Confidence
    isolation_fit: Confidence
    customer_facing_fit: Confidence
    uniformed_role_fit: Confidence
    male_dominated_fit: Confidence
    schedule_fit: Confidence


class WageRange(BaseModel):
    """Computed from BLS columns on the occupation row. Never hardcoded."""

    p10_hourly: HourlyWage
    p50_hourly: HourlyWage
    p90_hourly: HourlyWage


class Candidate(BaseModel):
    """A scored, explained occupation. The UI's primary surface.

    `fit_explanation` is the engine-generated prose the UI renders as the
    description paragraph under the criteria bars. `safe_resume_framings`
    respect each skill's citability.
    """

    occupation: Occupation
    fit_score: Confidence

    criteria_breakdown: CriteriaBreakdown
    fit_explanation: str = Field(
        description="2-3 sentences explaining why this candidate scored where it did"
    )
    safe_resume_framings: list[str] = Field(
        description="Resume bullets respecting each Skill.citability and safe_framing"
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Caseworker-verifiable concerns, e.g. 'verify whether reception is street-facing'",
    )
    upskill_next_step: str = Field(
        default="",
        description="One concrete training step that would raise fit, if any",
    )
    wage_range: WageRange


# =============================================================================
# Excluded occupations
# =============================================================================


class Excluded(BaseModel):
    """An occupation cut by a hard-constraint rule, with the named rule.

    Feeds the Excluded panel and the Interventions analysis.
    """

    occupation: Occupation
    rule: ExclusionRule
    detail: str = Field(
        description="Human-readable detail, e.g. 'hospitality' for industry, "
        "'requires_drivers_license' for documentation"
    )


# =============================================================================
# Interventions (what would unlock more options if it changed)
# =============================================================================


class Intervention(BaseModel):
    constraint: str = Field(description="The constraint that would change, e.g. 'requires_drivers_license'")
    jobs_unlocked: conint(ge=0)
    hint: str = Field(
        description="One-sentence caseworker action, e.g. 'DMV documentation pathway'"
    )
    actionable: bool = Field(
        description="False for safety-critical constraints (industry exclusions, exclusion zones)"
    )


class InterventionReport(BaseModel):
    """All interventions, sorted by jobs_unlocked descending."""

    entries: list[Intervention]


# =============================================================================
# Skills the caseworker needs to confirm
# =============================================================================


class SkillToReview(BaseModel):
    """A skill the engine flagged as uncertain.

    Surfaced in the UI as a banner above Candidates when present. Empty when
    every skill mapped cleanly. The UI never says 'low confidence mapping' or
    references the layer that produced this — it just says 'review this skill'.
    """

    skill_id: str
    skill_name: str
    reason: str = Field(description="Plain-language reason, no layer references")


# =============================================================================
# The single object the UI consumes
# =============================================================================


class PipelineResult(BaseModel):
    """The only thing the engine returns to the UI.

    Fields are named in domain terms. The UI never references pipeline layers.
    """

    ticket_id: str
    candidates: list[Candidate] = Field(description="Top-N ranked candidates")
    excluded: list[Excluded]
    interventions: InterventionReport
    skills_to_review: list[SkillToReview] = Field(default_factory=list)

