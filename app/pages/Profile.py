"""New survivor profile entry form."""

from __future__ import annotations

import base64
import os
import re
import sys
from datetime import date
from decimal import Decimal
from enum import Enum
from html import escape
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app import copy  # noqa: E402
from app.components import header  # noqa: E402
from core.anonymizer import profile_to_ticket  # noqa: E402
from db.repository import ProfileRepository  # noqa: E402
from models import (  # noqa: E402
    AvailableShifts,
    DocumentationBlockers,
    DocumentsHeld,
    EducationLevel,
    GradedConstraints,
    GradedLevel,
    Identity,
    Industry,
    Language,
    LegalProfile,
    Profile,
    RecordCategory,
    SafeContactMethod,
    TrainingAppetite,
    WorkAuthorization,
)

st.set_page_config(
    page_title=copy.PROFILE_PAGE_TITLE,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _inject_styles() -> None:
    css_path = Path(__file__).resolve().parent.parent / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def _section(title: str) -> None:
    st.markdown(
        f'<p class="pp-label" style="margin-top: 8px;">{escape(title)}</p>',
        unsafe_allow_html=True,
    )


def _section_end() -> None:
    st.markdown(
        '<div style="margin-bottom: 16px;"></div>',
        unsafe_allow_html=True,
    )


def _info_card(message: str) -> None:
    st.markdown(
        f'<div class="pp-card" style="margin-bottom: 16px;">'
        f'  <p class="pp-label">{escape(message)}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _aes_key() -> bytes | None:
    raw = os.environ.get("PATHWAY_AES_KEY", "")
    if not raw:
        return None
    return base64.b64decode(raw)


def _hmac_pepper() -> bytes | None:
    raw = os.environ.get("PATHWAY_HMAC_PEPPER", "")
    if not raw:
        return None
    return base64.b64decode(raw)


def _repo() -> ProfileRepository:
    db_path = os.environ.get("PATHWAY_DB_PATH", "./pathway.sqlite")
    return ProfileRepository(db_path, _aes_key())  # type: ignore[arg-type]


def _enum_selectbox(
    label: str,
    enum_cls: type[Enum],
    labels_map: dict[str, str],
    *,
    key: str,
    default: Enum | None = None,
) -> Enum:
    members = list(enum_cls)
    if default is not None and default in members:
        default_index = members.index(default)
    else:
        default_index = 0
    return st.selectbox(
        label,
        members,
        index=default_index,
        format_func=lambda m: labels_map[m.value],
        key=key,
    )


def _enum_multiselect(
    label: str,
    enum_cls: type[Enum],
    labels_map: dict[str, str],
    *,
    key: str,
) -> list[Enum]:
    members = list(enum_cls)
    return st.multiselect(
        label,
        members,
        format_func=lambda m: labels_map[m.value],
        key=key,
    )


def _parse_disabilities(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _parse_list(raw: str) -> list[str]:
    """Split free text on commas or newlines into a clean list of strings.

    Mirrors how existing_skills is parsed, so the "Other" industry fields
    behave the same way as the skills text area.
    """
    if not raw.strip():
        return []
    return [part.strip() for part in re.split(r"[\n,]", raw) if part.strip()]


def _render_footer() -> None:
    st.markdown(
        f'<p style="text-align: center; color: var(--slate-light); '
        f'font-size: 11px; margin-top: 40px;">{copy.ACCOUNTABILITY}</p>',
        unsafe_allow_html=True,
    )


def main() -> None:
    _inject_styles()
    header.render(None)

    # ── Edit-mode detection ───────────────────────────────────────────────────
    # Home.py sets `edit_profile_id` in session state when the caseworker
    # clicks Edit on a saved profile. We load the existing profile once,
    # stash it under `_edit_profile`, and use its fields as form defaults.
    # On a fresh new-profile visit neither key exists and we fall through to
    # the blank form.
    edit_profile_id: str | None = st.session_state.get("edit_profile_id")
    existing: Profile | None = st.session_state.get("_edit_profile")

    is_edit_mode = edit_profile_id is not None

    if _aes_key() is None or _hmac_pepper() is None:
        _info_card(copy.PROFILE_ENV_MISSING)
        _render_footer()
        st.stop()

    repo = _repo()

    # Load the profile being edited exactly once per edit session.
    if is_edit_mode and existing is None:
        try:
            existing = repo.get(edit_profile_id)
            st.session_state["_edit_profile"] = existing
        except KeyError:
            _info_card("Profile not found. It may have been deleted.")
            _render_footer()
            st.stop()

    # Page title differs between new and edit mode.
    page_title = copy.PROFILE_EDIT_TITLE if is_edit_mode else copy.PROFILE_PAGE_TITLE
    st.markdown(
        f'<div class="pp-header" style="margin-bottom: 24px;">'
        f'  <div class="pp-header-title">{page_title}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Language rows ─────────────────────────────────────────────────────────
    # Languages live outside the form so the "Add language" button can add a
    # row without submitting the whole form. In edit mode we seed the row
    # count and field values from the existing profile on the very first
    # render only (guard: `_lang_prefilled` flag in session state).
    if is_edit_mode and existing and not st.session_state.get("_lang_prefilled"):
        st.session_state["lang_row_count"] = max(len(existing.languages), 1)
        for i, lang in enumerate(existing.languages):
            st.session_state[f"lang_code_{i}"] = lang.code
            st.session_state[f"lang_fluency_{i}"] = lang.fluency_1_to_5
        st.session_state["_lang_prefilled"] = True

    if "lang_row_count" not in st.session_state:
        st.session_state["lang_row_count"] = 1

    # Languages live outside the form so the "Add language" button can add a
    # row without submitting the whole form (Streamlit disallows ordinary
    # buttons inside st.form). Keeping the button directly beneath the rows it
    # affects is the point of pulling this block out here.
    _section(copy.PROFILE_SECTION_LANGUAGES)
    languages: list[Language] = []
    for i in range(st.session_state["lang_row_count"]):
        st.markdown(
            f'<p class="pp-label">{copy.PROFILE_LANGUAGE_HEADING.format(n=i + 1)}</p>',
            unsafe_allow_html=True,
        )
        col_code, col_fluency = st.columns(2)
        with col_code:
            code = st.text_input(
                copy.PROFILE_FIELD_LABELS["language_code"],
                key=f"lang_code_{i}",
            )
        with col_fluency:
            fluency = st.slider(
                copy.PROFILE_FIELD_LABELS["fluency_1_to_5"],
                min_value=1,
                max_value=5,
                value=3,
                key=f"lang_fluency_{i}",
            )
        if code.strip():
            languages.append(Language(code=code.strip(), fluency_1_to_5=fluency))

    if st.button(copy.PROFILE_ADD_LANGUAGE):
        st.session_state["lang_row_count"] += 1
        st.rerun()
    _section_end()

    with st.form("new_profile", clear_on_submit=False):
        # Shorthand so every field can write: default=_v("field") or _v("field", fallback)
        def _v(attr: str, fallback=None):
            """Return existing profile value in edit mode, else fallback."""
            if existing is None:
                return fallback
            parts = attr.split(".")
            obj = existing
            for p in parts:
                obj = getattr(obj, p, None)
                if obj is None:
                    return fallback
            return obj if obj is not None else fallback

        # 1. Identity
        _section(copy.PROFILE_SECTION_IDENTITY)
        legal_name = st.text_input(
            copy.PROFILE_FIELD_LABELS["legal_name"],
            value=_v("identity.legal_name", ""),
        )
        preferred_name = st.text_input(
            copy.PROFILE_FIELD_LABELS["preferred_name"],
            value=_v("identity.preferred_name", ""),
        )
        pronouns = st.text_input(
            copy.PROFILE_FIELD_LABELS["pronouns"],
            value=_v("identity.pronouns", ""),
        )
        dob = st.date_input(
            copy.PROFILE_FIELD_LABELS["dob"],
            value=_v("identity.dob", date(1990, 1, 1)),
            min_value=date(1940, 1, 1),
            max_value=date.today(),
        )
        safe_phone = st.text_input(
            copy.PROFILE_FIELD_LABELS["safe_phone"],
            value=_v("identity.safe_phone", ""),
        )
        safe_contact_method = _enum_selectbox(
            copy.PROFILE_FIELD_LABELS["safe_contact_method"],
            SafeContactMethod,
            copy.PROFILE_CONTACT_METHOD_LABELS,
            key="safe_contact_method",
            default=_v("identity.safe_contact_method", SafeContactMethod.CASEWORKER_ONLY),
        )
        caseworker_notes = st.text_area(
            copy.PROFILE_FIELD_LABELS["caseworker_notes"],
            value=_v("identity.caseworker_notes", ""),
        )
        _section_end()

        # 2. Demographics
        _section(copy.PROFILE_SECTION_DEMOGRAPHICS)
        current_metro = st.text_input(
            copy.PROFILE_FIELD_LABELS["current_metro"],
            value=_v("current_metro", ""),
        )
        education_highest = _enum_selectbox(
            copy.PROFILE_FIELD_LABELS["education_highest"],
            EducationLevel,
            copy.PROFILE_EDUCATION_LABELS,
            key="education_highest",
            default=_v("education_highest", EducationLevel.NONE),
        )
        disabilities_raw = st.text_input(
            copy.PROFILE_FIELD_LABELS["disabilities"],
            value=", ".join(_v("disabilities", [])),
        )
        dependents = st.number_input(
            copy.PROFILE_FIELD_LABELS["dependents"],
            min_value=0,
            max_value=10,
            value=_v("dependents", 0),
        )
        _section_end()

        # 3. Constraints
        _section(copy.PROFILE_SECTION_CONSTRAINTS)
        work_authorization = _enum_selectbox(
            copy.PROFILE_FIELD_LABELS["work_authorization"],
            WorkAuthorization,
            copy.PROFILE_WORK_AUTH_LABELS,
            key="work_authorization",
            default=_v("work_authorization", WorkAuthorization.NO),
        )
        col_vehicle, col_license, col_transit = st.columns(3)
        with col_vehicle:
            has_vehicle = st.checkbox(
                copy.PROFILE_FIELD_LABELS["has_vehicle"],
                value=_v("has_vehicle", False),
            )
        with col_license:
            has_valid_license = st.checkbox(
                copy.PROFILE_FIELD_LABELS["has_valid_license"],
                value=_v("has_valid_license", False),
            )
        with col_transit:
            transit_access = st.checkbox(
                copy.PROFILE_FIELD_LABELS["transit_access"],
                value=_v("transit_access", False),
            )

        max_commute_minutes = st.number_input(
            copy.PROFILE_FIELD_LABELS["max_commute_minutes"],
            min_value=1,
            value=_v("max_commute_minutes", 30),
        )
        wage_minimum_hourly = st.number_input(
            copy.PROFILE_FIELD_LABELS["wage_minimum_hourly"],
            min_value=0.01,
            step=0.01,
            format="%.2f",
            value=float(_v("wage_minimum_hourly", Decimal("15.00"))),
        )
        col_morning, col_afternoon, col_evening = st.columns(3)
        with col_morning:
            shift_morning = st.checkbox(
                copy.PROFILE_FIELD_LABELS["shift_morning"],
                value=_v("available_shifts.morning", True),
            )
        with col_afternoon:
            shift_afternoon = st.checkbox(
                copy.PROFILE_FIELD_LABELS["shift_afternoon"],
                value=_v("available_shifts.afternoon", True),
            )
        with col_evening:
            shift_evening = st.checkbox(
                copy.PROFILE_FIELD_LABELS["shift_evening"],
                value=_v("available_shifts.evening", False),
            )

        exclusion_industries = _enum_multiselect(
            copy.PROFILE_EXCLUSION_INDUSTRIES_LABEL,
            Industry,
            copy.PROFILE_INDUSTRY_LABELS,
            key="exclusion_industries",
        )
        exclusion_industries_other_raw = st.text_input(
            copy.PROFILE_EXCLUSION_INDUSTRIES_OTHER_LABEL,
            key="exclusion_industries_other",
        )
        _section_end()

        # 4. Graded constraints
        _section(copy.PROFILE_SECTION_GRADED)
        graded_fields = [
            "night_shift",
            "isolated_workplace",
            "customer_facing",
            "male_dominated_team",
            "uniformed_role",
            "requires_overnight_travel",
        ]
        graded_values: dict[str, GradedLevel] = {}
        for field in graded_fields:
            graded_values[field] = _enum_selectbox(
                copy.PROFILE_FIELD_LABELS[field],
                GradedLevel,
                copy.PROFILE_GRADED_LABELS,
                key=f"graded_{field}",
                default=_v(f"graded_constraints.{field}", GradedLevel.OK),
            )
        _section_end()

        # 5. Documentation
        _section(copy.PROFILE_SECTION_DOCUMENTATION)
        st.markdown(
            f'<p class="pp-label">{copy.PROFILE_DOCUMENTATION_BLOCKERS_HEADING}</p>',
            unsafe_allow_html=True,
        )
        requires_clean_record = st.checkbox(
            copy.PROFILE_FIELD_LABELS["requires_clean_record"],
            value=_v("documentation_blockers.requires_clean_record", False),
        )
        requires_drivers_license = st.checkbox(
            copy.PROFILE_FIELD_LABELS["requires_drivers_license"],
            value=_v("documentation_blockers.requires_drivers_license", False),
        )
        requires_ssn = st.checkbox(
            copy.PROFILE_FIELD_LABELS["requires_ssn"],
            value=_v("documentation_blockers.requires_ssn", False),
        )
        requires_credit_check = st.checkbox(
            copy.PROFILE_FIELD_LABELS["requires_credit_check"],
            value=_v("documentation_blockers.requires_credit_check", False),
        )

        st.markdown(
            f'<p class="pp-label">{copy.PROFILE_DOCUMENTS_HELD_HEADING}</p>',
            unsafe_allow_html=True,
        )
        col_id, col_dl, col_ssn = st.columns(3)
        with col_id:
            state_id = st.checkbox(
                copy.PROFILE_FIELD_LABELS["state_id"],
                value=_v("documents_held.state_id", False),
            )
        with col_dl:
            drivers_license = st.checkbox(
                copy.PROFILE_FIELD_LABELS["drivers_license"],
                value=_v("documents_held.drivers_license", False),
            )
        with col_ssn:
            ssn = st.checkbox(
                copy.PROFILE_FIELD_LABELS["ssn"],
                value=_v("documents_held.ssn", False),
            )
        col_wad, col_passport = st.columns(2)
        with col_wad:
            work_authorization_doc = st.checkbox(
                copy.PROFILE_FIELD_LABELS["work_authorization_doc"],
                value=_v("documents_held.work_authorization_doc", False),
            )
        with col_passport:
            passport = st.checkbox(
                copy.PROFILE_FIELD_LABELS["passport"],
                value=_v("documents_held.passport", False),
            )
        _section_end()

        # 6. Legal
        _section(copy.PROFILE_SECTION_LEGAL)
        record_categories = _enum_multiselect(
            copy.PROFILE_FIELD_LABELS["record_categories"],
            RecordCategory,
            copy.PROFILE_RECORD_LABELS,
            key="record_categories",
        )
        expungement_eligible = _enum_multiselect(
            copy.PROFILE_FIELD_LABELS["expungement_eligible"],
            RecordCategory,
            copy.PROFILE_RECORD_LABELS,
            key="expungement_eligible",
        )
        jurisdiction = st.text_input(
            copy.PROFILE_FIELD_LABELS["jurisdiction"],
            value=_v("legal_profile.jurisdiction", ""),
        )
        _section_end()

        # 7. Skills — free-text entry
        _section(copy.PROFILE_SECTION_SKILLS)
        skills_text = st.text_area(
            copy.PROFILE_SKILLS_TEXT_LABEL,
            value=", ".join(_v("existing_skills", [])),
            height=120,
            key="skills_text",
        )
        _section_end()

        # 8. Goals
        _section(copy.PROFILE_SECTION_GOALS)
        industries_of_interest = _enum_multiselect(
            copy.PROFILE_FIELD_LABELS["industries_of_interest"],
            Industry,
            copy.PROFILE_INDUSTRY_LABELS,
            key="industries_of_interest",
        )
        industries_of_interest_other_raw = st.text_input(
            copy.PROFILE_INDUSTRIES_INTEREST_OTHER_LABEL,
            key="industries_of_interest_other",
        )
        training_appetite = _enum_selectbox(
            copy.PROFILE_FIELD_LABELS["training_appetite"],
            TrainingAppetite,
            copy.PROFILE_TRAINING_LABELS,
            key="training_appetite",
            default=_v("training_appetite", TrainingAppetite.MODERATE),
        )
        long_term_goal = st.text_area(
            copy.PROFILE_FIELD_LABELS["long_term_goal"],
            value=_v("long_term_goal", ""),
        )
        _section_end()

        submit_label = copy.PROFILE_SAVE_CHANGES if is_edit_mode else copy.PROFILE_SUBMIT
        submitted = st.form_submit_button(submit_label, type="primary")

    if submitted:
        # Parse free-text skills into a list of strings
        existing_skills = [
            s.strip()
            for s in re.split(r"[\n,]", skills_text)
            if s.strip()
        ]
        try:
            # Carry forward saved_candidate_codes in edit mode so an edit
            # doesn't silently wipe the caseworker's saved shortlist.
            saved_codes = existing.saved_candidate_codes if existing else []

            profile = Profile(
                identity=Identity(
                    legal_name=legal_name,
                    preferred_name=preferred_name,
                    pronouns=pronouns,
                    dob=dob,
                    safe_phone=safe_phone,
                    safe_contact_method=safe_contact_method,
                    caseworker_notes=caseworker_notes,
                ),
                languages=languages,
                current_metro=current_metro,
                work_authorization=work_authorization,
                has_vehicle=has_vehicle,
                has_valid_license=has_valid_license,
                transit_access=transit_access,
                education_highest=education_highest,
                disabilities=_parse_disabilities(disabilities_raw),
                dependents=dependents,
                skills=[],
                existing_skills=existing_skills,
                exclusion_zones=[],
                exclusion_industries=exclusion_industries,
                exclusion_industries_other=_parse_list(exclusion_industries_other_raw),
                exclusion_employers=[],
                documentation_blockers=DocumentationBlockers(
                    requires_clean_record=requires_clean_record,
                    requires_drivers_license=requires_drivers_license,
                    requires_ssn=requires_ssn,
                    requires_credit_check=requires_credit_check,
                ),
                graded_constraints=GradedConstraints(**graded_values),
                max_commute_minutes=max_commute_minutes,
                available_shifts=AvailableShifts(
                    morning=shift_morning,
                    afternoon=shift_afternoon,
                    evening=shift_evening,
                ),
                legal_profile=LegalProfile(
                    record_categories=record_categories,
                    expungement_eligible=expungement_eligible,
                    jurisdiction=jurisdiction,
                ),
                documents_held=DocumentsHeld(
                    state_id=state_id,
                    drivers_license=drivers_license,
                    ssn=ssn,
                    work_authorization_doc=work_authorization_doc,
                    passport=passport,
                ),
                industries_of_interest=industries_of_interest,
                industries_of_interest_other=_parse_list(industries_of_interest_other_raw),
                wage_minimum_hourly=Decimal(str(wage_minimum_hourly)),
                training_appetite=training_appetite,
                long_term_goal=long_term_goal,
                saved_candidate_codes=saved_codes,
            )
        except ValidationError:
            _info_card(copy.PROFILE_VALIDATION_ERROR)
        else:
            pepper = _hmac_pepper()
            assert pepper is not None

            if is_edit_mode and edit_profile_id:
                # Edit path — update in place, clear stale results.
                repo.update(edit_profile_id, profile)
                profile_id = edit_profile_id
                # Clean up edit-mode session keys.
                for key in ("edit_profile_id", "_edit_profile", "_lang_prefilled"):
                    st.session_state.pop(key, None)
            else:
                # New profile path.
                profile_id = repo.save(profile)

            ticket = profile_to_ticket(profile, pepper)
            st.session_state["active_profile_id"] = profile_id
            st.session_state["active_ticket"] = ticket
            st.session_state["active_name"] = (
                profile.identity.preferred_name or profile.identity.legal_name
            )
            st.session_state["is_sample_profile"] = False
            # Clear stale pipeline result so the next render re-runs the
            # pipeline with the updated ticket — not the old cached result.
            st.session_state.pop("pipeline_result", None)
            st.session_state.pop("pipeline_result_ticket_id", None)
            st.switch_page("Home.py")

    _render_footer()


if __name__ == "__main__":
    main()
