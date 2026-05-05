"""
Phase 2: Monte Carlo Statistical Mechanics of a 2DEG
=====================================================
Simulates the thermodynamics of electrons in a 2D quantum well
using the Metropolis-Hastings algorithm.

Outputs:
  - Real-time console updates for each Temperature step.
  - Real-time dynamic plotting of 3 subplots:
      1. Equilibration (Energy vs. MC steps for the current T)
      2. Fermi-Dirac emergence (Occupation vs. Energy)
      3. Specific Heat Capacity (Cv) vs. Temperature
"""

import numpy as np
import matplotlib.pyplot as plt
import time

# 1. IMPORT QUANTUM ENERGIES FROM PHASE 1
# This will run your shooting method quietly and extract the eigenvalues
print("Importing eigenvalues from Phase 1 shooting method...")
try:
    import shooting_method_2DEG as sm
    subband_energies = sm.mid_energies_meV
    print(f"Successfully loaded subband energies: {subband_energies} meV")
except ImportError:
    print("Could not import shooting_method_2DEG. Using fallback placeholder values.")
    subband_energies = np.array([0.0, 35.0, 85.0]) # Fallback meV values

# 2. PARAMETERS
kB = 0.08617  # Boltzmann constant in meV/K

# Simulation parameters
N_electrons = 500       # Number of simulated electrons (keep moderate for speed today)
dE = 0.5                # Energy bin size (meV) - Represents the constant 2D DOS
E_max = 200.0           # Maximum energy to simulate (meV) above E0
temperatures = np.linspace(1, 300, 200)  # Kelvin

# MC parameters
equilibration_steps = 500000
production_steps    = 1000000

# 3. STATE SPACE SETUP (Constant 2D Density of States)
print("Generating state space...")
all_states = []
for n, En in enumerate(subband_energies):
    E = En
    while E <= E_max:
        all_states.append({'subband': n, 'energy': E})
        E += dE

num_states = len(all_states)
state_energies = np.array([s['energy'] for s in all_states])
state_subbands = np.array([s['subband'] for s in all_states])

sort_idx = np.argsort(state_energies)
state_energies = state_energies[sort_idx]
state_subbands = state_subbands[sort_idx]

if num_states < N_electrons:
    raise ValueError("Not enough states for the electrons. Increase E_max or decrease dE.")

# 4. MONTE CARLO CORE FUNCTION
def run_monte_carlo(T, initial_occ, initial_unocc, steps, track_history=False, history=[]):
    """Metropolis-Hastings Markov Chain enforcing Pauli exclusion."""
    occ = initial_occ.copy()
    unocc = initial_unocc.copy()

    total_energy = np.sum(state_energies[occ])
    energy_history = np.zeros(steps) if track_history else None

    beta = 1.0 / (kB * T)
    N_occ = len(occ)
    N_unocc = len(unocc)
    accepted_moves = 0

    for step in range(1, steps):
        # Propose move
        idx_occ_arr = np.random.randint(0, N_occ)
        idx_unocc_arr = np.random.randint(0, N_unocc)

        state_i = occ[idx_occ_arr]
        state_j = unocc[idx_unocc_arr]

        # Calculate energy difference
        dE_move = state_energies[state_j] - state_energies[state_i]

        # Metropolis Criterion
        accept = False
        if dE_move < 0:
            accept = True
        elif np.random.rand() < np.exp(-beta * dE_move * 2.4):
            accept = True

        # Execute Move
        if accept:
            occ[idx_occ_arr] = state_j
            unocc[idx_unocc_arr] = state_i
            total_energy += dE_move
            accepted_moves += 1
            history.append(total_energy)

        if track_history:
            energy_history[step] = total_energy

    return occ, unocc, total_energy, energy_history, accepted_moves / steps

# 5. REAL-TIME PLOTTING SETUP
plt.ion() # Turn on interactive mode for real-time updates
fig = plt.figure(figsize=(15, 5))
ax1 = fig.add_subplot(131)
ax2 = fig.add_subplot(132)
ax3 = fig.add_subplot(133)
fig.tight_layout(pad=3.0)

# Initialize at T=0
current_occ = np.arange(N_electrons)
current_unocc = np.arange(N_electrons, num_states)

completed_T = []
Cv_data = []

print("\nStarting real-time Monte Carlo Simulation...")
print("-" * 60)

for T in temperatures:
    print(f"Running T = {T:5.1f} K... ", end="", flush=True)

    # Equilibration Phase (Track history for real-time plot)
    current_occ, current_unocc, _, eq_hist, acc_rate = run_monte_carlo(
        T, current_occ, current_unocc, equilibration_steps, track_history=True
    )

    # Production Phase
    snapshots = 500
    steps_between = production_steps // snapshots
    sampled_energies = np.zeros(snapshots)

    for i in range(snapshots):
        current_occ, current_unocc, e_tot, _, _ = run_monte_carlo(
            T, current_occ, current_unocc, steps_between, track_history=False
        )
        sampled_energies[i] = e_tot

    mean_E = sum(sampled_energies) / len(sampled_energies)
    var_E = sum((e - mean_E) ** 2 for e in sampled_energies) / len(sampled_energies)
    cv_val = var_E / (kB * T**2) / N_electrons

    completed_T.append(T)
    Cv_data.append(cv_val)

    print(f"<E> = {mean_E/N_electrons:6.2f} meV | Cv = {cv_val:5.3f} | Acc: {acc_rate*100:4.1f}%")

    # --- REAL-TIME PLOT UPDATES ---

    # Subplot 1: Equilibration (updates completely per T)
    ax1.clear()
    ax1.plot(eq_hist / N_electrons, color='purple', alpha=0.7)
    ax1.set_title(f"Equilibration at T={T:.1f} K")
    ax1.set_xlabel("Monte Carlo Steps")
    ax1.set_ylabel("Average Energy (meV/e-)")
    ax1.grid(True, alpha=0.3)

    # Subplot 2: Fermi-Dirac Distribution
    ax2.clear()
    bins = np.arange(0, E_max, 5.0)
    hist, bin_edges = np.histogram(state_energies[current_occ], bins=bins)
    centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    total_states_hist, _ = np.histogram(state_energies, bins=bins)
    prob = np.zeros_like(hist, dtype=float)
    valid = total_states_hist > 0
    prob[valid] = hist[valid] / total_states_hist[valid]

    ax2.plot(centers, prob, 'bo-', markersize=4)
    ax2.set_title(f"Occupation Probability at T={T:.1f} K")
    ax2.set_xlabel("Energy (meV)")
    ax2.set_ylabel("f(E)")
    ax2.set_ylim(-0.05, 1.05)
    ax2.axvline(x=N_electrons*dE, color='k', linestyle='--', label='Approx $E_F$')
    ax2.grid(True, alpha=0.3)

    # Subplot 3: Heat Capacity (builds up continuously)
    ax3.clear()
    ax3.plot(completed_T, Cv_data, 'k-s', linewidth=2, markersize=5)
    ax3.set_title("Specific Heat Capacity $C_v$ vs T")
    ax3.set_xlabel("Temperature (K)")
    ax3.set_ylabel("$C_v$ ($k_B$ per electron)")
    ax3.set_xlim(0, max(temperatures) + 10)
    # Estimate the expected peak
    if len(subband_energies) > 1:
        delta_E = subband_energies[1] - subband_energies[0]
        ax3.axvline(x=delta_E/kB, color='gray', linestyle=':', alpha=0.7)
    ax3.grid(True, alpha=0.3)

    # Flush GUI events to update the screen
    fig.canvas.flush_events()
    plt.pause(0.01)

print("-" * 60)
print("Simulation complete! Saving final figure...")
plt.ioff() # Turn off interactive mode
plt.savefig('Phase2_RealTime_Thermodynamics.png', dpi=200)
plt.show() # Keep the final plot open
