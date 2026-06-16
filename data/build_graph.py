"""
DATA LAYER — build_graph.py
Builds the occupational pathway graph from O*NET-style data.

In production: replace synthetic_occupations and synthetic_training
with real O*NET Web Services API calls and local training program data.
O*NET API (free): https://services.onetcenter.org/
"""

import json
import networkx as nx
import pandas as pd
from pathlib import Path

# ─── SYNTHETIC OCCUPATIONS ────────────────────────────────────────────────────
# Each occupation is a node in the graph.
# Fields mirror O*NET structure so you can swap in real API data later.

OCCUPATIONS = [
    {
        "code": "43-9061.00", "title": "Office Clerk",
        "industry": "Administrative",
        "shift_types": ["day", "part_time"],
        "requires_docs": ["ID"],
        "min_wage_hourly": 15.50, "median_wage_hourly": 18.00,
        "weeks_to_hire": 2,
        "skills_required": ["basic_computer", "communication"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": None
    },
    {
        "code": "43-6014.00", "title": "Medical Secretary",
        "industry": "Healthcare",
        "shift_types": ["day"],
        "requires_docs": ["ID", "SSN"],
        "min_wage_hourly": 17.00, "median_wage_hourly": 20.50,
        "weeks_to_hire": 4,
        "skills_required": ["basic_computer", "communication", "medical_terminology"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": "medical_admin_cert"
    },
    {
        "code": "31-1014.00", "title": "Nursing Assistant (CNA)",
        "industry": "Healthcare",
        "shift_types": ["day", "evening", "night"],
        "requires_docs": ["ID", "SSN", "work_auth"],
        "min_wage_hourly": 16.00, "median_wage_hourly": 19.00,
        "weeks_to_hire": 3,
        "skills_required": ["physical_stamina", "communication", "caregiving"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": "cna_cert"
    },
    {
        "code": "35-2014.00", "title": "Cook",
        "industry": "Food_Service",
        "shift_types": ["day", "evening", "night"],
        "requires_docs": ["ID"],
        "min_wage_hourly": 15.00, "median_wage_hourly": 17.50,
        "weeks_to_hire": 2,
        "skills_required": ["food_service", "physical_stamina"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": None
    },
    {
        "code": "35-3031.00", "title": "Waiter / Waitress",
        "industry": "Hospitality",
        "shift_types": ["day", "evening", "night"],
        "requires_docs": ["ID"],
        "min_wage_hourly": 12.00, "median_wage_hourly": 16.00,
        "weeks_to_hire": 1,
        "skills_required": ["communication", "food_service"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": None
    },
    {
        "code": "41-2011.00", "title": "Cashier",
        "industry": "Retail",
        "shift_types": ["day", "evening", "night"],
        "requires_docs": ["ID"],
        "min_wage_hourly": 15.00, "median_wage_hourly": 16.50,
        "weeks_to_hire": 1,
        "skills_required": ["basic_computer", "communication"],
        "isolated_workplace": False, "high_surveillance": True,
        "training_required": None
    },
    {
        "code": "43-3031.00", "title": "Bookkeeping Clerk",
        "industry": "Administrative",
        "shift_types": ["day"],
        "requires_docs": ["ID", "SSN"],
        "min_wage_hourly": 18.00, "median_wage_hourly": 22.00,
        "weeks_to_hire": 3,
        "skills_required": ["basic_computer", "math", "communication"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": "bookkeeping_cert"
    },
    {
        "code": "15-1232.00", "title": "Software QA Tester",
        "industry": "Technology",
        "shift_types": ["day", "remote"],
        "requires_docs": ["ID", "SSN"],
        "min_wage_hourly": 22.00, "median_wage_hourly": 30.00,
        "weeks_to_hire": 8,
        "skills_required": ["basic_computer", "analytical_thinking"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": "qa_bootcamp"
    },
    {
        "code": "39-9011.00", "title": "Childcare Worker",
        "industry": "Education",
        "shift_types": ["day", "part_time"],
        "requires_docs": ["ID", "background_check"],
        "min_wage_hourly": 14.50, "median_wage_hourly": 16.00,
        "weeks_to_hire": 3,
        "skills_required": ["caregiving", "communication", "patience"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": "childcare_cert"
    },
    {
        "code": "43-4051.00", "title": "Customer Service Rep",
        "industry": "Administrative",
        "shift_types": ["day", "evening", "remote"],
        "requires_docs": ["ID"],
        "min_wage_hourly": 16.00, "median_wage_hourly": 19.00,
        "weeks_to_hire": 2,
        "skills_required": ["communication", "basic_computer"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": None
    },
    {
        "code": "53-7062.00", "title": "Laundry / Dry-Cleaning Worker",
        "industry": "Personal_Services",
        "shift_types": ["day", "evening"],
        "requires_docs": ["ID"],
        "min_wage_hourly": 14.00, "median_wage_hourly": 15.50,
        "weeks_to_hire": 1,
        "skills_required": ["physical_stamina"],
        "isolated_workplace": True, "high_surveillance": False,
        "training_required": None
    },
    {
        "code": "31-9092.00", "title": "Medical Transcriptionist",
        "industry": "Healthcare",
        "shift_types": ["day", "remote"],
        "requires_docs": ["ID", "SSN"],
        "min_wage_hourly": 16.00, "median_wage_hourly": 20.00,
        "weeks_to_hire": 4,
        "skills_required": ["basic_computer", "medical_terminology", "typing"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": "medical_transcription_cert"
    },
    {
        "code": "39-5012.00", "title": "Hairdresser / Cosmetologist",
        "industry": "Personal_Services",
        "shift_types": ["day", "part_time"],
        "requires_docs": ["ID", "cosmetology_license"],
        "min_wage_hourly": 14.00, "median_wage_hourly": 18.00,
        "weeks_to_hire": 2,
        "skills_required": ["communication", "physical_dexterity"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": "cosmetology_license"
    },
    {
        "code": "43-9021.00", "title": "Data Entry Clerk",
        "industry": "Administrative",
        "shift_types": ["day", "remote", "part_time"],
        "requires_docs": ["ID"],
        "min_wage_hourly": 14.00, "median_wage_hourly": 17.00,
        "weeks_to_hire": 2,
        "skills_required": ["basic_computer", "typing", "attention_to_detail"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": None
    },
    {
        "code": "21-1093.00", "title": "Social Service Assistant",
        "industry": "Nonprofit",
        "shift_types": ["day"],
        "requires_docs": ["ID", "SSN"],
        "min_wage_hourly": 17.00, "median_wage_hourly": 20.00,
        "weeks_to_hire": 4,
        "skills_required": ["communication", "empathy", "basic_computer"],
        "isolated_workplace": False, "high_surveillance": False,
        "training_required": "human_services_cert"
    }
]

# ─── SYNTHETIC TRAINING PROGRAMS ─────────────────────────────────────────────
# Each training program unlocks jobs that require it.
# weeks_to_complete = how long before the survivor can start working.

TRAINING_PROGRAMS = [
    {
        "code": "cna_cert", "title": "Certified Nursing Assistant",
        "weeks_to_complete": 8,
        "cost_usd": 0,  # Many states offer free CNA training
        "requires_docs": ["ID", "SSN"],
        "shift_types": ["day", "evening"],
        "unlocks": ["31-1014.00"],
        "provider": "Community College / Red Cross"
    },
    {
        "code": "medical_admin_cert", "title": "Medical Administrative Assistant",
        "weeks_to_complete": 12,
        "cost_usd": 0,
        "requires_docs": ["ID"],
        "shift_types": ["day"],
        "unlocks": ["43-6014.00", "31-9092.00"],
        "provider": "Workforce Development Center"
    },
    {
        "code": "bookkeeping_cert", "title": "Bookkeeping Certificate",
        "weeks_to_complete": 10,
        "cost_usd": 0,
        "requires_docs": ["ID"],
        "shift_types": ["day", "online"],
        "unlocks": ["43-3031.00"],
        "provider": "Community College / Online"
    },
    {
        "code": "qa_bootcamp", "title": "Software QA Testing Bootcamp",
        "weeks_to_complete": 16,
        "cost_usd": 0,
        "requires_docs": ["ID"],
        "shift_types": ["day", "online"],
        "unlocks": ["15-1232.00"],
        "provider": "Workforce Development / Online Bootcamp"
    },
    {
        "code": "childcare_cert", "title": "Childcare Development Associate",
        "weeks_to_complete": 6,
        "cost_usd": 0,
        "requires_docs": ["ID", "background_check"],
        "shift_types": ["day"],
        "unlocks": ["39-9011.00"],
        "provider": "Local Childcare Network"
    },
    {
        "code": "medical_transcription_cert", "title": "Medical Transcription",
        "weeks_to_complete": 10,
        "cost_usd": 0,
        "requires_docs": ["ID"],
        "shift_types": ["online"],
        "unlocks": ["31-9092.00"],
        "provider": "Online / Community College"
    },
    {
        "code": "human_services_cert", "title": "Human Services Certificate",
        "weeks_to_complete": 16,
        "cost_usd": 0,
        "requires_docs": ["ID", "SSN"],
        "shift_types": ["day"],
        "unlocks": ["21-1093.00"],
        "provider": "Community College"
    },
    {
        "code": "cosmetology_license", "title": "Cosmetology License",
        "weeks_to_complete": 52,
        "cost_usd": 500,
        "requires_docs": ["ID", "SSN"],
        "shift_types": ["day"],
        "unlocks": ["39-5012.00"],
        "provider": "Cosmetology School"
    }
]


# ─── GRAPH BUILDER ────────────────────────────────────────────────────────────

def build_pathway_graph():
    """
    Builds a directed graph where:
      - Nodes are occupations and training programs
      - Edges connect training programs to the jobs they unlock
      - Edge weight = weeks_to_complete for training nodes
    """
    G = nx.DiGraph()

    # Add occupation nodes
    for occ in OCCUPATIONS:
        G.add_node(
            occ["code"],
            node_type="occupation",
            **occ
        )

    # Add training nodes + edges to jobs they unlock
    for prog in TRAINING_PROGRAMS:
        G.add_node(
            prog["code"],
            node_type="training",
            **prog
        )
        for job_code in prog["unlocks"]:
            G.add_edge(
                prog["code"],
                job_code,
                weight=prog["weeks_to_complete"],
                edge_type="training_to_job"
            )

    # Direct hire edges (jobs with no training required)
    for occ in OCCUPATIONS:
        if occ["training_required"] is None:
            G.add_edge(
                "START",
                occ["code"],
                weight=occ["weeks_to_hire"],
                edge_type="direct_hire"
            )
        else:
            G.add_edge(
                "START",
                occ["training_required"],
                weight=0,
                edge_type="start_to_training"
            )

    # Add START node
    G.add_node("START", node_type="start", title="Start Point")

    return G


def save_graph_data():
    """Save raw data to JSON for use by the constraint engine."""
    output_dir = Path(__file__).parent
    with open(output_dir / "occupations.json", "w") as f:
        json.dump(OCCUPATIONS, f, indent=2)
    with open(output_dir / "training_programs.json", "w") as f:
        json.dump(TRAINING_PROGRAMS, f, indent=2)
    print(f"Saved {len(OCCUPATIONS)} occupations and {len(TRAINING_PROGRAMS)} training programs")


if __name__ == "__main__":
    save_graph_data()
    G = build_pathway_graph()
    print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"Occupation nodes: {len([n for n,d in G.nodes(data=True) if d.get('node_type')=='occupation'])}")
    print(f"Training nodes:   {len([n for n,d in G.nodes(data=True) if d.get('node_type')=='training'])}")
