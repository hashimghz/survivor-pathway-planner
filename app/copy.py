"""User-facing strings.

Centralised so the tone is reviewable in one file. Two rules govern every
string here:

1. No internal terminology surfaces in the UI: never write 'L1', 'L2', 'TOPSIS',
   'embedding', 'model', 'pipeline', 'inference', or 'AI says'. The caseworker
   sees one coherent result.

2. The caseworker is the decision-maker. Avoid 'recommendation', 'best match',
   'you should'. Prefer 'option', 'candidate', 'consider', 'worth verifying'.
"""

from __future__ import annotations

# Top-of-page chrome
APP_TITLE = "Pathway planner"
ACTIVE_PROFILE_LABEL = "Active:"
ACTIVE_PROFILE_NO_NAME = "Unnamed profile"
NO_PROFILE_LABEL = "No profile loaded"
EXIT_PROFILE_BUTTON = "Exit profile"

# Tabs
TAB_CANDIDATES = "Candidates"
TAB_EXCLUDED = "Excluded"
TAB_INTERVENTIONS = "Interventions"
TAB_HISTORY = "History"

# Sidebar context card
CONTEXT_HEADING = "CONTEXT"
TRIGGERS_HEADING = "TRIGGERS"
AVOID_HEADING = "AVOID"
CONTEXT_LABELS = {
    "work_authorization": "Work auth",
    "vehicle": "Vehicle",
    "transit": "Transit",
    "commute": "Commute",
    "wage_floor": "Wage floor",
    "education": "Education",
    "training_appetite": "Training appetite",
}

# Candidate card
CARD_FIT_LABEL = "FIT"
CARD_FRAMINGS_LABEL = "SAFE RESUME FRAMINGS"
CARD_WAGE_LABEL = "WAGE"
CARD_RISKS_LABEL = "WORTH VERIFYING"
CARD_UPSKILL_LABEL = "ONE NEXT STEP"
CARD_BUTTON_SAVE = "Save"
CARD_BUTTON_SAVED = "Saved"
CARD_BUTTON_DETAILS = "Details"
CARD_BUTTON_EXPAND = "Expand"
CARD_BUTTON_COLLAPSE = "Collapse"
CARD_SAVE_SAMPLE_DISABLED = "Saving isn't available for sample profiles — submit a real profile first."

# Excluded panel
EXCLUDED_EMPTY = "Every catalogued occupation cleared the constraints. " \
                 "That's unusual — worth a sanity check on the profile."
EXCLUSION_RULE_LABELS = {
    "geography":          "Outside reachable area",
    "industry":           "Excluded industry",
    "employer":           "Excluded employer",
    "documentation":      "Documentation requirement",
    "work_authorization": "Work authorization required",
    "criminal_record":    "Criminal-record requirement",
    "wage_floor":         "Below wage floor",
}

# Interventions panel
INTERVENTIONS_EMPTY = "No actionable interventions surfaced for this profile."
INTERVENTIONS_HEADING_ACTIONABLE = "Actionable"
INTERVENTIONS_HEADING_NOT_ACTIONABLE = "Safety-critical, not actionable"
INTERVENTIONS_JOBS_SUFFIX = "options would open"

# History tab (outcome tracking for saved candidates — see
# next_phase_plan.md §3.6a; lives only on Home.py, never on the intake form)
HISTORY_EMPTY = (
    "No saved candidates yet. Use Save on a candidate in the Candidates tab "
    "to start tracking its outcome here."
)
HISTORY_SAMPLE_DISABLED = (
    "History tracking isn't available for sample profiles — submit a real "
    "profile first."
)
HISTORY_CURRENT_STATUS_LABEL = "CURRENT STATUS"
HISTORY_TIMELINE_LABEL = "Full history ({n})"
HISTORY_STATUS_INPUT_LABEL = "New status"
HISTORY_NOTES_LABEL = "Notes (optional)"
HISTORY_RECORD_BUTTON = "Record"
HISTORY_STATUS_LABELS = {
    "saved": "Saved",
    "applied": "Applied",
    "interviewing": "Interviewing",
    "offered": "Offered",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
}

# Skills to review banner
SKILLS_REVIEW_BANNER = "{n} skill needs your review"
SKILLS_REVIEW_BANNER_PLURAL = "{n} skills need your review"
SKILLS_REVIEW_BUTTON = "Review"

# Skills-interpreted panel (surfaces the free-text -> O*NET cluster mapping)
SKILLS_INTERPRETED_HEADING = "How the engine interpreted the skills"
SKILLS_INTERPRETED_NO_MATCH = "No confident match — consider rephrasing"

# Income trajectory chart
CHART_TRAJECTORY_TITLE = "Projected income — top matches"
CHART_TRAJECTORY_XAXIS = "Months since placement"
CHART_TRAJECTORY_YAXIS = "Annual income ($)"
CHART_TRAJECTORY_CAPTION = (
    "Projection assumes placement near each occupation's 10th-percentile wage, "
    "moving toward its median over 24 months — a modeling assumption, not a "
    "guarantee. The shaded band is each occupation's full 10th–90th "
    "percentile wage range, not a forecast interval."
)
CHART_TRAJECTORY_EMPTY = "No candidates to project an income trajectory for."

# Empty state
EMPTY_TITLE = "No profile loaded"
EMPTY_BODY = (
    "Load a survivor profile to see candidate occupations, what was filtered "
    "out, and what could be unlocked with a single intervention."
)
EMPTY_BUTTON_LOAD = "Load profile"
EMPTY_BUTTON_NEW = "New profile"

# Saved profiles list
SAVED_PROFILES_HEADING = "Saved profiles"
SAVED_PROFILES_LOAD = "Load"
SAVED_PROFILES_EDIT = "Edit"
SAVED_PROFILES_DATE_UNKNOWN = "—"
SAVED_PROFILES_STATUS_NONE = "No history yet"
SAVED_PROFILES_DELETE = "Delete"
SAVED_PROFILES_DELETE_CONFIRM_PROMPT = "Permanently delete this profile and its history? This can't be undone."
SAVED_PROFILES_DELETE_CONFIRM_BUTTON = "Yes, delete permanently"
SAVED_PROFILES_DELETE_CANCEL = "Cancel"

# Sample profile picker (demo/at-a-glance only — not the primary intake flow)
EMPTY_SAMPLE_HEADING = "Or view a sample profile"
EMPTY_SAMPLE_BODY = (
    "For seeing the engine work at a glance. Not a substitute for entering "
    "a real survivor through New profile."
)
EMPTY_SAMPLE_SELECT_LABEL = "Sample profile"
EMPTY_SAMPLE_BUTTON = "Load sample"
SAMPLE_TAG_LABEL = "SAMPLE DATA — NOT A REAL PROFILE"

# Footer / accountability strip
ACCOUNTABILITY = (
    "This tool surfaces options. The caseworker decides what to discuss "
    "with the survivor and what to act on."
)

# Profile entry form
PROFILE_PAGE_TITLE = "New survivor profile"
PROFILE_EDIT_TITLE = "Edit survivor profile"
PROFILE_SUBMIT = "Save profile"
PROFILE_SAVE_CHANGES = "Save changes"
PROFILE_ADD_LANGUAGE = "Add language"
PROFILE_LANGUAGE_HEADING = "Language {n}"

PROFILE_SECTION_IDENTITY = "Identity"
PROFILE_SECTION_LANGUAGES = "Languages"
PROFILE_SECTION_DEMOGRAPHICS = "Demographics"
PROFILE_SECTION_CONSTRAINTS = "Constraints"
PROFILE_SECTION_GRADED = "Graded constraints"
PROFILE_SECTION_DOCUMENTATION = "Documentation"
PROFILE_SECTION_LEGAL = "Legal"
PROFILE_SECTION_SKILLS = "Skills"
PROFILE_SECTION_GOALS = "Goals"

PROFILE_FIELD_LABELS = {
    "legal_name": "Legal name",
    "preferred_name": "Preferred name",
    "pronouns": "Pronouns",
    "dob": "Date of birth",
    "safe_phone": "Safe phone",
    "safe_contact_method": "Safe contact method",
    "caseworker_notes": "Caseworker notes",
    "language_code": "Language code",
    "fluency_1_to_5": "Fluency (1–5)",
    "current_metro": "Current metro area",
    "education_highest": "Highest education",
    "disabilities": "Disabilities (comma-separated)",
    "dependents": "Dependents",
    "work_authorization": "Work authorization",
    "has_vehicle": "Has vehicle",
    "has_valid_license": "Has valid driver's license",
    "transit_access": "Transit access",
    "max_commute_minutes": "Max commute (minutes)",
    "wage_minimum_hourly": "Wage minimum (hourly)",
    "shift_morning": "Morning shift available",
    "shift_afternoon": "Afternoon shift available",
    "shift_evening": "Evening shift available",
    "night_shift": "Night shift",
    "isolated_workplace": "Isolated workplace",
    "customer_facing": "Customer-facing role",
    "male_dominated_team": "Male-dominated team",
    "uniformed_role": "Uniformed role",
    "requires_overnight_travel": "Overnight travel",
    "requires_clean_record": "Posting requires clean record",
    "requires_drivers_license": "Posting requires driver's license",
    "requires_ssn": "Posting requires SSN",
    "requires_credit_check": "Posting requires credit check",
    "state_id": "State ID held",
    "drivers_license": "Driver's license held",
    "ssn": "SSN held",
    "work_authorization_doc": "Work authorization document held",
    "passport": "Passport held",
    "record_categories": "Record categories",
    "expungement_eligible": "Expungement eligible",
    "jurisdiction": "Jurisdiction (state code)",
    "industries_of_interest": "Industries of interest",
    "training_appetite": "Training appetite",
    "long_term_goal": "Long-term goal",
}

PROFILE_DOCUMENTATION_BLOCKERS_HEADING = "Documentation blockers"
PROFILE_DOCUMENTS_HELD_HEADING = "Documents held"

PROFILE_SKILLS_TEXT_LABEL = (
    "Survivor's skills (one per line, or comma-separated). "
    "Free text is fine — the engine will match against O*NET clusters."
)

PROFILE_WORK_AUTH_LABELS = {
    "yes": "Authorized to work",
    "in_process": "Authorization in process",
    "no": "Not authorized",
}

PROFILE_CONTACT_METHOD_LABELS = {
    "phone": "Direct phone",
    "caseworker_only": "Caseworker only",
}

PROFILE_EDUCATION_LABELS = {
    "none": "None",
    "some_hs": "Some high school",
    "ged": "GED",
    "some_college": "Some college",
    "associates": "Associate's degree",
    "bachelors": "Bachelor's degree",
    "graduate": "Graduate degree",
}

PROFILE_GRADED_LABELS = {
    "trigger": "Trigger",
    "avoid": "Avoid",
    "ok": "OK",
}

PROFILE_TRAINING_LABELS = {
    "none": "None",
    "short": "Short (under 4 weeks)",
    "moderate": "Moderate (1–3 months)",
    "extensive": "Extensive (3+ months)",
}

PROFILE_RECORD_LABELS = {
    "prostitution_related": "Prostitution-related",
    "drug_possession": "Drug possession",
    "theft_property": "Theft / property",
    "other": "Other",
}

PROFILE_INDUSTRY_LABELS = {
    "hospitality": "Hospitality",
    "transportation": "Transportation",
    "agriculture": "Agriculture",
    "domestic_work": "Domestic work",
    "salon_nail": "Salon / nail",
    "massage_parlor": "Massage parlor",
    "restaurant_back_of_house": "Restaurant (back of house)",
    "retail_overnight": "Retail (overnight)",
    "restaurant_front_of_house": "Restaurant (front of house)",
    "retail_daytime": "Retail (daytime)",
    "healthcare_support": "Healthcare support",
    "childcare": "Childcare",
    "construction": "Construction",
    "landscaping_groundskeeping": "Landscaping / groundskeeping",
    "peddling_door_to_door_sales": "Peddling / door-to-door sales",
    "carnival_traveling_entertainment": "Carnival / traveling entertainment",
    "begging_panhandling": "Begging / panhandling",
    "warehousing_logistics": "Warehousing / logistics",
    "manufacturing": "Manufacturing",
    "janitorial_custodial": "Janitorial / custodial",
    "security_services": "Security services",
    "office_administrative": "Office / administrative",
    "call_center_customer_service": "Call center / customer service",
    "personal_care_aide": "Personal care aide",
    "nightlife_entertainment": "Nightlife / entertainment",
    "other": "Other (specify below)",
}

# Industries-to-avoid multiselect + its free-text companion (Industry.OTHER).
PROFILE_EXCLUSION_INDUSTRIES_LABEL = "Industries to avoid"
PROFILE_EXCLUSION_INDUSTRIES_OTHER_LABEL = (
    "Other industries to avoid (comma-separated) — used when \"Other\" is selected above"
)
# Industries-of-interest free-text companion (Industry.OTHER).
PROFILE_INDUSTRIES_INTEREST_OTHER_LABEL = (
    "Other industries of interest (comma-separated) — used when \"Other\" is selected above"
)

PROFILE_ENV_MISSING = (
    "Configuration incomplete. Set PATHWAY_AES_KEY and PATHWAY_HMAC_PEPPER "
    "in your environment before saving profiles."
)

PROFILE_VALIDATION_ERROR = "Could not save profile — check the highlighted fields."
