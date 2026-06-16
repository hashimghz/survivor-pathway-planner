# Survivor Career Pathway Planner
## USAII Global AI Hackathon 2026 | Brief 5 Direction B | Graduate Track

---

## Project Structure

```
pathway_planner/
├── data/
│   └── build_graph.py        ← DATA LAYER: occupational graph builder
├── engine/
│   └── constraint_engine.py  ← CONSTRAINT ENGINE: core AI component
├── app/
│   └── app.py                ← STREAMLIT UI: caseworker interface
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit app
```bash
streamlit run app/app.py
```

The app opens at http://localhost:8501

### 3. Test the constraint engine directly
```bash
python engine/constraint_engine.py
```

### 4. Rebuild the data layer
```bash
python data/build_graph.py
```

---

## What Each File Does

### data/build_graph.py
- Defines 15 occupations and 8 training programs (synthetic O*NET-style data)
- Builds a directed NetworkX graph: START → training programs → occupations
- **To swap in real O*NET data:** Replace OCCUPATIONS and TRAINING_PROGRAMS lists
  with calls to https://services.onetcenter.org/ (free API, register at O*NET)

### engine/constraint_engine.py
- Takes a `ConstraintProfile` dataclass as input
- Filters the graph by applying all constraints simultaneously
- Runs graph traversal (nx.all_simple_paths) on the viable subgraph
- Scores and ranks up to 3 viable pathways
- Returns `PathwayResult` objects + `ConstraintAuditResult`
- Triggers audit if fewer than 3 viable paths found

### app/app.py
- Streamlit caseworker interface
- Sidebar: constraint profile intake form (all 10 constraint fields)
- Main panel: pathway comparison with income trajectory charts
- Constraint audit alert banner when triggered
- Exclusion transparency log (every excluded node + reason)
- Caseworker decision section with supervisor escalation flag

---

## How the Constraint Engine Works

```
Input: ConstraintProfile
    ↓
Build viable subgraph (remove excluded nodes)
    ↓
Traverse graph: START → [optional training] → occupation
    ↓
Score each path:
  - Does it meet income deadline?
  - Does it meet income threshold?
  - Weeks to first income
  - Monthly income at start and 12 months
  - Safety fit notes
    ↓
Rank and deduplicate (one path per final occupation)
    ↓
Return top 3 PathwayResults + ConstraintAuditResult
```

---

## Constraint Fields

| Field | Type | What It Filters |
|-------|------|-----------------|
| excluded_industries | List[str] | Removes all occupations in excluded industries |
| excluded_shift_types | List[str] | Removes occupations where ALL shifts are excluded |
| exclude_isolated_workplaces | bool | Removes isolated workplace occupations |
| exclude_high_surveillance | bool | Removes high-surveillance occupations |
| has_government_id | bool | Required by most occupations |
| has_ssn | bool | Required for some occupations and training |
| has_work_authorization | bool | Required for specific occupations |
| has_background_check_clearance | bool | Required for childcare |
| existing_skills | List[str] | (Not yet filtering — future: boost scoring) |
| income_deadline_weeks | int | Removes paths that exceed the time horizon |
| minimum_monthly_income | float | Removes occupations below income threshold |

---

## Responsible AI Design

### Risk: Constraint Encoding Bias
Caseworkers may apply constraints over-broadly (excluding entire industries rather
than specific employers), systematically narrowing pathways for certain survivors.

### Mitigation: Constraint Audit Layer
- Triggers when fewer than 3 viable paths are found
- Flags which constraint types are responsible for most exclusions
- Prompts caseworker to review specificity before proceeding

### Human-in-the-Loop
- System surfaces 2-3 options — caseworker selects
- No pathway is ever presented to the survivor directly by the system
- Supervisor co-review flag for legal/immigration/safety cases
- All decisions documented in caseworker notes

---

## Next Steps for Day 3-4

- [ ] Connect to real O*NET Web Services API
- [ ] Add skill-based scoring (boost pathways matching existing skills)
- [ ] Add local training program catalog for your city/region
- [ ] Add demographic audit logging for quarterly review
- [ ] Write model card (see proposal document)

---

## Submission Checklist

- [ ] Qualifier Approval Code confirmed (check email from June 11-13)
- [ ] Working Streamlit demo recorded as video
- [ ] Devpost fields completed
- [ ] Responsible AI statement written
- [ ] Tools disclosure complete (NetworkX, Streamlit, Plotly, Python)
- [ ] Data disclosure complete (synthetic O*NET-style data)
- [ ] Submit before June 21 at 11:59 PM ET
