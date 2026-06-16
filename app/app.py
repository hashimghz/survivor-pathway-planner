"""
STREAMLIT APP — app.py
Caseworker-facing constraint profile intake + pathway comparison interface.

Run with: streamlit run app/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from engine.constraint_engine import ConstraintEngine, ConstraintProfile

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Survivor Career Pathway Planner",
    page_icon="🛤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── STYLING ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1B2A4A 0%, #2E75B6 100%);
        color: white; padding: 24px 32px; border-radius: 8px;
        margin-bottom: 24px;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #BBCCDD; margin: 6px 0 0; font-size: 0.95rem; }
    .pathway-card {
        border: 2px solid #2E75B6; border-radius: 8px;
        padding: 20px; margin-bottom: 16px;
        background: #F8FAFC;
    }
    .pathway-card-title {
        font-size: 1.1rem; font-weight: bold;
        color: #1B2A4A; margin-bottom: 12px;
    }
    .metric-row { display: flex; gap: 16px; margin: 12px 0; }
    .metric-box {
        background: white; border: 1px solid #DDDDDD;
        border-radius: 6px; padding: 12px 16px; flex: 1; text-align: center;
    }
    .metric-box .label { font-size: 0.75rem; color: #888; text-transform: uppercase; }
    .metric-box .value { font-size: 1.3rem; font-weight: bold; color: #1B2A4A; }
    .audit-box {
        background: #FEF9E7; border: 2px solid #F39C12;
        border-radius: 8px; padding: 16px; margin-bottom: 20px;
    }
    .safety-note {
        background: #D5F5E3; border-left: 4px solid #1E8449;
        padding: 8px 12px; border-radius: 4px; margin: 4px 0;
        font-size: 0.9rem;
    }
    .flag-note {
        background: #FEF9E7; border-left: 4px solid #F39C12;
        padding: 8px 12px; border-radius: 4px; margin: 4px 0;
        font-size: 0.9rem;
    }
    .no-results {
        background: #FDEDEC; border: 2px solid #C0392B;
        border-radius: 8px; padding: 20px; text-align: center;
    }
    .section-header {
        color: #1B2A4A; font-size: 1.1rem; font-weight: bold;
        border-bottom: 2px solid #2E75B6; padding-bottom: 6px;
        margin: 16px 0 12px;
    }
    .confidence-HIGH { color: #1E8449; font-weight: bold; }
    .confidence-MEDIUM { color: #B7770D; font-weight: bold; }
    .confidence-LOW { color: #C0392B; font-weight: bold; }
    .non-goal-box {
        background: #F5F6FA; border-left: 4px solid #2E75B6;
        padding: 12px 16px; border-radius: 4px; margin: 12px 0;
        font-size: 0.85rem; color: #444;
    }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🛤️ Survivor Career Pathway Planner</h1>
    <p>Constraint-aware career pathway decision support for caseworkers &nbsp;|&nbsp;
    Brief 5 Direction B &nbsp;|&nbsp; Graduate Track &nbsp;|&nbsp;
    AI surfaces options — caseworker decides</p>
</div>
""", unsafe_allow_html=True)

# ─── NON-GOALS NOTICE ────────────────────────────────────────────────────────
with st.expander("ℹ️ What this system does NOT do (click to read)", expanded=False):
    st.markdown("""
    <div class="non-goal-box">
    This tool <strong>does not</strong> select or recommend a single 'best' pathway.<br>
    This tool <strong>does not</strong> communicate pathway options to survivors directly.<br>
    This tool <strong>does not</strong> make legal or immigration determinations.<br>
    This tool <strong>does not</strong> replace trauma-informed clinical judgment.<br>
    This tool <strong>does not</strong> store sensitive survivor data beyond this session.<br>
    <br>
    <strong>All pathway recommendations are made by the caseworker in discussion with the survivor.</strong>
    </div>
    """, unsafe_allow_html=True)

# ─── ENGINE ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    return ConstraintEngine()

engine = get_engine()

# ─── SIDEBAR — CONSTRAINT PROFILE INTAKE ─────────────────────────────────────
with st.sidebar:
    st.markdown("## 📋 Constraint Profile Intake")
    st.caption("Complete this form for each client. All fields are filters applied simultaneously.")

    st.markdown("---")
    case_id = st.text_input("Case ID (anonymized)", value="CASE-001",
        help="For audit logging only — no personally identifiable information")

    st.markdown("### 🚫 Industry Exclusions")
    st.caption("Select industries the survivor cannot safely enter")
    INDUSTRIES = ["Hospitality", "Retail", "Food_Service", "Personal_Services",
                  "Healthcare", "Administrative", "Technology", "Education",
                  "Nonprofit", "Transportation"]
    excluded_industries = st.multiselect(
        "Excluded industries", INDUSTRIES,
        help="Select entire industries to exclude. If only specific employers are unsafe, "
             "leave the industry and use 'Specific job codes excluded' below."
    )

    st.markdown("### ⏰ Shift Restrictions")
    excluded_shifts = st.multiselect(
        "Excluded shift types",
        ["night", "evening", "day", "part_time", "remote"],
        help="Select shift types that are unsafe or unavailable for this survivor"
    )

    st.markdown("### 🏢 Workplace Environment")
    exclude_isolated = st.checkbox("Exclude isolated workplaces",
        help="Workplaces where the survivor would be alone or in low-contact settings")
    exclude_surveillance = st.checkbox("Exclude high-surveillance workplaces",
        help="Workplaces with extensive camera monitoring or tracking systems")

    st.markdown("### 📄 Documentation Available")
    has_id = st.checkbox("Government-issued ID", value=True)
    has_ssn = st.checkbox("Social Security Number")
    has_work_auth = st.checkbox("Work authorization")
    has_bg_check = st.checkbox("Background check clearance")
    has_cosmo = st.checkbox("Cosmetology license")

    st.markdown("### 🛠️ Existing Skills")
    ALL_SKILLS = ["basic_computer", "communication", "food_service", "caregiving",
                  "physical_stamina", "math", "typing", "medical_terminology",
                  "attention_to_detail", "physical_dexterity", "analytical_thinking",
                  "empathy", "patience", "bilingual"]
    existing_skills = st.multiselect("Survivor's existing skills", ALL_SKILLS)

    st.markdown("### ⏱️ Time & Income")
    has_deadline = st.checkbox("Income deadline applies")
    income_deadline = None
    if has_deadline:
        income_deadline = st.slider(
            "Weeks until income needed", min_value=4, max_value=52, value=16
        )
        st.caption(f"Income needed within {income_deadline} weeks")

    min_income = st.number_input(
        "Minimum monthly income needed ($)",
        min_value=500, max_value=5000, value=1500, step=100,
        help="Minimum income for housing or visa stability"
    )

    st.markdown("---")
    run_search = st.button("🔍 Find Viable Pathways", type="primary", use_container_width=True)

# ─── MAIN PANEL ──────────────────────────────────────────────────────────────
if not run_search:
    st.markdown("""
    ### Getting started
    Complete the **Constraint Profile** in the left panel, then click
    **Find Viable Pathways** to see constraint-safe career options for this client.

    The system will:
    - Apply all constraints **simultaneously** across the occupational graph
    - Return only pathways that are viable given this client's full constraint set
    - Explain the top 3 options with time-to-income, wage estimates, and safety notes
    - Flag if the constraint profile produces fewer than 3 options for your review
    """)

    # Show example constraint profile
    with st.expander("📖 Example: How constraints interact", expanded=True):
        st.markdown("""
        A survivor with retail experience might seem like a natural fit for retail jobs.
        But if her constraint profile includes:
        - **Night shifts excluded** (trauma-related)
        - **High-surveillance workplaces excluded** (safety concern)

        Then the typical retail cashier role is eliminated — even though the skill match is
        perfect — because cashier roles often involve night shifts and camera monitoring.

        This system applies all constraints simultaneously and only surfaces options
        where **every constraint is satisfied**. A caseworker reasoning manually might
        miss this conflict under time pressure. This tool doesn't.
        """)
    st.stop()

# ─── BUILD PROFILE AND RUN ───────────────────────────────────────────────────
profile = ConstraintProfile(
    case_id=case_id,
    excluded_industries=excluded_industries,
    excluded_shift_types=excluded_shifts,
    exclude_isolated_workplaces=exclude_isolated,
    exclude_high_surveillance=exclude_surveillance,
    has_government_id=has_id,
    has_ssn=has_ssn,
    has_work_authorization=has_work_auth,
    has_background_check_clearance=has_bg_check,
    has_cosmetology_license=has_cosmo,
    existing_skills=existing_skills,
    income_deadline_weeks=income_deadline,
    minimum_monthly_income=float(min_income)
)

with st.spinner("Applying constraints across occupational graph..."):
    results, audit, exclusion_log = engine.find_pathways(profile)

# ─── CONSTRAINT AUDIT ALERT ──────────────────────────────────────────────────
if audit.audit_triggered:
    st.markdown(f"""
    <div class="audit-box">
    <strong>⚠️ Constraint Audit Triggered</strong><br>
    Only <strong>{audit.viable_path_count}</strong> viable pathway(s) found.
    Review constraint specificity before presenting options to the survivor.<br><br>
    <em>{audit.suggestion}</em>
    </div>
    """, unsafe_allow_html=True)

    if audit.flags:
        st.markdown("**Specific flags to review:**")
        for flag in audit.flags:
            st.markdown(f"""
            <div class="flag-note">⚠️ {flag}</div>
            """, unsafe_allow_html=True)

# ─── RESULTS SUMMARY ─────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Viable Pathways Found", len(results))
with col2:
    st.metric("Occupations/Programs Excluded", len(exclusion_log))
with col3:
    deadline_str = f"{income_deadline} weeks" if income_deadline else "No deadline"
    st.metric("Income Deadline", deadline_str)
with col4:
    st.metric("Income Threshold", f"${min_income:,}/month")

st.markdown("---")

# ─── NO RESULTS ──────────────────────────────────────────────────────────────
if not results:
    st.markdown("""
    <div class="no-results">
    <h3>No viable pathways found</h3>
    <p>The current constraint profile eliminates all occupations in the graph.
    Please review each constraint for specificity — particularly industry exclusions
    and documentation requirements — and discuss with a supervisor before proceeding.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── PATHWAY COMPARISON ──────────────────────────────────────────────────────
st.markdown("## 🗺️ Viable Pathway Comparison")
st.caption(
    "All pathways below satisfy every constraint simultaneously. "
    "Review with the survivor and select the path that best fits their goals and readiness."
)

CONF_COLORS = {"HIGH": "#1E8449", "MEDIUM": "#B7770D", "LOW": "#C0392B"}
CONF_ICONS = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "🔴"}

tabs = st.tabs([
    f"Pathway {r.path_id} — {r.node_titles[-1]}"
    for r in results
])

for tab, result in zip(tabs, results):
    with tab:
        col_left, col_right = st.columns([3, 2])

        with col_left:
            # Route visualization
            st.markdown(f"**Route:** {' → '.join(result.node_titles)}")
            st.markdown("---")

            # Key metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Weeks to Income", result.weeks_to_first_income)
            m2.metric("Income at Start", f"${result.monthly_income_at_start:,.0f}/mo")
            m3.metric("Income at 12mo", f"${result.monthly_income_at_12_months:,.0f}/mo")
            m4.metric("Training Steps", result.training_steps_required)

            # Deadline and threshold checks
            d1, d2 = st.columns(2)
            with d1:
                if result.meets_income_deadline:
                    st.success("✅ Meets income deadline")
                else:
                    st.error("❌ Does not meet income deadline")
            with d2:
                if result.meets_income_threshold:
                    st.success("✅ Meets income threshold")
                else:
                    st.error("❌ Below income threshold")

            # Confidence
            conf_color = CONF_COLORS[result.confidence_level]
            conf_icon = CONF_ICONS[result.confidence_level]
            st.markdown(
                f"**Confidence:** "
                f"<span style='color:{conf_color}'>{conf_icon} {result.confidence_level}</span>",
                unsafe_allow_html=True
            )

            # Why viable
            st.markdown(f"**Why viable:** {result.why_viable}")

        with col_right:
            # Safety notes
            st.markdown("**Safety fit notes:**")
            for note in result.safety_fit_notes:
                st.markdown(
                    f'<div class="safety-note">✓ {note}</div>',
                    unsafe_allow_html=True
                )

            # Flags for caseworker
            if result.constraint_flags:
                st.markdown("**Caseworker review flags:**")
                for flag in result.constraint_flags:
                    st.markdown(
                        f'<div class="flag-note">⚠️ {flag}</div>',
                        unsafe_allow_html=True
                    )

        # Income trajectory chart
        st.markdown("---")
        fig = go.Figure()
        months = [0, 1, 3, 6, 12]
        incomes = [
            0,
            result.monthly_income_at_start * 0.5,
            result.monthly_income_at_start,
            (result.monthly_income_at_start + result.monthly_income_at_12_months) / 2,
            result.monthly_income_at_12_months
        ]
        fig.add_trace(go.Scatter(
            x=months, y=incomes, mode="lines+markers",
            line=dict(color="#2E75B6", width=3),
            marker=dict(size=8),
            name="Estimated income"
        ))
        fig.add_hline(
            y=min_income, line_dash="dash", line_color="#C0392B",
            annotation_text=f"Income threshold: ${min_income:,}/mo"
        )
        if income_deadline:
            deadline_month = income_deadline / 4.33
            fig.add_vline(
                x=deadline_month, line_dash="dash", line_color="#F39C12",
                annotation_text=f"Deadline: week {income_deadline}"
            )
        fig.update_layout(
            title="Estimated Income Trajectory",
            xaxis_title="Months",
            yaxis_title="Monthly Income ($)",
            height=280,
            margin=dict(t=40, b=40, l=40, r=40),
            plot_bgcolor="white",
            paper_bgcolor="white"
        )
        st.plotly_chart(fig, use_container_width=True)

# ─── EXCLUSION LOG ───────────────────────────────────────────────────────────
with st.expander(f"🔍 Transparency — {len(exclusion_log)} exclusions applied (click to review)", expanded=False):
    st.caption(
        "This log shows every occupation and training program removed by the constraint "
        "profile, and why. Review this if the audit was triggered."
    )
    for code, reasons in exclusion_log.items():
        with st.container():
            col_a, col_b = st.columns([1, 3])
            with col_a:
                st.markdown(f"**{code}**")
            with col_b:
                for r in reasons:
                    st.markdown(f"- {r}")

# ─── HUMAN DECISION SECTION ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 👤 Caseworker Decision")
st.markdown(
    "The pathways above are for discussion with the survivor. "
    "Select the chosen pathway below to document the decision."
)

pathway_options = ["— Select after discussion with survivor —"] + [
    f"Pathway {r.path_id}: {' → '.join(r.node_titles)}" for r in results
]
chosen = st.selectbox("Chosen pathway", pathway_options)
caseworker_notes = st.text_area(
    "Caseworker notes (reasoning, survivor preference, any undisclosed constraints)",
    height=100,
    placeholder="Document the rationale for this pathway selection..."
)

col_a, col_b = st.columns(2)
with col_a:
    supervisor_review = st.checkbox(
        "Flag for supervisor co-review",
        help="Required for cases with legal proceedings, immigration proceedings, or active safety planning"
    )
with col_b:
    if st.button("📋 Save Decision to Case File", type="secondary"):
        if chosen == pathway_options[0]:
            st.warning("Please select a pathway before saving.")
        else:
            st.success(f"Decision saved: {chosen}")
            if supervisor_review:
                st.info("🔔 Supervisor co-review flagged — case will appear in supervisor queue.")

st.markdown("---")
st.caption(
    "Constraint-Aware Survivor Career Pathway Planner · Brief 5 Direction B · "
    "Graduate Track · USAII Global AI Hackathon 2026 · "
    "All pathway decisions are made by trained caseworkers, not by this system."
)
