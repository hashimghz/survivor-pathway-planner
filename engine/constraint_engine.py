"""
CONSTRAINT ENGINE — constraint_engine.py
Takes a survivor constraint profile and returns viable, constraint-safe pathways.

This is the core AI component. It:
1. Takes a structured constraint profile from the caseworker intake form
2. Filters the occupational graph to remove excluded nodes
3. Traverses the filtered graph to find viable paths
4. Scores and ranks paths by time-to-income, wage, and safety fit
5. Returns the top 3 paths with full explanation
"""

import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import networkx as nx

# Add data directory to path
DATA_DIR = Path(__file__).parent.parent / "data"
sys.path.insert(0, str(DATA_DIR))
from build_graph import build_pathway_graph, OCCUPATIONS, TRAINING_PROGRAMS


# ─── CONSTRAINT PROFILE SCHEMA ───────────────────────────────────────────────

@dataclass
class ConstraintProfile:
    """
    The structured intake form the caseworker fills out.
    Every field is a filter applied to the pathway graph.
    """
    # Hard exclusions — these are removed from the graph entirely
    excluded_industries: List[str] = field(default_factory=list)
    excluded_shift_types: List[str] = field(default_factory=list)
    excluded_job_codes: List[str] = field(default_factory=list)  # specific employers/jobs

    # Environment restrictions
    exclude_isolated_workplaces: bool = False
    exclude_high_surveillance: bool = False

    # Documentation available
    has_government_id: bool = True
    has_ssn: bool = False
    has_work_authorization: bool = False
    has_background_check_clearance: bool = False
    has_cosmetology_license: bool = False

    # Existing skills (from intake)
    existing_skills: List[str] = field(default_factory=list)

    # Time and income constraints
    income_deadline_weeks: Optional[int] = None  # weeks until income is needed
    minimum_monthly_income: float = 1500.0       # minimum acceptable monthly income

    # Survivor identifier (anonymized — for audit logging only)
    case_id: str = "CASE-UNKNOWN"


# ─── PATHWAY RESULT ──────────────────────────────────────────────────────────

@dataclass
class PathwayResult:
    """A single viable pathway returned to the caseworker."""
    path_id: int
    nodes: List[str]
    node_titles: List[str]
    node_types: List[str]

    # Outcome estimates
    weeks_to_first_income: int
    monthly_income_at_start: float
    monthly_income_at_12_months: float
    training_steps_required: int

    # Safety and fit
    safety_fit_notes: List[str]
    constraint_flags: List[str]   # any borderline items caseworker should review
    confidence_level: str          # HIGH / MEDIUM / LOW based on data completeness

    # Audit
    why_viable: str
    meets_income_deadline: bool
    meets_income_threshold: bool


# ─── CONSTRAINT AUDIT RESULT ─────────────────────────────────────────────────

@dataclass
class ConstraintAuditResult:
    """
    Returned when the constraint profile produces fewer than 3 viable paths.
    Prompts the caseworker to review constraint specificity before proceeding.
    """
    viable_path_count: int
    audit_triggered: bool
    flags: List[str]
    suggestion: str


# ─── CORE ENGINE ─────────────────────────────────────────────────────────────

class ConstraintEngine:

    MINIMUM_VIABLE_PATHS = 3  # Triggers audit if fewer paths returned
    AUDIT_THRESHOLD = 3

    def __init__(self):
        self.graph = build_pathway_graph()
        self.occupations = {o["code"]: o for o in OCCUPATIONS}
        self.training_programs = {t["code"]: t for t in TRAINING_PROGRAMS}

    def _docs_available(self, profile: ConstraintProfile) -> List[str]:
        """Build list of available documentation from profile."""
        docs = []
        if profile.has_government_id:
            docs.append("ID")
        if profile.has_ssn:
            docs.append("SSN")
        if profile.has_work_authorization:
            docs.append("work_auth")
        if profile.has_background_check_clearance:
            docs.append("background_check")
        if profile.has_cosmetology_license:
            docs.append("cosmetology_license")
        return docs

    def _occupation_is_viable(
        self, occ_code: str, profile: ConstraintProfile, available_docs: List[str]
    ) -> tuple[bool, List[str]]:
        """
        Returns (is_viable, list_of_reasons_if_not_viable).
        Checks ALL constraints simultaneously — this is the key advantage over
        a simple keyword job matcher.
        """
        if occ_code not in self.occupations:
            return False, ["Occupation code not found in dataset"]

        occ = self.occupations[occ_code]
        reasons = []

        # 1. Industry exclusion
        if occ["industry"] in profile.excluded_industries:
            reasons.append(f"Industry excluded: {occ['industry']}")

        # 2. Specific job code exclusion
        if occ_code in profile.excluded_job_codes:
            reasons.append("Specific occupation excluded by caseworker")

        # 3. Shift type — ALL available shifts must be acceptable
        available_shifts = set(occ["shift_types"])
        excluded_shifts = set(profile.excluded_shift_types)
        if available_shifts.issubset(excluded_shifts):
            reasons.append(f"All available shift types excluded: {occ['shift_types']}")

        # 4. Workplace environment restrictions
        if profile.exclude_isolated_workplaces and occ["isolated_workplace"]:
            reasons.append("Isolated workplace — excluded by safety constraint")
        if profile.exclude_high_surveillance and occ["high_surveillance"]:
            reasons.append("High surveillance workplace — excluded by safety constraint")

        # 5. Documentation requirements
        required_docs = set(occ["requires_docs"])
        available_doc_set = set(available_docs)
        missing_docs = required_docs - available_doc_set
        if missing_docs:
            reasons.append(f"Missing documentation: {', '.join(missing_docs)}")

        # 6. Wage threshold check
        # Estimate monthly income: hourly * 160 hours/month
        estimated_monthly = occ["median_wage_hourly"] * 160
        if estimated_monthly < profile.minimum_monthly_income:
            reasons.append(
                f"Wage below threshold: ${estimated_monthly:.0f}/month "
                f"< ${profile.minimum_monthly_income:.0f} required"
            )

        return (len(reasons) == 0), reasons

    def _training_is_viable(
        self, train_code: str, profile: ConstraintProfile, available_docs: List[str]
    ) -> tuple[bool, List[str]]:
        """Check if a training program is accessible given constraints."""
        if train_code not in self.training_programs:
            return False, ["Training program not found"]

        prog = self.training_programs[train_code]
        reasons = []

        # Documentation check for training enrollment
        required_docs = set(prog["requires_docs"])
        available_doc_set = set(available_docs)
        missing_docs = required_docs - available_doc_set
        if missing_docs:
            reasons.append(f"Missing docs for training enrollment: {', '.join(missing_docs)}")

        # Time horizon check — training + hire time must fit deadline
        if profile.income_deadline_weeks is not None:
            # Find the fastest job this training unlocks
            fastest_unlock = None
            for job_code in prog["unlocks"]:
                if job_code in self.occupations:
                    hire_weeks = self.occupations[job_code]["weeks_to_hire"]
                    total_weeks = prog["weeks_to_complete"] + hire_weeks
                    if fastest_unlock is None or total_weeks < fastest_unlock:
                        fastest_unlock = total_weeks

            if fastest_unlock and fastest_unlock > profile.income_deadline_weeks:
                reasons.append(
                    f"Training + hire ({fastest_unlock} weeks) "
                    f"exceeds income deadline ({profile.income_deadline_weeks} weeks)"
                )

        # Shift conflict for training sessions
        prog_shifts = set(prog.get("shift_types", []))
        excluded_shifts = set(profile.excluded_shift_types)
        # If all training shift options are excluded AND there's no online/remote option
        if prog_shifts and prog_shifts.issubset(excluded_shifts) and "online" not in prog_shifts:
            reasons.append(f"All training session types conflict with shift restrictions")

        return (len(reasons) == 0), reasons

    def _build_viable_subgraph(
        self, profile: ConstraintProfile
    ) -> tuple[nx.DiGraph, Dict[str, List[str]]]:
        """
        Returns a copy of the graph with all non-viable nodes removed.
        Also returns a dict of exclusion reasons for audit purposes.
        """
        available_docs = self._docs_available(profile)
        viable_graph = self.graph.copy()
        exclusion_log = {}

        for node, data in list(self.graph.nodes(data=True)):
            if node == "START":
                continue

            node_type = data.get("node_type")

            if node_type == "occupation":
                is_viable, reasons = self._occupation_is_viable(node, profile, available_docs)
                if not is_viable:
                    viable_graph.remove_node(node)
                    exclusion_log[node] = reasons

            elif node_type == "training":
                is_viable, reasons = self._training_is_viable(node, profile, available_docs)
                if not is_viable:
                    viable_graph.remove_node(node)
                    exclusion_log[node] = reasons

        return viable_graph, exclusion_log

    def _score_pathway(
        self, path: List[str], profile: ConstraintProfile
    ) -> Dict[str, Any]:
        """Score a path and build the PathwayResult."""
        safety_notes = []
        constraint_flags = []
        training_steps = 0
        weeks_to_income = 0
        final_occ_code = None

        for node in path:
            if node == "START":
                continue
            node_data = self.graph.nodes[node]
            ntype = node_data.get("node_type")

            if ntype == "training":
                training_steps += 1
                weeks_to_income += node_data["weeks_to_complete"]
                safety_notes.append(
                    f"Training: {node_data['title']} "
                    f"({node_data['weeks_to_complete']} weeks, "
                    f"provider: {node_data['provider']})"
                )

            elif ntype == "occupation":
                final_occ_code = node
                weeks_to_income += node_data["weeks_to_hire"]
                occ = self.occupations[node]

                # Safety fit notes
                if "remote" in occ["shift_types"]:
                    safety_notes.append("Remote work option available")
                if "part_time" in occ["shift_types"]:
                    safety_notes.append("Part-time start available — can scale up gradually")
                if not occ["isolated_workplace"]:
                    safety_notes.append("Not an isolated workplace")
                if not occ["high_surveillance"]:
                    safety_notes.append("Low surveillance environment")

                # Borderline flags for caseworker
                if "evening" in occ["shift_types"] and "evening" not in profile.excluded_shift_types:
                    constraint_flags.append(
                        "Evening shifts available — confirm survivor is comfortable with this"
                    )

        if final_occ_code is None:
            return None

        occ = self.occupations[final_occ_code]
        monthly_start = occ["min_wage_hourly"] * 160
        monthly_12m = occ["median_wage_hourly"] * 160

        meets_deadline = (
            profile.income_deadline_weeks is None or
            weeks_to_income <= profile.income_deadline_weeks
        )
        meets_threshold = monthly_start >= profile.minimum_monthly_income

        # Confidence based on data completeness
        confidence = "HIGH"
        if training_steps > 0:
            confidence = "MEDIUM"
        if not meets_deadline:
            confidence = "LOW"

        titles = []
        types = []
        for node in path:
            if node == "START":
                titles.append("Starting Point")
                types.append("start")
            elif node in self.training_programs:
                titles.append(self.training_programs[node]["title"])
                types.append("training")
            elif node in self.occupations:
                titles.append(self.occupations[node]["title"])
                types.append("occupation")

        why_viable = (
            f"This path respects all {len(profile.excluded_industries)} industry exclusions, "
            f"{len(profile.excluded_shift_types)} shift restrictions, and documentation requirements. "
            f"Estimated income: ${monthly_start:.0f}-${monthly_12m:.0f}/month."
        )

        return {
            "nodes": path,
            "node_titles": titles,
            "node_types": types,
            "weeks_to_first_income": weeks_to_income,
            "monthly_income_at_start": monthly_start,
            "monthly_income_at_12_months": monthly_12m,
            "training_steps_required": training_steps,
            "safety_fit_notes": safety_notes,
            "constraint_flags": constraint_flags,
            "confidence_level": confidence,
            "why_viable": why_viable,
            "meets_income_deadline": meets_deadline,
            "meets_income_threshold": meets_threshold
        }

    def find_pathways(
        self, profile: ConstraintProfile
    ) -> tuple[List[PathwayResult], ConstraintAuditResult, Dict]:
        """
        Main method — takes a constraint profile, returns viable pathways.

        Returns:
          - List of PathwayResult (up to 3, ranked)
          - ConstraintAuditResult (audit triggered if < 3 paths found)
          - Exclusion log (dict of excluded nodes and reasons — for transparency)
        """
        # 1. Build viable subgraph
        viable_graph, exclusion_log = self._build_viable_subgraph(profile)

        # 2. Find all paths from START to occupation nodes
        occupation_nodes = [
            n for n, d in viable_graph.nodes(data=True)
            if d.get("node_type") == "occupation" and "START" in viable_graph
        ]

        all_paths = []
        for target in occupation_nodes:
            try:
                paths = list(nx.all_simple_paths(viable_graph, "START", target, cutoff=4))
                all_paths.extend(paths)
            except (nx.NetworkXError, nx.NodeNotFound):
                continue

        # 3. Score and rank paths
        scored_paths = []
        for path in all_paths:
            score_data = self._score_pathway(path, profile)
            if score_data:
                # Primary sort: meets deadline + meets threshold
                # Secondary: fewer weeks to income
                # Tertiary: higher monthly income
                priority = (
                    int(score_data["meets_income_deadline"]) +
                    int(score_data["meets_income_threshold"]),
                    -score_data["weeks_to_first_income"],
                    score_data["monthly_income_at_12_months"]
                )
                scored_paths.append((priority, score_data))

        scored_paths.sort(key=lambda x: x[0], reverse=True)

        # 4. Deduplicate by final occupation node, take top 3
        seen_final_jobs = set()
        top_paths = []
        for _, data in scored_paths:
            final_node = data["nodes"][-1]
            if final_node not in seen_final_jobs:
                seen_final_jobs.add(final_node)
                top_paths.append(data)
            if len(top_paths) == 3:
                break

        # 5. Build PathwayResult objects
        results = []
        for i, data in enumerate(top_paths):
            results.append(PathwayResult(
                path_id=i + 1,
                **data
            ))

        # 6. Constraint audit
        audit_triggered = len(results) < self.AUDIT_THRESHOLD
        audit_flags = []
        suggestions = ""

        if audit_triggered:
            # Analyze exclusion log to identify over-broad constraints
            industry_exclusions = sum(
                1 for reasons in exclusion_log.values()
                for r in reasons if "Industry excluded" in r
            )
            doc_exclusions = sum(
                1 for reasons in exclusion_log.values()
                for r in reasons if "Missing documentation" in r
            )
            shift_exclusions = sum(
                1 for reasons in exclusion_log.values()
                for r in reasons if "shift type" in r.lower()
            )

            if industry_exclusions > 5:
                audit_flags.append(
                    f"{industry_exclusions} occupations excluded by industry. "
                    "Review: are specific employers excluded rather than entire industries?"
                )
            if doc_exclusions > 3:
                audit_flags.append(
                    f"{doc_exclusions} occupations excluded due to documentation gaps. "
                    "Review: are alternative documentation options available?"
                )
            if shift_exclusions > 3:
                audit_flags.append(
                    f"{shift_exclusions} occupations excluded by shift restrictions. "
                    "Review: are shift restrictions specific to unsafe times or overly broad?"
                )

            suggestions = (
                "Only " + str(len(results)) + " viable pathway(s) found. "
                "Please review each constraint for specificity before proceeding. "
                "Consider: are exclusions by employer (specific) or by industry (broad)?"
            )

        audit = ConstraintAuditResult(
            viable_path_count=len(results),
            audit_triggered=audit_triggered,
            flags=audit_flags,
            suggestion=suggestions
        )

        return results, audit, exclusion_log


# ─── QUICK TEST ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = ConstraintEngine()

    # Test profile — survivor with several real constraints
    profile = ConstraintProfile(
        case_id="CASE-TEST-001",
        excluded_industries=["Hospitality", "Personal_Services"],
        excluded_shift_types=["night"],
        exclude_isolated_workplaces=True,
        exclude_high_surveillance=True,
        has_government_id=True,
        has_ssn=False,
        has_work_authorization=False,
        existing_skills=["communication", "basic_computer", "food_service"],
        income_deadline_weeks=16,
        minimum_monthly_income=1500.0
    )

    results, audit, exclusion_log = engine.find_pathways(profile)

    print(f"\n{'='*60}")
    print(f"CONSTRAINT ENGINE TEST — Case: {profile.case_id}")
    print(f"{'='*60}")
    print(f"Viable pathways found: {len(results)}")
    print(f"Audit triggered: {audit.audit_triggered}")
    if audit.audit_triggered:
        print(f"Audit flags: {audit.flags}")

    for result in results:
        print(f"\n--- Pathway {result.path_id} ---")
        print(f"Route: {' -> '.join(result.node_titles)}")
        print(f"Weeks to first income: {result.weeks_to_first_income}")
        print(f"Monthly income at start: ${result.monthly_income_at_start:.0f}")
        print(f"Monthly income at 12m:  ${result.monthly_income_at_12_months:.0f}")
        print(f"Training steps: {result.training_steps_required}")
        print(f"Meets deadline: {result.meets_income_deadline}")
        print(f"Meets threshold: {result.meets_income_threshold}")
        print(f"Confidence: {result.confidence_level}")
        print(f"Safety notes: {result.safety_fit_notes[:2]}")

    print(f"\nExcluded {len(exclusion_log)} occupations/programs")
    print(f"{'='*60}\n")
