"""
SYNTHETIC SURVIVOR PROFILE GENERATOR — make_survivors.py

Generates 10 SYNTHETIC survivor profiles for the Survivor Career Pathway Planner
and writes them to data/clean/survivors.json (a JSON array).

ALL DATA IS SYNTHETIC. No real people, no real PII. The only "real" values are the
skill (id, name) pairs, which are drawn from data/clean/occupations.csv so the
profiles join cleanly against the occupational graph.

Run from project root:
    python scripts/make_survivors.py

Outputs:
    data/clean/survivors.json              — the 10 profiles (JSON array)
    data/clean/survivors_validation.txt    — human-readable validation report

Standard library + pandas only. Self-contained.
"""

import ast
import json
import random
from datetime import date, datetime
from pathlib import Path

import pandas as pd

# ─── PATHS ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
OCC_FILE = CLEAN / "occupations.csv"
OUT_JSON = CLEAN / "survivors.json"
OUT_REPORT = CLEAN / "survivors_validation.txt"

SEED = 42
N_PROFILES = 10

# ─── CONTROLLED VOCAB (tokens, NOT SOC codes) ──────────────────────────────────
INDUSTRY_VOCAB = [
    "hospitality", "transportation", "agriculture", "domestic_work",
    "salon_nail", "massage_parlor", "restaurant_back_of_house", "retail_overnight",
]

PRONOUNS = ["she/her", "he/him", "they/them"]
CONTACT_METHODS = ["phone", "caseworker_only"]
WORK_AUTH = ["yes", "in_process", "no"]
EDUCATION = ["none", "some_hs", "hs_diploma", "ged", "some_college",
             "associates", "bachelors"]
DISABILITIES = ["mobility", "chronic_pain", "ptsd", "cognitive", "none"]
CITABILITY = ["direct", "transferable", "unsafe"]
SOURCES = ["prior_employment", "exploitation", "education", "self_taught"]
GRADED_VALUES = ["trigger", "avoid", "ok"]
GRADED_KEYS = ["night_shift", "isolated_workplace", "customer_facing",
               "male_dominated_team", "uniformed_role", "requires_overnight_travel"]
TRAINING_APPETITE = ["none", "short", "moderate", "extensive"]
RECORD_CATEGORIES = ["prostitution_related", "drug_possession",
                     "theft_property", "other"]
LANG_CODES = ["en", "es", "vi", "ar", "zh", "ru", "tl", "fr", "ht", "ko", "pt", "so"]
STATE_CODES = ["TX", "AZ", "GA", "WA", "MN", "NJ", "NV", "OH", "CA", "FL",
               "MI", "CO", "OR", "TN", "IL", "NY"]
METROS = [
    "Houston, TX", "Phoenix, AZ", "Atlanta, GA", "Seattle, WA", "Minneapolis, MN",
    "Newark, NJ", "Las Vegas, NV", "Columbus, OH", "Fresno, CA", "Tampa, FL",
    "Detroit, MI", "Denver, CO", "San Antonio, TX", "Portland, OR", "Nashville, TN",
]

# Synthetic name pools (deliberately generic — no resemblance to real individuals).
FIRST_NAMES = ["Maria", "Aisha", "Linh", "Daniela", "Fatima", "Grace", "Yuki",
               "Sofia", "Naomi", "Priya", "Elena", "Rosa", "Hana", "Carmen",
               "Ava", "Mei", "Layla", "Jasmine", "Nadia", "Tanya"]
LAST_NAMES = ["Rivera", "Okafor", "Tran", "Santos", "Hassan", "Bennett", "Sato",
              "Morales", "Cole", "Patel", "Petrov", "Diaz", "Kim", "Vega",
              "Reed", "Chen", "Haddad", "Brooks", "Volkov", "Ortiz"]
NICKNAMES = ["Mari", "Ash", "Lin", "Dani", "Faty", "Gigi", "Yu", "Sof",
             "Nay", "Pri", "Lena", "Ro", "Han", "Carm", "Avi", "May"]

CASEWORKER_NOTES = [
    "Client is motivated and prefers structured, predictable work environments.",
    "Active safety planning in progress; avoid any contact-with-public exposure for now.",
    "Strong support network locally; main barrier is documentation, not motivation.",
    "Prefers small teams; large or male-dominated workplaces increase anxiety.",
    "Currently in temporary housing; income timeline is the top priority.",
    "Open to short training but cannot commit to multi-month programs due to childcare.",
    "Has reliable childcare on weekday mornings only.",
    "Recovering from injury; physically demanding roles should be flagged for review.",
    "Bilingual and interested in roles that use language skills.",
    "Cautious about anything resembling prior workplaces; review industry fit carefully.",
]

GOALS = [
    "Reach stable full-time employment with benefits within a year.",
    "Build toward a certification that leads to remote-capable work.",
    "Secure steady income to support dependents and move to permanent housing.",
    "Transition into an administrative or office support career path.",
    "Find safe, daytime work close to home while continuing therapy.",
    "Grow toward a supervisory role in a supportive, team-based setting.",
    "Use existing skills to enter a trade with clear advancement steps.",
    "Establish financial independence and rebuild credit over the next two years.",
    "Enter healthcare support work that offers training and upward mobility.",
    "Find flexible part-time work that scales up as confidence returns.",
]


# ─── LOAD REAL SKILL VOCAB ─────────────────────────────────────────────────────
def load_skill_vocab(occ_path: Path) -> set:
    """Parse the skills column of occupations.csv -> set of (id, name) pairs."""
    df = pd.read_csv(occ_path)
    if "skills" not in df.columns:
        raise ValueError(f"'skills' column not found in {occ_path}")
    vocab = set()
    for cell in df["skills"].dropna():
        items = ast.literal_eval(cell)
        for d in items:
            vocab.add((d["id"], d["name"]))
    if not vocab:
        raise ValueError("No skills parsed from occupations.csv — aborting.")
    return vocab


# ─── PROFILE COMPONENT BUILDERS ────────────────────────────────────────────────
_USED_LEGAL = set()
_USED_PREFERRED = set()


def make_identity():
    pron = random.choice(PRONOUNS)
    # Draw a unique legal name and a unique preferred name so no two synthetic
    # profiles share a name (avoids the appearance of templated/duplicate rows).
    while True:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        legal = f"{first} {last}"
        if legal not in _USED_LEGAL:
            _USED_LEGAL.add(legal)
            break
    while True:
        preferred = random.choice([first, random.choice(NICKNAMES)])
        if preferred not in _USED_PREFERRED:
            _USED_PREFERRED.add(preferred)
            break
    age = random.randint(22, 55)
    # Synthetic DOB: pick a plausible day in the birth year.
    birth_year = date.today().year - age
    dob = date(birth_year, random.randint(1, 12), random.randint(1, 28)).isoformat()
    # 555-01xx is a reserved fictional range — safe for synthetic phone numbers.
    safe_phone = f"(555) 01{random.randint(0, 9)}-{random.randint(0, 9999):04d}"
    return {
        "legal_name": legal,
        "preferred_name": preferred,
        "pronouns": pron,
        "dob": dob,
        "safe_phone": safe_phone,
        "safe_contact_method": random.choice(CONTACT_METHODS),
        "caseworker_notes": random.choice(CASEWORKER_NOTES),
    }


def make_languages():
    n = random.randint(1, 3)
    codes = random.sample(LANG_CODES, n)
    return [{"code": c, "fluency_1_to_5": random.randint(1, 5)} for c in codes]


# Only these (real vocab) skills are plausibly acquired in an exploitation
# context. We never tag skills like Programming or Reading Comprehension as
# exploitation-sourced.
EXPLOITATION_SKILLS = {
    "Active Listening", "Speaking", "Service Orientation", "Social Perceptiveness",
    "Time Management", "Coordination", "Persuasion", "Negotiation",
}

# Concrete, resume-ready reframings that hide origin by SOUNDING like ordinary
# work experience. No meta-language ("without disclosing", "origin", etc.).
SAFE_FRAMING_MAP = {
    "Active Listening": "Client intake and needs assessment",
    "Speaking": "Front-of-house customer communication",
    "Service Orientation": "High-volume customer service",
    "Social Perceptiveness": "De-escalation and rapport-building",
    "Time Management": "Coordinating schedules under pressure",
    "Coordination": "Multi-party logistics coordination",
    "Persuasion": "Customer retention and upselling",
    "Negotiation": "Vendor and client negotiation",
}


def safe_framing(name: str, source: str) -> str:
    """A sanitized, employment-ready rephrasing."""
    if source == "exploitation":
        # Exploitation-sourced skills are restricted to EXPLOITATION_SKILLS, all
        # of which have a concrete mapping; the fallback is just defensive.
        return SAFE_FRAMING_MAP.get(name, f"{name} in a customer-service setting")
    n = name.lower()
    if source == "prior_employment":
        return f"Applied {n} regularly in prior paid roles."
    if source == "education":
        return f"Developed {n} through coursework and training."
    return f"Self-developed {n} through independent practice."


def make_skills(vocab_list):
    n = random.randint(3, 6)
    chosen = random.sample(vocab_list, n)
    skills = []
    for sid, sname in chosen:
        # Exploitation source is only believable for a small set of soft skills.
        # For those, make it a realistic possibility so the safe-framing logic is
        # actually exercised; for everything else, exclude it entirely.
        if sname in EXPLOITATION_SKILLS:
            # SOURCES order: prior_employment, exploitation, education, self_taught
            source = random.choices(SOURCES, weights=[3, 4, 2, 2])[0]
        else:
            source = random.choice([s for s in SOURCES if s != "exploitation"])
        if source == "exploitation":
            # Never citable as direct work history.
            citability = random.choice(["transferable", "unsafe"])
        else:
            citability = random.choice(CITABILITY)
        skills.append({
            "skill_id": sid,
            "skill_name": sname,
            "level_1_to_5": random.randint(1, 5),
            "citability": citability,
            "safe_framing": safe_framing(sname, source),
            "source": source,
        })
    return skills


def make_exclusion_zones():
    n = random.randint(0, 2)
    zones = []
    for _ in range(n):
        zones.append({
            "lat": round(random.uniform(25.0, 48.0), 4),
            "lng": round(random.uniform(-124.0, -67.0), 4),
            "radius_mi": round(random.uniform(1.0, 25.0), 1),
        })
    return zones


def make_graded_constraints():
    # Weight toward "ok" so most profiles aren't uniformly over-constrained.
    return {k: random.choices(GRADED_VALUES, weights=[1, 2, 4])[0] for k in GRADED_KEYS}


def make_available_shifts():
    shifts = {s: random.random() < 0.6 for s in ("morning", "afternoon", "evening")}
    if not any(shifts.values()):  # ensure at least one available shift
        shifts[random.choice(list(shifts))] = True
    return shifts


def make_legal_profile():
    # Cap at 2 record categories for realism (most cases aren't stacked).
    k = random.randint(0, 2)
    records = random.sample(RECORD_CATEGORIES, k)
    # expungement_eligible is always a subset of record_categories.
    eligible = [c for c in records if random.random() < 0.5]
    return {
        "record_categories": records,
        "expungement_eligible": eligible,
        "jurisdiction": random.choice(STATE_CODES),
    }


def make_documents_held():
    licenses = []
    if random.random() < 0.25:
        licenses = random.sample(["cosmetology", "cna", "food_handler", "forklift"],
                                 random.randint(1, 2))
    return {
        "state_id": random.random() < 0.7,
        "drivers_license": random.random() < 0.5,
        "ssn": random.random() < 0.6,
        "work_authorization_doc": random.random() < 0.5,
        "passport": random.random() < 0.2,
        "professional_licenses": licenses,
    }


def make_base_profile(vocab_list):
    """A fully random, schema-valid profile (archetypes override on top of this)."""
    return {
        "identity": make_identity(),
        "languages": make_languages(),
        "current_metro": random.choice(METROS),
        "work_authorization": random.choice(WORK_AUTH),
        "has_vehicle": random.random() < 0.45,
        "has_valid_license": random.random() < 0.5,
        "transit_access": random.random() < 0.6,
        "education_highest": random.choice(EDUCATION),
        "disabilities": (["none"] if random.random() < 0.4
                         else random.sample([d for d in DISABILITIES if d != "none"],
                                            random.randint(1, 2))),
        "dependents": random.randint(0, 5),
        "skills": make_skills(vocab_list),
        "exclusion_zones": make_exclusion_zones(),
        "exclusion_industries": random.sample(INDUSTRY_VOCAB, random.randint(0, 3)),
        "exclusion_employers": ([] if random.random() < 0.6
                                else random.sample(
                                    ["[redacted-A]", "[redacted-B]", "[redacted-C]"],
                                    random.randint(1, 2))),
        "documentation_blockers": {
            "requires_clean_record": random.random() < 0.4,
            "requires_drivers_license": random.random() < 0.4,
            "requires_ssn": random.random() < 0.5,
            "requires_credit_check": random.random() < 0.3,
        },
        "graded_constraints": make_graded_constraints(),
        "max_commute_minutes": random.randint(20, 90),
        "available_shifts": make_available_shifts(),
        "legal_profile": make_legal_profile(),
        "documents_held": make_documents_held(),
        "industries_of_interest": random.sample(INDUSTRY_VOCAB, random.randint(0, 3)),
        "wage_minimum_hourly": round(random.uniform(15.0, 25.0), 2),
        "training_appetite": random.choice(TRAINING_APPETITE),
        "long_term_goal": random.choice(GOALS),
    }


# ─── SEEDED ARCHETYPES ─────────────────────────────────────────────────────────
def make_audit_trigger(vocab_list):
    """Over-constrained: very few jobs should survive the constraint engine."""
    p = make_base_profile(vocab_list)
    p["work_authorization"] = "no"
    p["has_valid_license"] = False
    p["graded_constraints"]["night_shift"] = "trigger"
    p["graded_constraints"]["isolated_workplace"] = "trigger"
    p["documentation_blockers"]["requires_drivers_license"] = True
    p["exclusion_industries"] = random.sample(INDUSTRY_VOCAB, 2)
    p["max_commute_minutes"] = random.randint(20, 25)
    # night_shift is a trigger, so interests must be day-compatible — exclude
    # retail_overnight and transportation.
    p["industries_of_interest"] = random.sample(
        ["domestic_work", "salon_nail", "restaurant_back_of_house"], 2)
    p["identity"]["caseworker_notes"] = (
        "Highly constrained profile; expect the engine to surface very few options "
        "and trigger a constraint audit for caseworker review."
    )
    return p


def make_expungement_leverage(vocab_list):
    """Single, clean leverage point: one expungement-eligible record category."""
    p = make_base_profile(vocab_list)
    # Exactly ONE record category, expungement-eligible — the clean leverage point.
    p["legal_profile"]["record_categories"] = ["prostitution_related"]
    p["legal_profile"]["expungement_eligible"] = ["prostitution_related"]
    p["documentation_blockers"]["requires_clean_record"] = True
    p["identity"]["caseworker_notes"] = (
        "Prior record is expungement-eligible; pursuing expungement unlocks "
        "clean-record-required roles."
    )
    return p


def generate_profiles(vocab):
    vocab_list = sorted(vocab)  # deterministic ordering for random.sample under seed
    profiles = []
    seeded = {}
    profiles.append(make_audit_trigger(vocab_list))
    seeded[0] = "audit_trigger"
    profiles.append(make_expungement_leverage(vocab_list))
    seeded[1] = "expungement_leverage"
    while len(profiles) < N_PROFILES:
        profiles.append(make_base_profile(vocab_list))
    return profiles, seeded


# ─── HARD VALIDATION (raises on failure, before any write) ─────────────────────
def validate_hard(profiles, vocab):
    for i, p in enumerate(profiles):
        for s in p["skills"]:
            if (s["skill_id"], s["skill_name"]) not in vocab:
                raise ValueError(
                    f"Profile {i}: skill ({s['skill_id']}, {s['skill_name']}) "
                    "not in occupations vocab.")
        for tok in p["exclusion_industries"] + p["industries_of_interest"]:
            if tok not in INDUSTRY_VOCAB:
                raise ValueError(f"Profile {i}: industry token '{tok}' not in vocab.")
        records = set(p["legal_profile"]["record_categories"])
        eligible = set(p["legal_profile"]["expungement_eligible"])
        if not eligible.issubset(records):
            raise ValueError(
                f"Profile {i}: expungement_eligible not subset of record_categories.")


# ─── SCHEMA + INTEGRITY CHECKS (for the report; non-raising) ───────────────────
def _is_bool(x):
    return isinstance(x, bool)


def _is_int_in(x, lo, hi):
    return isinstance(x, int) and not isinstance(x, bool) and lo <= x <= hi


def _is_num_in(x, lo, hi):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and lo <= x <= hi


def _chk_identity(p):
    d = p.get("identity")
    if not isinstance(d, dict):
        return "not a dict"
    req = ["legal_name", "preferred_name", "pronouns", "dob",
           "safe_phone", "safe_contact_method", "caseworker_notes"]
    for k in req:
        if k not in d or not isinstance(d[k], str) or not d[k]:
            return f"missing/empty {k}"
    if d["pronouns"] not in PRONOUNS:
        return "bad pronouns"
    if d["safe_contact_method"] not in CONTACT_METHODS:
        return "bad safe_contact_method"
    try:
        born = date.fromisoformat(d["dob"])
    except ValueError:
        return "bad dob format"
    age = (date.today() - born).days // 365
    if not (22 <= age <= 55):
        return f"age {age} out of 22-55"
    return None


def _chk_languages(p):
    v = p.get("languages")
    if not isinstance(v, list) or not (1 <= len(v) <= 3):
        return "must be list of 1-3"
    for lang in v:
        if not isinstance(lang, dict) or "code" not in lang or "fluency_1_to_5" not in lang:
            return "bad language object"
        if lang["code"] not in LANG_CODES:
            return f"bad code {lang['code']}"
        if not _is_int_in(lang["fluency_1_to_5"], 1, 5):
            return "fluency out of 1-5"
    return None


def _chk_skills(p, vocab):
    v = p.get("skills")
    if not isinstance(v, list) or not (3 <= len(v) <= 6):
        return "must be list of 3-6"
    for s in v:
        keys = {"skill_id", "skill_name", "level_1_to_5", "citability",
                "safe_framing", "source"}
        if not isinstance(s, dict) or not keys.issubset(s):
            return "missing skill keys"
        if (s["skill_id"], s["skill_name"]) not in vocab:
            return f"skill not in vocab: {s['skill_id']}"
        if not _is_int_in(s["level_1_to_5"], 1, 5):
            return "level out of 1-5"
        if s["citability"] not in CITABILITY:
            return f"bad citability {s['citability']}"
        if s["source"] not in SOURCES:
            return f"bad source {s['source']}"
        if not isinstance(s["safe_framing"], str) or not s["safe_framing"]:
            return "empty safe_framing"
    return None


def _chk_exclusion_zones(p):
    v = p.get("exclusion_zones")
    if not isinstance(v, list) or len(v) > 2:
        return "must be list of 0-2"
    for z in v:
        if not isinstance(z, dict) or not {"lat", "lng", "radius_mi"}.issubset(z):
            return "bad zone object"
        if not _is_num_in(z["lat"], -90, 90) or not _is_num_in(z["lng"], -180, 180):
            return "bad lat/lng"
        if not _is_num_in(z["radius_mi"], 0, 1000):
            return "bad radius"
    return None


def _chk_industry_list(p, key):
    v = p.get(key)
    if not isinstance(v, list) or len(v) > 3:
        return "must be list of 0-3"
    for tok in v:
        if tok not in INDUSTRY_VOCAB:
            return f"bad token {tok}"
    return None


def _chk_doc_blockers(p):
    d = p.get("documentation_blockers")
    keys = ["requires_clean_record", "requires_drivers_license",
            "requires_ssn", "requires_credit_check"]
    if not isinstance(d, dict):
        return "not a dict"
    for k in keys:
        if k not in d or not _is_bool(d[k]):
            return f"missing/non-bool {k}"
    return None


def _chk_graded(p):
    d = p.get("graded_constraints")
    if not isinstance(d, dict):
        return "not a dict"
    for k in GRADED_KEYS:
        if k not in d or d[k] not in GRADED_VALUES:
            return f"missing/bad {k}"
    return None


def _chk_shifts(p):
    d = p.get("available_shifts")
    if not isinstance(d, dict):
        return "not a dict"
    for k in ("morning", "afternoon", "evening"):
        if k not in d or not _is_bool(d[k]):
            return f"missing/non-bool {k}"
    return None


def _chk_legal(p):
    d = p.get("legal_profile")
    if not isinstance(d, dict):
        return "not a dict"
    rc = d.get("record_categories")
    ee = d.get("expungement_eligible")
    if not isinstance(rc, list) or any(c not in RECORD_CATEGORIES for c in rc):
        return "bad record_categories"
    if not isinstance(ee, list) or any(c not in RECORD_CATEGORIES for c in ee):
        return "bad expungement_eligible"
    if not set(ee).issubset(set(rc)):
        return "expungement not subset of record"
    if not (isinstance(d.get("jurisdiction"), str) and len(d["jurisdiction"]) == 2):
        return "bad jurisdiction"
    return None


def _chk_documents(p):
    d = p.get("documents_held")
    if not isinstance(d, dict):
        return "not a dict"
    for k in ("state_id", "drivers_license", "ssn", "work_authorization_doc", "passport"):
        if k not in d or not _is_bool(d[k]):
            return f"missing/non-bool {k}"
    if not isinstance(d.get("professional_licenses"), list):
        return "professional_licenses not a list"
    return None


def _chk_disabilities(p):
    v = p.get("disabilities")
    if not isinstance(v, list) or not v:
        return "must be non-empty list"
    if any(x not in DISABILITIES for x in v):
        return "bad disability value"
    return None


# field name -> checker producing an error string or None
def schema_checkers(vocab):
    return {
        "identity": _chk_identity,
        "languages": _chk_languages,
        "current_metro": lambda p: None if isinstance(p.get("current_metro"), str)
        and p["current_metro"] else "missing/empty",
        "work_authorization": lambda p: None if p.get("work_authorization") in WORK_AUTH
        else "bad enum",
        "has_vehicle": lambda p: None if _is_bool(p.get("has_vehicle")) else "non-bool",
        "has_valid_license": lambda p: None if _is_bool(p.get("has_valid_license"))
        else "non-bool",
        "transit_access": lambda p: None if _is_bool(p.get("transit_access"))
        else "non-bool",
        "education_highest": lambda p: None if p.get("education_highest") in EDUCATION
        else "bad enum",
        "disabilities": _chk_disabilities,
        "dependents": lambda p: None if _is_int_in(p.get("dependents"), 0, 5)
        else "out of 0-5",
        "skills": lambda p: _chk_skills(p, vocab),
        "exclusion_zones": _chk_exclusion_zones,
        "exclusion_industries": lambda p: _chk_industry_list(p, "exclusion_industries"),
        "exclusion_employers": lambda p: None if isinstance(p.get("exclusion_employers"),
                                                            list) else "not a list",
        "documentation_blockers": _chk_doc_blockers,
        "graded_constraints": _chk_graded,
        "max_commute_minutes": lambda p: None
        if _is_int_in(p.get("max_commute_minutes"), 20, 90) else "out of 20-90",
        "available_shifts": _chk_shifts,
        "legal_profile": _chk_legal,
        "documents_held": _chk_documents,
        "industries_of_interest": lambda p: _chk_industry_list(p, "industries_of_interest"),
        "wage_minimum_hourly": lambda p: None
        if _is_num_in(p.get("wage_minimum_hourly"), 15.0, 25.0) else "out of 15-25",
        "training_appetite": lambda p: None if p.get("training_appetite") in TRAINING_APPETITE
        else "bad enum",
        "long_term_goal": lambda p: None if isinstance(p.get("long_term_goal"), str)
        and p["long_term_goal"] else "missing/empty",
    }


# ─── REPORT ────────────────────────────────────────────────────────────────────
def _age_of(p):
    return (date.today() - date.fromisoformat(p["identity"]["dob"])).days // 365


def _hard_blockers(p):
    n = sum(1 for v in p["documentation_blockers"].values() if v)
    n += sum(1 for v in p["graded_constraints"].values() if v == "trigger")
    return n


def build_report(profiles, seeded, vocab):
    lines = []
    issues = []

    def w(s=""):
        lines.append(s)

    # 1. HEADER
    w("=" * 78)
    w("SURVIVOR PROFILE VALIDATION REPORT")
    w("=" * 78)
    w(f"Total profiles generated : {len(profiles)}")
    w(f"RNG seed                 : {SEED}")
    w(f"Source file              : {OCC_FILE.as_posix()}")
    w(f"Generated at             : {datetime.now().isoformat(timespec='seconds')}")
    w()

    # 2. VOCAB CHECK
    w("-" * 78)
    w("1. SKILL VOCAB CHECK")
    w("-" * 78)
    w(f"Distinct (id, name) skill pairs in occupations.csv : {len(vocab)}")
    used = set()
    bad_skills = []
    for i, p in enumerate(profiles):
        for s in p["skills"]:
            pair = (s["skill_id"], s["skill_name"])
            used.add(pair)
            if pair not in vocab:
                bad_skills.append(f"profile {i}: {pair}")
    w(f"Distinct skill pairs USED across profiles          : {len(used)}")
    if bad_skills:
        issues.extend(bad_skills)
        w("FAIL - skills not in vocab:")
        for b in bad_skills:
            w(f"   {b}")
    else:
        w("PASS - every skill_id/skill_name used exists in the occupations vocab.")
    w()

    # 3. SCHEMA CHECK
    w("-" * 78)
    w("2. SCHEMA CHECK (per field, across all profiles)")
    w("-" * 78)
    checkers = schema_checkers(vocab)
    for field, fn in checkers.items():
        failures = []
        for i, p in enumerate(profiles):
            err = fn(p)
            if err is not None:
                failures.append(f"profile {i} ({err})")
        status = "PASS" if not failures else "FAIL"
        w(f"  [{status}] {field}")
        if failures:
            issues.extend(f"schema:{field}:{f}" for f in failures)
            for f in failures:
                w(f"          - {f}")
    w()

    # 4. CONSTRAINT INTEGRITY CHECK
    w("-" * 78)
    w("3. CONSTRAINT INTEGRITY CHECK")
    w("-" * 78)
    exp_violations = []
    for i, p in enumerate(profiles):
        rc = set(p["legal_profile"]["record_categories"])
        ee = set(p["legal_profile"]["expungement_eligible"])
        if not ee.issubset(rc):
            exp_violations.append(f"profile {i}: {sorted(ee - rc)} not in record")
    w(f"  [{'PASS' if not exp_violations else 'FAIL'}] "
      "expungement_eligible is a subset of record_categories")
    for v in exp_violations:
        issues.append(f"expungement:{v}")
        w(f"          - {v}")

    ind_violations = []
    for i, p in enumerate(profiles):
        for tok in p["exclusion_industries"] + p["industries_of_interest"]:
            if tok not in INDUSTRY_VOCAB:
                ind_violations.append(f"profile {i}: '{tok}'")
    w(f"  [{'PASS' if not ind_violations else 'FAIL'}] "
      "industry tokens within controlled vocab")
    for v in ind_violations:
        issues.append(f"industry:{v}")
        w(f"          - {v}")

    exp_skill_violations = []
    for i, p in enumerate(profiles):
        for s in p["skills"]:
            if s["source"] == "exploitation" and s["citability"] == "direct":
                exp_skill_violations.append(f"profile {i}: {s['skill_id']}")
    w(f"  [{'PASS' if not exp_skill_violations else 'FAIL'}] "
      "exploitation-sourced skills never citability=='direct'")
    for v in exp_skill_violations:
        issues.append(f"exploitation_citability:{v}")
        w(f"          - {v}")
    w()

    # 5. ARCHETYPE CHECK
    w("-" * 78)
    w("4. ARCHETYPE CHECK")
    w("-" * 78)
    audit_idx = next((i for i, n in seeded.items() if n == "audit_trigger"), None)
    exp_idx = next((i for i, n in seeded.items() if n == "expungement_leverage"), None)

    if audit_idx is not None:
        a = profiles[audit_idx]
        gc = a["graded_constraints"]
        db = a["documentation_blockers"]
        checks = [
            ("work_authorization == 'no'", a["work_authorization"], a["work_authorization"] == "no"),
            ("night_shift == 'trigger'", gc["night_shift"], gc["night_shift"] == "trigger"),
            ("isolated_workplace == 'trigger'", gc["isolated_workplace"],
             gc["isolated_workplace"] == "trigger"),
            ("has_valid_license == False", a["has_valid_license"], a["has_valid_license"] is False),
            ("requires_drivers_license == True", db["requires_drivers_license"],
             db["requires_drivers_license"] is True),
            ("len(exclusion_industries) == 2", len(a["exclusion_industries"]),
             len(a["exclusion_industries"]) == 2),
            ("max_commute_minutes <= 25", a["max_commute_minutes"],
             a["max_commute_minutes"] <= 25),
        ]
        w(f"  AUDIT-TRIGGER  (profile index {audit_idx}, "
          f"{profiles[audit_idx]['identity']['preferred_name']})")
        for label, actual, ok in checks:
            w(f"     [{'OK ' if ok else 'BAD'}] {label:38s} actual={actual}")
            if not ok:
                issues.append(f"archetype-audit:{label}")
    else:
        issues.append("archetype-audit:missing")
        w("  AUDIT-TRIGGER archetype MISSING")
    w()

    if exp_idx is not None:
        e = profiles[exp_idx]
        rc = e["legal_profile"]["record_categories"]
        ee = e["legal_profile"]["expungement_eligible"]
        rcr = e["documentation_blockers"]["requires_clean_record"]
        checks = [
            ("prostitution_related in record_categories", rc, "prostitution_related" in rc),
            ("prostitution_related in expungement_eligible", ee, "prostitution_related" in ee),
            ("requires_clean_record == True", rcr, rcr is True),
        ]
        w(f"  EXPUNGEMENT-LEVERAGE  (profile index {exp_idx}, "
          f"{profiles[exp_idx]['identity']['preferred_name']})")
        for label, actual, ok in checks:
            w(f"     [{'OK ' if ok else 'BAD'}] {label:44s} actual={actual}")
            if not ok:
                issues.append(f"archetype-expungement:{label}")
    else:
        issues.append("archetype-expungement:missing")
        w("  EXPUNGEMENT-LEVERAGE archetype MISSING")
    w()

    # 6. DIVERSITY SNAPSHOT
    w("-" * 78)
    w("5. DIVERSITY SNAPSHOT")
    w("-" * 78)
    hdr = f"{'#':>2}  {'name':10s} {'metro':17s} {'age':>3} {'education':12s} " \
          f"{'work_auth':10s} {'sk':>2} {'blk':>3}  record_categories"
    w(hdr)
    w("-" * len(hdr))
    for i, p in enumerate(profiles):
        seed_mark = "*" if i in seeded else " "
        rc = ",".join(p["legal_profile"]["record_categories"]) or "-"
        w(f"{i:>2}{seed_mark} {p['identity']['preferred_name'][:10]:10s} "
          f"{p['current_metro'][:17]:17s} {_age_of(p):>3} "
          f"{p['education_highest']:12s} {p['work_authorization']:10s} "
          f"{len(p['skills']):>2} {_hard_blockers(p):>3}  {rc}")
    w("  (* = seeded archetype)")
    w()

    # 7. OVERALL
    w("=" * 78)
    if issues:
        w(f"FAILED: {len(issues)} issues")
        for it in issues:
            w(f"   - {it}")
    else:
        w("ALL CHECKS PASSED")
    w("=" * 78)

    return "\n".join(lines), issues


# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    random.seed(SEED)

    if not OCC_FILE.exists():
        raise FileNotFoundError(
            f"{OCC_FILE} not found. Run scripts/clean_data.py first.")

    vocab = load_skill_vocab(OCC_FILE)
    profiles, seeded = generate_profiles(vocab)

    # Hard validation — must pass before anything is written.
    validate_hard(profiles, vocab)

    # One-line summary per profile.
    print("Generated profiles:")
    for i, p in enumerate(profiles):
        tag = f" [{seeded[i]}]" if i in seeded else ""
        rc = ",".join(p["legal_profile"]["record_categories"]) or "none"
        print(f"  {i:>2}. {p['identity']['preferred_name']:10s} | "
              f"{p['current_metro']:17s} | skills={len(p['skills'])} | "
              f"record=[{rc}]{tag}")
    print()

    OUT_JSON.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    print(f"[OK] Wrote {len(profiles)} profiles -> {OUT_JSON.as_posix()}\n")

    report, issues = build_report(profiles, seeded, vocab)
    OUT_REPORT.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n[OK] Wrote validation report -> {OUT_REPORT.as_posix()}")

    if issues:
        raise SystemExit(f"Validation report flagged {len(issues)} issue(s).")


if __name__ == "__main__":
    main()
