"""USInitializer: builds SimulationState from CalibrationBundle + ObservedDataset."""
from __future__ import annotations

import numpy as np

from src.engine.core.state import (
    SimulationState, AggregateState, FirmState, WorkerState,
    BankState, CentralBankState, GovernmentState, ROTWState,
    FinancialState, SimData,
)
from src.us.calibration.us_calibration import CalibrationBundle
from src.us.data_contracts.build_dataset import ObservedDataset
from .validators import InitializationValidator


class USInitializer:
    """Initialize simulation state from calibration + observed data."""

    def initialize(
        self,
        calib: CalibrationBundle,
        obs_data: ObservedDataset,
        seed: int = 42,
    ) -> SimulationState:
        """
        Build the initial SimulationState for 2019Q4 baseline.

        Steps:
        1. Set aggregate state from NIPA data
        2. Distribute firms across sectors
        3. Initialize worker arrays
        4. Set bank, central bank, govt, ROW states
        5. Validate
        """
        rng = np.random.default_rng(seed)
        s = calib.structural
        d = calib.initial_distributions
        sp = calib.shock_process

        # ── 1. Aggregate ──────────────────────────────────────────────────
        Y_0 = d.Y_0
        # Quarterly rate: annualised FFR / 4 ≈ 1.55% / 4
        r_bar_0 = 0.0155 / 4.0

        aggregate = AggregateState(
            Y=Y_0,
            Y_real=Y_0,
            pi_=0.005,           # ~2% annual = 0.5% quarterly
            P_bar=d.P_bar_0,
            P_bar_HH=d.P_bar_0,
            P_bar_CF=d.P_bar_0,
            P_bar_g=np.ones(s.G),
            Y_e=Y_0,
            gamma_e=0.005,
            pi_e=0.005,
            r_bar=r_bar_0,
        )

        # ── 2. Firms ──────────────────────────────────────────────────────
        I = s.I
        sector_weights = np.array(s.sector_weights)
        # Assign sectors
        G_i = rng.choice(s.G, size=I, p=sector_weights)

        alpha_bar_i = np.array([s.alpha_bar[g] for g in G_i]) * (1 + rng.normal(0, 0.02, I))
        beta_i = np.array([s.beta[g] for g in G_i])
        kappa_i = np.array([s.kappa[g] for g in G_i])
        delta_i = np.array([s.delta[g] for g in G_i])
        tau_Y_i = np.array([s.tau_Y[g] for g in G_i])
        tau_K_i = np.array([s.tau_K_sect[g] for g in G_i])

        # Scale output per firm to aggregate GDP
        gva_shares = np.array([d.gva_shares[g] for g in G_i])
        gva_shares /= gva_shares.sum()
        Y_i = gva_shares * Y_0 * 0.01  # per firm (bn USD)

        P_i = np.ones(I)
        Q_i = Y_i.copy()
        K_i = Y_i * 8.0   # capital/output ratio ≈ 8
        L_i = K_i * 0.4   # leverage ~40% of capital
        D_i = Y_i * 0.5
        E_i = K_i - L_i
        w_bar_i = np.full(I, Y_0 * 0.0001)  # average wage per firm
        N_i = np.maximum(1, (Y_i / (alpha_bar_i * w_bar_i)).astype(int))

        firms = FirmState(
            G_i=G_i,
            alpha_bar_i=alpha_bar_i,
            beta_i=beta_i,
            kappa_i=kappa_i,
            delta_i=delta_i,
            tau_Y_i=tau_Y_i,
            tau_K_i=tau_K_i,
            N_i=N_i,
            Y_i=Y_i,
            Q_i=Q_i,
            Q_d_i=Q_i.copy(),
            P_i=P_i,
            S_i=np.zeros(I),
            K_i=K_i,
            M_i=Y_i * beta_i,
            L_i=L_i,
            pi_bar_i=np.zeros(I),
            D_i=D_i,
            Pi_i=np.zeros(I),
            V_i=np.zeros(I, dtype=int),
            I_i=K_i * delta_i,
            E_i=E_i,
            P_bar_i=np.ones(I),
            DS_i=np.zeros(I),
            DM_i=np.zeros(I),
            DL_i=np.zeros(I),
            DL_d_i=np.zeros(I),
            K_e_i=K_i.copy(),
            L_e_i=L_i.copy(),
            Q_s_i=Q_i.copy(),
            I_d_i=K_i * delta_i,
            DM_d_i=np.zeros(I),
            N_d_i=N_i.copy(),
            Pi_e_i=np.zeros(I),
            w_i=w_bar_i.copy(),
            w_bar_i=w_bar_i.copy(),
            Y_h_i=Y_i * 0.1,
            C_d_h_i=Y_i * 0.06,
            I_d_h_i=Y_i * 0.01,
            C_h_i=np.zeros(I),
            I_h_i=np.zeros(I),
            K_h_i=Y_i * 0.08,
            D_h_i=Y_i * 0.05,
        )

        # ── 3. Workers ────────────────────────────────────────────────────
        H_act = s.H_act
        H_inact = s.H_inact
        u_rate = d.unemployment_rate_0
        H_employed = int(H_act * (1 - u_rate))
        H_unemployed = H_act - H_employed

        # Base wage
        w_base = Y_0 / (H_employed * 4)  # rough quarterly wage
        w_h_act = rng.lognormal(np.log(w_base), 0.3, H_act)
        O_h_act = np.zeros(H_act, dtype=int)
        # Assign employed workers to firms
        firm_slots = np.repeat(np.arange(I), np.maximum(N_i, 0))
        rng.shuffle(firm_slots)
        assigned = min(H_employed, len(firm_slots))
        O_h_act[:assigned] = firm_slots[:assigned]

        Y_h_act = np.where(
            O_h_act > 0,
            w_h_act * (1 - s.tau_SIW - s.tau_INC * (1 - s.tau_SIW)),
            w_h_act * s.theta_UB,
        )

        workers_act = WorkerState(
            Y_h=Y_h_act,
            D_h=d.D_H * Y_h_act,
            K_h=d.K_H * Y_h_act,
            w_h=w_h_act,
            O_h=O_h_act,
            C_d_h=Y_h_act * 0.7,
            I_d_h=Y_h_act * 0.05,
            C_h=np.zeros(H_act),
            I_h=np.zeros(H_act),
        )

        w_inact_val = rng.lognormal(np.log(w_base * 0.3), 0.3, H_inact)
        Y_h_inact = w_inact_val * 0.3
        workers_inact = WorkerState(
            Y_h=Y_h_inact,
            D_h=d.D_H * Y_h_inact,
            K_h=d.K_H * Y_h_inact,
            w_h=w_inact_val,
            O_h=np.full(H_inact, -1, dtype=int),
            C_d_h=Y_h_inact * 0.5,
            I_d_h=np.zeros(H_inact),
            C_h=np.zeros(H_inact),
            I_h=np.zeros(H_inact),
        )

        # ── 4. Bank ───────────────────────────────────────────────────────
        mu = sp.mu
        E_k = d.E_k
        Pi_k = mu * L_i.sum() + r_bar_0 * E_k
        bank = BankState(
            E_k=E_k,
            Pi_k=Pi_k,
            Pi_e_k=Pi_k,
            D_k=D_i.sum() + E_k - L_i.sum(),
            r=r_bar_0 + mu,
        )

        # ── 5. Central Bank ───────────────────────────────────────────────
        central_bank = CentralBankState(
            r_bar=r_bar_0,
            r_G=0.0172 / 4,  # 10y Treasury ~1.72% 2019Q4
            rho=sp.rho,
            r_star=sp.r_star,
            pi_star=sp.pi_star,
            xi_pi=sp.xi_pi,
            xi_gamma=sp.xi_gamma,
            E_CB=0.0,
        )

        # ── 6. Government ─────────────────────────────────────────────────
        sb_inact = Y_h_inact.mean() * 0.5
        sb_other = w_base * 0.01
        C_d_j = np.array(d.gva_shares) * d.G_0
        government = GovernmentState(
            Y_G=0.0,
            C_G=d.G_0,
            L_G=d.L_G,
            sb_inact=sb_inact,
            sb_other=sb_other,
            C_d_j=C_d_j,
            C_j=d.G_0,
            P_j=1.0,
        )

        # ── 7. ROW ────────────────────────────────────────────────────────
        exports = abs(d.NX_0) * 0.7 + d.I_0 * 0.05
        imports = exports - d.NX_0
        rotw = ROTWState(
            alpha_E=sp.alpha_E,
            beta_E=sp.beta_E,
            sigma_E=sp.sigma_E,
            alpha_I=sp.alpha_I,
            beta_I=sp.beta_I,
            sigma_I=sp.sigma_I,
            Y_ROW=80_000.0,   # rough global ex-US GDP proxy
            gamma_ROW=0.006,
            pi_ROW=0.005,
            alpha_pi_ROW=sp.alpha_pi_ROW,
            beta_pi_ROW=sp.beta_pi_ROW,
            sigma_pi_ROW=sp.sigma_pi_ROW,
            alpha_Y_ROW=sp.alpha_Y_ROW,
            beta_Y_ROW=sp.beta_Y_ROW,
            sigma_Y_ROW=sp.sigma_Y_ROW,
            D_RoW=d.NX_0 * 4.0,
            Y_I=imports,
            C_E=exports,
            C_d_l=np.array(d.gva_shares) * exports,
            C_l=exports,
            Y_m=np.ones(s.G) * imports / s.G,
            Q_m=np.ones(s.G) * imports / s.G,
            Q_d_m=np.ones(s.G) * imports / s.G,
            P_m=np.ones(s.G),
            P_l=1.0,
        )

        # ── 8. Financial ──────────────────────────────────────────────────
        financial = FinancialState(
            credit_spread=mu,
            term_premium=0.010,
            fci=0.0,
        )

        state = SimulationState(
            time_index=0,
            rng_state=rng,
            origin_quarter=calib.reference_quarter,
            aggregate=aggregate,
            firms=firms,
            workers_act=workers_act,
            workers_inact=workers_inact,
            bank=bank,
            central_bank=central_bank,
            government=government,
            rotw=rotw,
            financial=financial,
            data=SimData(),
        )

        # Validate
        validator = InitializationValidator()
        result = validator.validate(state)
        result.raise_if_failed()

        return state
