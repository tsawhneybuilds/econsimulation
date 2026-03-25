"""Labour market: search and matching."""
from __future__ import annotations
import numpy as np
from src.engine.core.state import SimulationState


def search_and_matching_labour(state: SimulationState) -> None:
    """
    Match unemployed workers to firm vacancies.
    BeforeIT.jl: search_and_matching_labour!
    """
    firms = state.firms
    workers = state.workers_act
    rng = state.rng_state
    I = firms.n_firms
    H = workers.n_workers

    # Vacancies = max(desired - current, 0)
    firms.V_i = np.maximum(firms.N_d_i - firms.N_i, 0).astype(int)
    total_vacancies = firms.V_i.sum()

    # Unemployed workers
    unemployed_mask = workers.O_h == 0
    unemployed_idx = np.where(unemployed_mask)[0]
    n_unemployed = len(unemployed_idx)

    if total_vacancies == 0 or n_unemployed == 0:
        return

    # Shuffle unemployed workers and match to firms with vacancies
    rng.shuffle(unemployed_idx)
    firms_with_vacancies = np.repeat(np.arange(I), firms.V_i)
    rng.shuffle(firms_with_vacancies)

    n_matches = min(n_unemployed, len(firms_with_vacancies))
    for k in range(n_matches):
        h = unemployed_idx[k]
        f = firms_with_vacancies[k]
        workers.O_h[h] = f + 1  # 1-indexed firm assignment
        workers.w_h[h] = firms.w_bar_i[f]
        firms.V_i[f] = max(0, firms.V_i[f] - 1)
        firms.N_i[f] += 1

    # Also handle separations: small random job destruction
    employed_mask = workers.O_h > 0
    employed_idx = np.where(employed_mask)[0]
    if len(employed_idx) > 0:
        sep_rate = 0.015  # 1.5% quarterly separation
        separating = rng.random(len(employed_idx)) < sep_rate
        for k, h in enumerate(employed_idx):
            if separating[k]:
                f_idx = workers.O_h[h] - 1  # convert back to 0-indexed
                if 0 <= f_idx < I:
                    firms.N_i[f_idx] = max(0, firms.N_i[f_idx] - 1)
                workers.O_h[h] = 0
                # Keep last wage for unemployment benefit calc


def update_workers_wages(state: SimulationState) -> None:
    """
    Workers' wages updated to reflect new firm wages.
    BeforeIT.jl: update_workers_wages!
    """
    firms = state.firms
    workers = state.workers_act

    employed_mask = workers.O_h > 0
    employed_idx = np.where(employed_mask)[0]

    for h in employed_idx:
        f = workers.O_h[h] - 1
        if 0 <= f < firms.n_firms:
            workers.w_h[h] = firms.w_i[f]
