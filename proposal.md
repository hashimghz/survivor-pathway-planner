The pipeline has one main flow and one parallel branch. The transformations are what matter most — each stage produces a fundamentally different data object, which is how you know layers aren't duplicating work.

## Layer-by-layer: input → process → output

![Flow Architecture](.\five_layer_pipeline_data_flow.png)


Each box in the diagram is a function with a specific data signature. The data object morphs at each step.

### Pre-pipeline: anonymizer

```python
# Input: encrypted survivor profile from SQLite
{
  "id": "uuid",
  "legal_name_ct": b"...",          # AES-256-GCM ciphertext
  "languages": [...],
  "current_metro": "Tampa",
  "skills_raw": [
    {"text": "managed cash for boss", "level": 4, "source": "exploitation"},
    {"text": "front desk receptionist", "level": 3, "source": "prior_employment"}
  ],
  "hard_constraints": {...}, "graded_constraints": {...}, ...
}

# Output: anonymous ticket (no PII anywhere)
{
  "ticket_id": "hmac_sha256(profile_uuid, pepper)",  # stable across sessions
  "skills_raw": [...],              # text descriptions only
  "languages": [...],
  "current_metro": "Tampa",
  "hard_constraints": {...},
  "graded_constraints": {...},
  "stability_needs": {...},
  "legal_profile": {...},
  "documentation_status": {...},
  "goals": {...}
}
```

The ticket is what every downstream layer sees. PII never leaves this box.

### L1: skill mapping

```python
# Input: ticket with skills_raw (free text)
# Process: embed each skill description with bge-small-en-v1.5,
#          cosine similarity vs pre-embedded O*NET skill catalog,
#          top-1 match with confidence threshold
# Output: ticket with mapped_skills (O*NET IDs attached)

{
  "ticket_id": "...",
  "mapped_skills": [
    {
      "raw_text": "managed cash for boss",
      "onet_skill_id": "2.A.1.f",
      "canonical_name": "Mathematics — Basic counting",
      "confidence": 0.87,
      "level": 4,
      "citability": "transferable",
      "safe_framing": "cash handling, high-volume environment",
      "source": "exploitation"
    },
    {
      "raw_text": "front desk receptionist",
      "onet_skill_id": "2.A.1.a",
      "canonical_name": "Customer service",
      "confidence": 0.94,
      "level": 3,
      "citability": "direct",
      "safe_framing": "customer service",
      "source": "prior_employment"
    }
  ],
  "low_confidence_mappings": [],   # any skill <0.6 confidence surfaced here
  # all other ticket fields pass through unchanged
}
```

L1 *only* enriches skills_raw with canonical IDs. It does not filter, rank, or judge fit.

### L2: veto filter

```python
# Input: mapped ticket + full 988-occupation O*NET catalog
# Process: each occupation tested against every hard constraint rule;
#          a single failure removes it; reasons recorded for the excluded set
# Output: (filtered candidates, excluded set with rules)

filtered_candidates = [
  {"onet_code": "43-4051.00", "title": "Customer Service Rep", ...},
  {"onet_code": "29-2071.00", "title": "Medical Records Specialist", ...},
  ...  # maybe 80-120 of the 988 survive
]

excluded_set = [
  {"onet_code": "35-3023.00", "title": "Fast Food Server",
   "failed_rule": "industry_exclusion", "details": "hospitality"},
  {"onet_code": "53-3032.00", "title": "Truck Driver",
   "failed_rule": "documentation_blocker", "details": "requires_drivers_license"},
  ...
]
```

L2 does the hard binary cuts on safety/legal/documentation. No scoring, no ranking — just a yes/no test per rule. The `excluded_set` is the input for both the filtered-out panel in the UI and Layer 5.

### L3: fuzzy TOPSIS

```python
# Input: filtered candidates + ticket's graded constraints, stability needs, mapped skills
# Process: build a decision matrix of (candidate × criteria),
#          normalize, weight by survivor preference,
#          compute distance to ideal and anti-ideal,
#          rank by similarity score
# Output: ranked candidates with full criteria breakdown

ranked = [
  {
    "onet_code": "43-4051.00",
    "title": "Customer Service Rep",
    "topsis_score": 0.84,
    "criteria_breakdown": {
      "skill_match": 0.91,        # from L1's mapped skills × O*NET importance
      "wage_fit": 0.78,
      "commute_fit": 0.85,
      "shift_fit": 1.0,           # from graded constraint night_shift
      "isolation_fit": 0.62,      # from graded constraint isolated_workplace
      "customer_facing_fit": 0.95,
      "uniformed_role_fit": 1.0,
      "male_dominated_fit": 0.7,
      "schedule_fit": 1.0,        # from stability_needs.available_shifts
    }
  },
  ...
]
```

L3 takes everything that passed L2 and ranks it on graded criteria. The criteria_breakdown is what makes it explainable: every candidate carries the score it earned along each dimension. The "fuzzy" handles ambiguity in survivor preferences — `trigger` isn't a single number, it's a band — so you compute a fuzzy distance instead of a scalar.

### L4: LLM reasoner

```python
# Input: top 5 ranked candidates + the anonymous ticket + criteria breakdown
# Process: structured prompt to Claude, JSON-schema-enforced output
# Output: enriched recommendations

enriched = [
  {
    **ranked[0],                    # all of L3's data passes through
    "fit_explanation": "Day-shift, customer-facing role with light supervision...",
    "safe_resume_framing": [
      "3+ years customer service experience in high-volume environments",
      "Bilingual Spanish-English communication",
      "Cash handling and basic transaction reconciliation"
    ],
    "risk_flags": [
      "Verify whether reception desk is street-facing before accepting"
    ],
    "upskill_next_step": "CompTIA A+ certification opens 14 additional roles..."
  },
  ...
]
```

L4 only *explains* — it does not change the ranking. The top-5 it sees is the top-5 L3 produced. The LLM is the natural-language layer over an already-decided ranking.

### L5: sensitivity analysis (sidecar)

```python
# Input: excluded_set from L2 + the ticket's hard constraints
# Process: for each hard constraint, recompute filter with it relaxed,
#          measure delta in candidate set size
# Output: ranked relaxation impact

sensitivity_report = [
  {"constraint": "requires_drivers_license", "jobs_unlocked": 47,
   "intervention_hint": "DMV documentation pathway"},
  {"constraint": "industry:hospitality",     "jobs_unlocked": 12,
   "intervention_hint": "(not actionable — safety-critical)"},
  {"constraint": "requires_clean_record",    "jobs_unlocked": 8,
   "intervention_hint": "vacatur filing for prostitution-related charges"},
  ...
]
```

L5 operates on the *excluded set*, not on the surviving candidates. That's why it can run in parallel with L3 — they consume different data.

## The no-overlap principle

Every constraint, skill, and signal in the ticket gets used by exactly one layer. This is the partition that prevents the layers from doing redundant work.

| What | Owned by | What gets done with it |
|---|---|---|
| Free-text skill descriptions | L1 | Map to canonical O*NET IDs |
| O*NET skill ID + level + survivor's match | L3 | Skill_match criterion in TOPSIS |
| Hard constraints (geography, industry, employer, docs, background check) | L2 | Binary yes/no filter |
| Graded constraints (night shift, isolation, customer-facing, male-dominated, uniformed) | L3 | Continuous fit score per criterion in TOPSIS |
| Stability needs (commute, available shifts, wage floor) | L3 | Continuous fit score criteria |
| Citability flags + safe_framing | L4 | Resume bullet generation |
| Goals / industries of interest | L4 | Upskill suggestion |
| Excluded set | L5 | Sensitivity analysis (parallel) |

Notice what's *not* on this list: nothing appears in two layers. The hard constraints don't get re-checked in L3 because they were already cut in L2. The graded constraints don't appear in L2 because they're not yes/no. Skills aren't compared with embeddings at ranking time — L1 already turned them into canonical IDs and L3 uses those IDs against O*NET's structured importance ratings.

## Recall safeguards: why we don't quietly lose good matches

This is the part you're right to worry about — a stack of layers can compound false negatives. Five safeguards:

**1. L1 has a confidence threshold, not a silent drop.** When the sentence transformer's top-1 match is below 0.6 confidence, the skill goes into `low_confidence_mappings` rather than being dropped. The caseworker UI surfaces these for review: "we couldn't confidently map 'handled appointment book' — is this customer service, scheduling, or administrative?" This converts the failure mode from silent loss to explicit review.

**2. L2 surfaces the boundary, doesn't hide it.** Every excluded job carries the rule that excluded it. The UI's filtered-out panel shows the caseworker exactly what was cut and why. If 90% of jobs were cut by one constraint, that's a discovery, not a bug — and L5 quantifies it.

**3. L3 is soft scoring, not filtering.** A candidate with one weak dimension doesn't disappear — it ranks lower. The criteria_breakdown lets the caseworker see "this one would be great except for the long commute" and decide whether to surface it anyway.

**4. Top-N is configurable, not fixed at 5.** L4 takes the top 5 by default, but the API lets the caseworker request top 10 or 20. There's also a "borderline" view: jobs that just passed L2 but ranked low in L3 — useful when the caseworker wants to see options the system thought were marginal.

**5. L5 makes "what was almost matched" actionable.** This is the safeguard that makes the constraint system honest. If a survivor's lack of a driver's license is cutting 47 jobs, the caseworker sees it and can prioritize the DMV pathway as an intervention. The constraint isn't permanently hidden — it's surfaced as the leverage point.

The thing that ties it together: at no point in the pipeline does a candidate silently vanish without a recorded reason. L1 surfaces uncertain mappings, L2 records exclusion rules, L3 retains all surviving candidates with scores, L4 doesn't filter at all, L5 quantifies what was cut. Every drop is documented. That's the recall guarantee.