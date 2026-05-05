"""
mc_2deg_thermo / sampler.py
============================
Production refactor of the original procedural Phase 2 script.

The 180-line top-level loop is replaced by a MetropolisSampler class with
five methods (propose, accept_reject, record, diagnostics, run), an
injected RNG, and a typed configuration dataclass. I/O and plotting live
in separate modules (ChainWriter, ChainDiagnostics) so the sampler is
pure-Python-importable from a test harness.

Bug fixes preserved relative to the research version:
  - Off-by-one: equilibration loop now starts at 0 (was range(1, steps)).
  - Mutable default arg: history=[] removed from run_monte_carlo signature;
    state is owned by the sampler instance.
  - Hardcoded acceptance factor 2.4 in Metropolis criterion removed; the
    factor is exposed as SamplerConfig.beta_scale (default 1.0) and
    flagged for researcher confirmation.
  - Catastrophic cancellation: naive Python sum loops in mean/variance
    replaced with Welford's online algorithm + Kahan compensated sum
    for the running total energy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SamplerConfig:
    """All sampler knobs in one typed object. No globals."""

    kB: float = 0.08617                 # Boltzmann (meV/K)
    n_electrons: int = 500
    dE: float = 0.5                     # bin size, meV
    e_max: float = 200.0                # ceiling, meV above E0
    equilibration_steps: int = 500_000
    production_steps: int = 1_000_000
    snapshots: int = 500
    beta_scale: float = 1.0             # was hardcoded 2.4 — see researcher Q
    subband_energies_meV: tuple = (0.0, 35.0, 85.0)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def build_state_space(cfg: SamplerConfig) -> tuple[np.ndarray, np.ndarray]:
    """Constant 2D DOS state ladder. Returns (energies, subbands), sorted."""
    states: list[tuple[int, float]] = []
    for n, En in enumerate(cfg.subband_energies_meV):
        E = En
        while E <= cfg.e_max:
            states.append((n, E))
            E += cfg.dE
    if len(states) < cfg.n_electrons:
        raise ValueError("Not enough states for the electrons.")
    arr = np.array(states, dtype=[("subband", "i4"), ("energy", "f8")])
    order = np.argsort(arr["energy"])
    return arr["energy"][order], arr["subband"][order]


def kahan_sum(xs: Iterable[float]) -> float:
    """Compensated summation — bounds error at O(eps) regardless of length."""
    s = 0.0
    c = 0.0
    for x in xs:
        y = x - c
        t = s + y
        c = (t - s) - y
        s = t
    return s


def welford_mean_var(xs: np.ndarray) -> tuple[float, float]:
    """Online mean/variance — numerically stable for large N and large means."""
    n = 0
    mean = 0.0
    m2 = 0.0
    for x in xs:
        n += 1
        d = x - mean
        mean += d / n
        m2 += d * (x - mean)
    if n < 2:
        return mean, 0.0
    return mean, m2 / n


# ---------------------------------------------------------------------------
# Sampler
# ---------------------------------------------------------------------------

class MetropolisSampler:
    """Metropolis-Hastings on a 2DEG occupation vector with Pauli exclusion.

    Five methods, one job each:
        propose()        — pick (occ, unocc) index pair
        accept_reject()  — Metropolis criterion, no hardcoded factor
        record()         — Kahan-compensated running energy
        diagnostics()    — Welford mean/variance over snapshots
        run()            — drive equilibration + production for one T
    """

    def __init__(
        self,
        cfg: SamplerConfig,
        state_energies: np.ndarray,
        rng: Optional[np.random.Generator] = None,
    ):
        self.cfg = cfg
        self.state_energies = state_energies
        self.rng = rng if rng is not None else np.random.default_rng()
        self._kahan_c = 0.0  # compensation term carried across record() calls

    # -- core moves -----------------------------------------------------------

    def propose(self, occ: np.ndarray, unocc: np.ndarray) -> tuple[int, int]:
        return (
            int(self.rng.integers(0, len(occ))),
            int(self.rng.integers(0, len(unocc))),
        )

    def accept_reject(self, dE_move: float, beta: float) -> bool:
        if dE_move < 0:
            return True
        return self.rng.random() < np.exp(-beta * dE_move * self.cfg.beta_scale)

    def record(self, total_energy: float, dE_move: float) -> float:
        y = dE_move - self._kahan_c
        t = total_energy + y
        self._kahan_c = (t - total_energy) - y
        return t

    def diagnostics(self, sampled_energies: np.ndarray) -> tuple[float, float]:
        return welford_mean_var(sampled_energies)

    # -- driver ---------------------------------------------------------------

    def run(
        self,
        T: float,
        occ: np.ndarray,
        unocc: np.ndarray,
        steps: int,
        track_history: bool = False,
    ) -> dict:
        occ = occ.copy()
        unocc = unocc.copy()
        beta = 1.0 / (self.cfg.kB * T)
        total_energy = float(np.sum(self.state_energies[occ]))
        self._kahan_c = 0.0
        history = np.zeros(steps) if track_history else None
        accepted = 0

        for step in range(0, steps):                       # off-by-one fixed
            i, j = self.propose(occ, unocc)
            si, sj = occ[i], unocc[j]
            dE = float(self.state_energies[sj] - self.state_energies[si])
            if self.accept_reject(dE, beta):
                occ[i] = sj
                unocc[j] = si
                total_energy = self.record(total_energy, dE)
                accepted += 1
            if track_history:
                history[step] = total_energy

        return {
            "occ": occ,
            "unocc": unocc,
            "total_energy": total_energy,
            "history": history,
            "acceptance": accepted / steps,
        }


# ---------------------------------------------------------------------------
# Top-level driver — kept thin; plotting & I/O live elsewhere now.
# ---------------------------------------------------------------------------

def sweep_temperature(
    cfg: SamplerConfig,
    temperatures: np.ndarray,
    rng: Optional[np.random.Generator] = None,
) -> dict:
    state_energies, _ = build_state_space(cfg)
    sampler = MetropolisSampler(cfg, state_energies, rng=rng)

    occ = np.arange(cfg.n_electrons)
    unocc = np.arange(cfg.n_electrons, len(state_energies))

    Cv = []
    for T in temperatures:
        eq = sampler.run(T, occ, unocc, cfg.equilibration_steps, track_history=True)
        occ, unocc = eq["occ"], eq["unocc"]

        steps_between = cfg.production_steps // cfg.snapshots
        sampled = np.zeros(cfg.snapshots)
        for k in range(cfg.snapshots):
            prod = sampler.run(T, occ, unocc, steps_between, track_history=False)
            occ, unocc = prod["occ"], prod["unocc"]
            sampled[k] = prod["total_energy"]

        _, var_E = sampler.diagnostics(sampled)
        Cv.append(var_E / (cfg.kB * T ** 2) / cfg.n_electrons)

    return {"temperatures": np.asarray(temperatures), "Cv": np.asarray(Cv)}
