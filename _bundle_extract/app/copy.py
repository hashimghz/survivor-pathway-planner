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
NO_PROFILE_LABEL = "No profile loaded"

# Tabs
TAB_CANDIDATES = "Candidates"
TAB_EXCLUDED = "Excluded"
TAB_INTERVENTIONS = "Interventions"

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
CARD_BUTTON_DETAILS = "Details"

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

# Skills to review banner
SKILLS_REVIEW_BANNER = "{n} skill needs your review"
SKILLS_REVIEW_BANNER_PLURAL = "{n} skills need your review"
SKILLS_REVIEW_BUTTON = "Review"

# Empty state
EMPTY_TITLE = "No profile loaded"
EMPTY_BODY = (
    "Load a survivor profile to see candidate occupations, what was filtered "
    "out, and what could be unlocked with a single intervention."
)
EMPTY_BUTTON_LOAD = "Load profile"
EMPTY_BUTTON_NEW = "New profile"

# Footer / accountability strip
ACCOUNTABILITY = (
    "This tool surfaces options. The caseworker decides what to discuss "
    "with the survivor and what to act on."
)
