# Swarm Learning + Privacy Architecture — Implementation Spec

**Component:** Cross-site training and privacy layer
**Status:** Spec; implementation scaffolded for demo, full deployment is roadmap
**Owner:** ONE-HealthRecord project team

---

## 1. Why swarm learning, in one paragraph

The One Health surveillance network we are designing for spans organizations with genuinely different trust postures: Tucson Medical Center, the Navajo Nation Department of Health, private vet clinics in Pinal County, the Arizona Department of Health Services, the USDA Animal and Plant Health Inspection Service. None of them should have to designate one of the others as the trusted aggregator in order for the system to learn. Federated learning forces exactly that designation. Swarm learning eliminates the central aggregator entirely — the coordination role is played by a permissioned blockchain ledger whose trust model is *cryptographic*, not *organizational*. That is the right fit for our deployment context, and it gives us a thesis-level differentiation: we chose SL over FL because the One Health threat surface includes the aggregator itself.

---

## 2. The four-layer privacy stack

Each layer addresses a different attack surface. Layers are stacked, not chosen.

```
┌───────────────────────────────────────────────────────────────────────┐
│ LAYER 4 — Output privacy (Laplace ε=1.0 on aggregate counts)         │  ← already shipped
├───────────────────────────────────────────────────────────────────────┤
│ LAYER 3 — Secure aggregation on weight exchange                      │  ← Bonawitz CCS'17
├───────────────────────────────────────────────────────────────────────┤
│ LAYER 2 — DP-SGD inside each site's local training step              │  ← Opacus, ε≤8.0
├───────────────────────────────────────────────────────────────────────┤
│ LAYER 1 — Swarm learning topology (no central aggregator)            │  ← HPE SL, blockchain coord
└───────────────────────────────────────────────────────────────────────┘
```

| Layer | Attack it stops | Library |
|---|---|---|
| 1 — Swarm topology | Aggregator compromise; aggregator coercion | `hpe-swarm-learning` (Apache 2.0) |
| 2 — DP-SGD | Training-data extraction via model inversion | `opacus` 1.4 |
| 3 — Secure aggregation | Reconstruction of any single site's update | `tf-encrypted` / custom Bonawitz impl |
| 4 — Laplace on outputs | Re-identification via the public surveillance feed | NumPy + `numpy.random.laplace` (already shipped) |

---

## 3. Layer 1 — Swarm learning topology

### 3.1 Site roles

A "site" is any participating organization that holds raw training data and runs a local training process. In the deployment model we are designing for:

| Site type | Example | Data held | Role in the swarm |
|---|---|---|---|
| Hospital system | Tucson Medical Center | Human EHR notes | Full participant; trains LoRA + risk model |
| Vet hospital network | A Pinal County mixed-practice clinic | Veterinary records | Full participant; trains LoRA + risk model |
| State public health | ADHS | Reportable-disease confirmed counts | Limited participant; risk-model only |
| Federal animal health | USDA APHIS | Production-animal reportable disease | Limited participant; risk-model only |
| Tribal health authority | Navajo Nation DoH | Tribal-land EHR | **Optional participant — full sovereignty over participation** |

### 3.2 Round structure

Each training round:

1. **Local training.** Each site trains the current model snapshot on its local data for `k = 5` epochs. DP-SGD active throughout (Layer 2).
2. **Weight masking.** Each site computes `delta_i = w_local - w_round_start` and masks `delta_i` with additive secret-shared noise (Layer 3).
3. **Ledger publication.** Each site publishes the masked delta to the swarm-learning blockchain ledger, with a digital signature.
4. **Quorum check.** When ≥ 2/3 of registered sites have published, the round is closed.
5. **Reconstruction.** Sites cooperatively reconstruct `Σ delta_i` (the sum, but not any individual `delta_i`), divide by the participant count to get the round's aggregate update, and apply it locally.
6. **Verification.** Each site verifies the reconstructed aggregate matches the ledger-recorded participation set.
7. **Next round.**

A round takes 30–90 seconds in our simulated three-site demo. In production over WAN connections between hospital systems, rounds would be on the order of minutes to hours depending on update size.

### 3.3 What the blockchain stores

The ledger does **not** store raw weights, gradients, or training data. It stores:

- Participation records: which site participated in which round, with timestamp and signature
- Cryptographic commitments to masked updates (hashes, not contents)
- Aggregate update hashes for cross-site verification
- A versioned model lineage: round N produced model `M_N` with hash `H_N`, derived from `M_{N-1}` with the contributing site set `{s_a, s_b, s_c, ...}`

The ledger is permissioned. Adding a new participating site requires consensus from the existing site set. We use a Proof-of-Authority consensus model (not Proof-of-Work) — there is no mining, no public token, no environmental cost beyond the compute cost of cryptographic operations on the participating servers.

### 3.4 Robust aggregation against poisoned updates

A malicious site can submit a deliberately-crafted weight update designed to degrade the model (a "poisoning attack"). We mitigate with two robust aggregators that the swarm can switch between by configuration:

- **Krum** (Blanchard et al., NeurIPS 2017): selects the single update most similar to its peers; robust if ≤ 1/3 of sites are malicious.
- **Coordinate-wise median**: takes the median of each parameter across sites; more robust to outliers but slower convergence.

The default is Krum for the LoRA training (where convergence speed matters) and median for the risk-model training (where final accuracy matters more than convergence speed).

This is a research-grade defense and the Model Card states it is not a guarantee. A coordinated attack by more than 1/3 of sites will still degrade the model.

---

## 4. Layer 2 — DP-SGD inside each site's local training step

### 4.1 Configuration

```python
# Pseudocode — actual implementation in src/training/dp_sgd_trainer.py
from opacus import PrivacyEngine

privacy_engine = PrivacyEngine()
model, optimizer, train_loader = privacy_engine.make_private_with_epsilon(
    module=model,
    optimizer=optimizer,
    data_loader=train_loader,
    epochs=k_local_epochs,
    target_epsilon=8.0,        # LoRA: 8.0; Risk model: 4.0
    target_delta=1e-5,
    max_grad_norm=1.0,         # Per-example gradient clipping
)
```

### 4.2 Privacy budget accounting

We use Rényi Differential Privacy (Mironov, 2017) for tight composition across rounds and across the swarm. Each round consumes a small portion of the total budget; the privacy accountant tracks cumulative cost and refuses additional rounds once the budget is exhausted.

| Component | Per-round ε spend | Total rounds | Total ε |
|---|---|---|---|
| Companion-animal LoRA | ~0.05 | ~160 | 8.0 |
| Production-animal LoRA | ~0.05 | ~160 | 8.0 |
| Risk model | ~0.025 | ~160 | 4.0 |
| **Cumulative on any single training subject** | — | — | ≤ 8.0 |

(Because no individual subject is in both the companion and production LoRA training sets, and no individual is in both the LoRA training set and the risk-model training set, the per-subject budget does not compound across components.)

### 4.3 What DP-SGD costs us in accuracy

The Model Card §7.2 reports a sensitivity analysis at three privacy budgets. We expect 1–3 percentage points of AUC degradation at ε = 8.0 vs the non-private baseline, based on prior literature on similarly-sized datasets. Worth it for the privacy guarantee.

---

## 5. Layer 3 — Secure aggregation on weight exchange

### 5.1 Protocol

We implement Bonawitz et al. (CCS 2017) Secure Aggregation:

1. **Setup phase.** Sites run a Diffie-Hellman key exchange to establish pairwise shared secrets `s_ij` between every pair of sites `(i, j)`.
2. **Mask phase.** Each site `i` computes its update `delta_i` and masks it as:
   `masked_i = delta_i + Σ_{j > i} PRG(s_ij) − Σ_{j < i} PRG(s_ji)`
   The pairwise PRG outputs cancel in the sum across all sites, so `Σ masked_i = Σ delta_i`.
3. **Drop-out tolerance.** If a site drops out mid-round, its share of the pairwise masks would prevent reconstruction. We use threshold secret-sharing of each site's secret keys among the others, so any quorum of `≥ 2/3 + 1` surviving sites can reconstruct the aggregate.
4. **Reveal phase.** Sites publish their masked updates to the ledger. The ledger reconstructs the aggregate via the sum.

### 5.2 What this gives us

Before secure aggregation, a malicious aggregator could see each site's individual `delta_i` and run model-inversion attacks site-by-site. After secure aggregation, the aggregator (or any observer of the ledger) sees only `Σ delta_i` — the sum, never an individual contribution. Combined with DP-SGD inside each site's local step, the privacy guarantee is multi-layered: even if secure aggregation were broken, DP-SGD still bounds what any individual `delta_i` can leak about its training data.

### 5.3 Communication cost

Secure aggregation roughly doubles the bytes-on-the-wire per round (each site publishes its masked update plus its share of others' secret keys). For LoRA updates at ~32 MB per site per round, this is ~64 MB published per site per round. Manageable on commodity WAN.

---

## 6. Layer 4 — Laplace on aggregate output counts (already shipped)

This is the layer that has been in place since v1.0. It applies the Laplace mechanism with ε = 1.0 and sensitivity = 1 to:

- County-level case counts on the One Health Map
- Household-cluster counts in the Sentinel Alerts feed
- Incidence-rate computations in the public-facing aggregate API

```python
import numpy as np

def laplace_protected_count(true_count: int, epsilon: float = 1.0) -> int:
    """ε-DP protected count via Laplace mechanism.
    Sensitivity = 1 because adding/removing one record changes the count by 1.
    """
    noise = np.random.laplace(loc=0.0, scale=1.0 / epsilon)
    return max(0, int(round(true_count + noise)))
```

This protects the **outputs** — the aggregate counts a public-health officer would see on the dashboard — from re-identification attacks. Combined with the upstream privacy of the model itself (Layers 1–3), the surveillance feed is differentially private end-to-end.

---

## 7. Demo implementation for the next iteration

For the project demo we present a **honest, working, single-laptop simulation** of the full stack:

### 7.1 What we ship

1. **Three Python processes simulating three sites** (`site_hospital`, `site_vet`, `site_adhs`) on the same laptop, communicating via local TCP sockets.
2. **A local blockchain stub** (in-memory append-only ledger with hash chaining and signature verification, using `cryptography` library). Not production-grade but sufficient to demonstrate the round protocol.
3. **DP-SGD active in each site's local training loop** via Opacus, with the actual privacy budget computed and displayed in the Model Card tab in real time.
4. **Secure aggregation between sites** using a simplified Bonawitz implementation (no drop-out tolerance for the demo; sites are assumed to stay up for the duration of the demo round).
5. **A Model Card panel** that visualizes:
   - Current round number
   - Per-site contribution status (pending / submitted / verified)
   - Cumulative privacy budget consumed
   - Reconstructed aggregate update size
   - Round-over-round model loss curve

### 7.2 What we explicitly do not ship in the demo

- Real cross-WAN deployment (single laptop only)
- Full HPE Swarm Learning integration (we use a simplified stub for the blockchain layer)
- Threshold-secret-sharing drop-out tolerance (sites are assumed stable in demo)
- Real cryptographic key management (demo uses ephemeral keys)
- Adversarial robust aggregation (Krum/median are scaffolded but not exercised in the demo)

### 7.3 What this gives us, and what we say about it

The demo demonstrates the technique end-to-end on a CPU-only laptop with all four privacy layers active and the privacy budget actually computed. The thesis claim is:

> *The privacy architecture is implemented and verifiable; the deployment topology is documented and ready for production engineering.*

That claim is true and defensible. We do not claim "this is production-ready code." We claim "this is a working demonstrator of a sound architecture," which is exactly what a capstone is supposed to be.

---

## 8. File layout to add to the repo

```
src/
└── privacy/
    ├── __init__.py
    ├── swarm_coordinator.py       # the round protocol; ledger client; quorum logic
    ├── ledger_stub.py              # the in-memory blockchain stub for demo
    ├── secure_aggregation.py       # Bonawitz mask/unmask; pairwise key exchange
    ├── dp_sgd_trainer.py           # Opacus-wrapped training loop
    ├── laplace_mechanism.py        # already exists; refactored from sentinel_alerts.py
    └── tests/
        ├── test_secure_aggregation.py
        ├── test_dp_budget_accounting.py
        └── test_round_protocol.py
docs/
├── swarm_learning_architecture.md  # this document
└── privacy_threat_model.md         # to be written: explicit threat model and defenses
```

---

## 9. Threat model summary (one-page version)

| Adversary | Capability | Defense | Residual risk |
|---|---|---|---|
| Compromised aggregator | Read all individual updates | Layer 3 secure aggregation hides individual updates | Aggregator can still observe participation timing on ledger |
| Compromised single site | Read its own data; submit poisoned updates | Krum/median robust aggregation; DP-SGD bounds local-data leakage | Coordinated attack by ≥ 1/3 sites still degrades model |
| Network observer | Sees encrypted traffic; sees ledger metadata | TLS for transport; ledger hides update contents | Side-channel on participation timing |
| Adversary with API access to deployed model | Run model-inversion or membership-inference attacks | DP-SGD bounds extraction probability | Per-prediction guarantee weaker than training-run guarantee; query budget required in production |
| Adversary with access to public surveillance feed | Run linkage attacks against external data | Layer 4 Laplace ε=1.0 noise | Persistent attacker can erode bound over many queries |
| Insider auditor | Read FHIR Provenance trail | Provenance does not contain training data | Audit trail itself is not protected by DP; access-controlled separately |

---

## 10. References

- Bonawitz, K., et al. (2017). *Practical Secure Aggregation for Privacy-Preserving Machine Learning.* CCS '17.
- Blanchard, P., et al. (2017). *Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent (Krum).* NeurIPS 2017.
- Mironov, I. (2017). *Rényi Differential Privacy.* CSF 2017.
- Saldanha, O. L., et al. (2022). *Swarm learning for decentralized artificial intelligence in cancer histopathology.* Nature Medicine 28, 1232–1239.
- Warnat-Herresthal, S., et al. (2021). *Swarm Learning for decentralized and confidential clinical machine learning.* Nature 594, 265–270.
- HPE Swarm Learning open-source release: <https://github.com/HewlettPackard/swarm-learning>
- Opacus PyTorch DP library: <https://opacus.ai>
