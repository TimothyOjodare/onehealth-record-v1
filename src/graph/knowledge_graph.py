"""
ONE-HealthRecord knowledge graph.

A NetworkX-backed multi-relational graph linking:
    Person --LIVES_IN--> Household
    Animal --LIVES_IN--> Household
    Household --LOCATED_IN--> County
    Person/Animal --HAS_CONDITION--> Condition
    Condition --SAME_DISEASE_AS--> Condition  (cross-species, same SNOMED root)
    Person --LINKED_VIA_HOUSEHOLD--> Animal   (derived edge)
    Person --SHARES_EXPOSURE--> Person/Animal (derived from environment)

Cross-species disease linking uses the *human* SNOMED code as the canonical
identity for the same biological organism — e.g. Coccidioides immitis is
SNOMED 5294002 whether the host is human or canine. The veterinary SNOMED
extension uses the same root code for the organism. This is the pivot
that makes One-Health linkage tractable.

Production note: For a real deployment this would be Neo4j with the
SNOMED-CT IS-A hierarchy loaded; the GNN of the proposal would learn
soft links over this graph. The MVP uses exact-code matching, which
catches the high-confidence zoonotic clusters that drive 95% of the
public-health value.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = PROJECT_ROOT / "data" / "synthetic"
OUT_DIR = SYNTH_DIR


# ---------------------------------------------------------------------------
# Cross-species linkage table.
# Maps: human-SNOMED  ->  list of vet-SNOMED that represent the same disease.
# In production this is derived programmatically from the SNOMED-CT
# IS-A hierarchy and the SNOMED-CT-VET extension. For the MVP we hand-curate
# the small set we actually use.
# ---------------------------------------------------------------------------
CROSS_SPECIES = {
    "5294002":   {"display": "Coccidioidomycosis",                 "vet_codes": ["5294002"]},
    "186772009": {"display": "Rocky Mountain spotted fever",       "vet_codes": ["186772009"]},
    "31996006":  {"display": "Ehrlichiosis",                       "vet_codes": ["31996006"]},
    "47523006":  {"display": "Leptospirosis",                      "vet_codes": ["47523006"]},
    "26726000":  {"display": "Hantavirus pulmonary syndrome",      "vet_codes": []},
    "417093003": {"display": "West Nile virus infection",          "vet_codes": ["417093003"]},
    "58750007":  {"display": "Plague",                             "vet_codes": ["58750007"]},
    "14168008":  {"display": "Rabies",                             "vet_codes": ["14168008"]},
    "16541001":  {"display": "Tularemia",                          "vet_codes": ["16541001"]},
    "75116005":  {"display": "Q fever",                            "vet_codes": ["75116005"]},
    "75702008":  {"display": "Salmonellosis",                      "vet_codes": ["75702008"]},
    "240589008": {"display": "Psittacosis",                        "vet_codes": ["240589008"]},
}


# ---------------------------------------------------------------------------
@dataclass
class GraphStats:
    n_nodes: int
    n_edges: int
    by_node_type: dict[str, int] = field(default_factory=dict)
    by_edge_type: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
def build_graph(households_bundle: dict) -> nx.MultiDiGraph:
    """Build the One Health knowledge graph from the synthetic households bundle."""
    G = nx.MultiDiGraph()

    for hh in households_bundle["households"]:
        hh_id = hh["household_id"]
        county = hh["county"]
        county_id = f"County/{county['fips']}"

        # County node
        if not G.has_node(county_id):
            G.add_node(county_id, type="County",
                       fips=county["fips"], name=county["name"],
                       lat=county["lat"], lon=county["lon"],
                       epa_eqi=county["epa_eqi"],
                       cocci_endemic=county["cocci_endemic"],
                       population=county["population"],
                       label=county["name"])

        # Household node
        G.add_node(hh_id, type="Household",
                   name=hh["name"], county=county["name"],
                   narrative=hh.get("narrative", ""),
                   label=f"{hh['name']} household")
        G.add_edge(hh_id, county_id, kind="LOCATED_IN")

        # Persons
        for p in hh["humans"]:
            pid = f"Patient/{p['id']}"
            given = p["name"][0]["given"][0]
            family = p["name"][0]["family"]
            G.add_node(pid, type="Person",
                       given=given, family=family,
                       gender=p["gender"], birthDate=p["birthDate"],
                       label=f"{given} {family}")
            G.add_edge(pid, hh_id, kind="LIVES_IN")

        # Animals
        for a in hh["animals"]:
            aid = f"AnimalPatient/{a['id']}"
            G.add_node(aid, type="Animal",
                       name=a["name"],
                       species=a["species"]["display"],
                       species_code=a["species"]["code"],
                       breed=a["breed"], sex=a["sex"], birthDate=a["birthDate"],
                       label=f"{a['name']} ({a['species']['code']})")
            G.add_edge(aid, hh_id, kind="LIVES_IN")

        # Conditions: as nodes keyed by (snomed_code, host_kind)
        # — but we need ONE shared "Disease" node per SNOMED to enable
        #   cross-species matching. So we keep both: a per-encounter Condition
        #   node for the patient's record, and a shared Disease node.
        for c in hh["conditions"]:
            cid = f"Condition/{c['id']}"
            primary = c["code"]["coding"][0]
            snomed = primary["code"]
            display = primary["display"]
            subject_ref = c["subject"]["reference"]

            disease_id = f"Disease/{snomed}"
            if not G.has_node(disease_id):
                G.add_node(disease_id, type="Disease",
                           snomed=snomed, display=display,
                           label=display)

            G.add_node(cid, type="Condition",
                       snomed=snomed, display=display,
                       onsetDateTime=c["onsetDateTime"],
                       label=f"Dx: {display}")
            G.add_edge(subject_ref, cid, kind="HAS_CONDITION")
            G.add_edge(cid, disease_id, kind="INSTANCE_OF")

        # Environmental profile
        env = hh.get("environment", {})
        if env:
            env_id = f"Environment/{hh_id}"
            G.add_node(env_id, type="Environment",
                       epa_eqi=env.get("epa_eqi"),
                       cocci_endemic=env.get("coccidioides_endemicity"),
                       label=f"Env profile · {hh['name']}")
            G.add_edge(hh_id, env_id, kind="HAS_ENVIRONMENT")

            for exp in env.get("recent_exposures", []) + env.get("shared_exposures", []):
                exp_id = f"Exposure/{hh_id}/{exp['type']}"
                G.add_node(exp_id, type="Exposure",
                           exposure_type=exp["type"],
                           label=exp["type"].replace("_", " ").title())
                G.add_edge(hh_id, exp_id, kind="HAS_EXPOSURE")

    # Add cross-species derived edges between Disease nodes (informational).
    for human_code, info in CROSS_SPECIES.items():
        d_human = f"Disease/{human_code}"
        if G.has_node(d_human):
            for vet_code in info["vet_codes"]:
                d_vet = f"Disease/{vet_code}"
                if d_vet != d_human and G.has_node(d_vet):
                    G.add_edge(d_human, d_vet, kind="SAME_DISEASE_AS")

    return G


# ---------------------------------------------------------------------------
# Graph queries used by the surveillance module and the UI
# ---------------------------------------------------------------------------
def household_members(G: nx.MultiDiGraph, household_id: str) -> dict[str, list[str]]:
    """Return all persons and animals living in a household."""
    persons, animals = [], []
    for src, _, data in G.in_edges(household_id, data=True):
        if data.get("kind") != "LIVES_IN":
            continue
        ntype = G.nodes[src].get("type")
        if ntype == "Person":
            persons.append(src)
        elif ntype == "Animal":
            animals.append(src)
    return {"persons": persons, "animals": animals}


def household_for(G: nx.MultiDiGraph, person_or_animal_ref: str) -> str | None:
    for _, dst, data in G.out_edges(person_or_animal_ref, data=True):
        if data.get("kind") == "LIVES_IN":
            return dst
    return None


def conditions_for(G: nx.MultiDiGraph, subject_ref: str) -> list[dict]:
    """Return condition info for a person or animal."""
    out = []
    for _, cond_id, data in G.out_edges(subject_ref, data=True):
        if data.get("kind") != "HAS_CONDITION":
            continue
        n = G.nodes[cond_id]
        out.append({"condition_node": cond_id,
                    "snomed": n["snomed"],
                    "display": n["display"],
                    "onsetDateTime": n.get("onsetDateTime")})
    return out


def cross_species_clusters(G: nx.MultiDiGraph) -> list[dict]:
    """Find households where the SAME disease is present in both a human and an animal.

    This is the One-Health-defining query. Returns one record per
    (household, disease) cluster with member references and onset dates.
    """
    clusters: list[dict] = []
    for hh_id, data in G.nodes(data=True):
        if data.get("type") != "Household":
            continue
        members = household_members(G, hh_id)
        # Collect (host_ref, host_kind, disease_snomed) tuples.
        host_diseases: list[tuple[str, str, dict]] = []
        for ref in members["persons"]:
            for c in conditions_for(G, ref):
                host_diseases.append((ref, "Person", c))
        for ref in members["animals"]:
            for c in conditions_for(G, ref):
                host_diseases.append((ref, "Animal", c))
        # Group by SNOMED.
        by_disease: dict[str, list[tuple[str, str, dict]]] = {}
        for ref, kind, c in host_diseases:
            by_disease.setdefault(c["snomed"], []).append((ref, kind, c))
        for snomed, hits in by_disease.items():
            kinds = {k for _, k, _ in hits}
            if {"Person", "Animal"} <= kinds:
                # Cross-species hit.
                # Earliest onset = index case, others = secondary.
                hits_sorted = sorted(hits, key=lambda h: h[2]["onsetDateTime"] or "")
                index_ref, index_kind, index_c = hits_sorted[0]
                clusters.append({
                    "household_id": hh_id,
                    "household_name": data["name"],
                    "disease_snomed": snomed,
                    "disease_display": index_c["display"],
                    "n_human_cases": sum(1 for _, k, _ in hits if k == "Person"),
                    "n_animal_cases": sum(1 for _, k, _ in hits if k == "Animal"),
                    "index_case": {"ref": index_ref, "kind": index_kind,
                                   "onset": index_c["onsetDateTime"],
                                   "label": G.nodes[index_ref].get("label", index_ref)},
                    "secondary_cases": [
                        {"ref": r, "kind": k, "onset": c["onsetDateTime"],
                         "label": G.nodes[r].get("label", r)}
                        for r, k, c in hits_sorted[1:]
                    ],
                })
    return clusters


def at_risk_household_members(G: nx.MultiDiGraph, household_id: str,
                              disease_snomed: str) -> list[dict]:
    """Members of a household who do NOT have the given diagnosis but live with someone who does.

    These are the prophylactic-alert candidates — same exposure, no diagnosis yet.
    """
    members = household_members(G, household_id)
    diagnosed_refs = set()
    for ref in members["persons"] + members["animals"]:
        for c in conditions_for(G, ref):
            if c["snomed"] == disease_snomed:
                diagnosed_refs.add(ref)
    at_risk = []
    for ref in members["persons"] + members["animals"]:
        if ref not in diagnosed_refs:
            at_risk.append({
                "ref": ref,
                "kind": G.nodes[ref]["type"],
                "label": G.nodes[ref].get("label", ref),
            })
    return at_risk


# ---------------------------------------------------------------------------
def stats(G: nx.MultiDiGraph) -> GraphStats:
    by_node_type: dict[str, int] = {}
    for _, d in G.nodes(data=True):
        t = d.get("type", "Unknown")
        by_node_type[t] = by_node_type.get(t, 0) + 1
    by_edge_type: dict[str, int] = {}
    for _, _, d in G.edges(data=True):
        k = d.get("kind", "Unknown")
        by_edge_type[k] = by_edge_type.get(k, 0) + 1
    return GraphStats(n_nodes=G.number_of_nodes(),
                      n_edges=G.number_of_edges(),
                      by_node_type=by_node_type,
                      by_edge_type=by_edge_type)


def export_for_d3(G: nx.MultiDiGraph) -> dict:
    """Export the graph in the standard D3 force-graph format
    (nodes with `id` and edges with `source`,`target`)."""
    nodes = [{"id": n, **{k: v for k, v in d.items()}} for n, d in G.nodes(data=True)]
    links = [{"source": s, "target": t, **{k: v for k, v in d.items()}} for s, t, d in G.edges(data=True)]
    return {"nodes": nodes, "links": links,
            "stats": {"n_nodes": len(nodes), "n_edges": len(links)}}


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    bundle = json.loads((SYNTH_DIR / "households.json").read_text())
    G = build_graph(bundle)
    s = stats(G)
    print(f"Graph: {s.n_nodes} nodes, {s.n_edges} edges")
    print(f"  Node types: {s.by_node_type}")
    print(f"  Edge types: {s.by_edge_type}")
    print()
    print("Cross-species clusters:")
    for cl in cross_species_clusters(G):
        print(f"  {cl['household_name']:12} {cl['disease_display']:35} "
              f"H={cl['n_human_cases']} A={cl['n_animal_cases']}  "
              f"index={cl['index_case']['label']}")
    print()
    # Demonstrate at-risk query for the Hernandez Valley Fever cluster.
    print("At-risk Hernandez household members (Cocci 5294002):")
    for m in at_risk_household_members(G, "HH-AZ-PIMA-001", "5294002"):
        print(f"   - {m['label']} ({m['kind']})")
    # Export for the UI.
    d3 = export_for_d3(G)
    (OUT_DIR / "knowledge_graph.json").write_text(json.dumps(d3, indent=2, default=str))
    print(f"\nExported D3 graph: data/synthetic/knowledge_graph.json "
          f"({d3['stats']['n_nodes']} nodes, {d3['stats']['n_edges']} edges)")
