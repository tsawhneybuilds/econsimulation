"""USInitializer: builds SimulationState from CalibrationBundle + ObservedDataset."""
from __future__ import annotations

import numpy as np
from types import SimpleNamespace

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
        obs_data: ObservedDataset | None = None,
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
        observed = self._extract_observed_targets(calib, obs_data)

        # ── 1. Aggregate ──────────────────────────────────────────────────
        Y_0 = observed.Y_0
        scale = Y_0 / max(d.Y_0, 1e-9)
        r_bar_0 = observed.fed_funds_rate_annual_0 / 4.0

        aggregate = AggregateState(
            Y=Y_0,
            Y_real=Y_0,
            pi_=0.005,           # ~2% annual = 0.5% quarterly
            P_bar=observed.P_bar_0,
            P_bar_HH=observed.P_bar_0,
            P_bar_CF=observed.P_bar_0,
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

        alpha_bar_base = np.array([s.alpha_bar[g] for g in G_i])
        beta_i = np.array([s.beta[g] for g in G_i])
        kappa_i = np.array([s.kappa[g] for g in G_i])
        delta_i = np.array([s.delta[g] for g in G_i])
        tau_Y_i = np.array([s.tau_Y[g] for g in G_i])
        tau_K_i = np.array([s.tau_K_sect[g] for g in G_i])

        # Scale output per firm to aggregate GDP
        gva_shares = np.array([d.gva_shares[g] for g in G_i])
        gva_shares /= gva_shares.sum()
        Y_i = gva_shares * Y_0  # per firm share of GDP (bn USD)

        P_i = np.ones(I)
        Q_i = Y_i.copy()
        # K such that delta*K ≈ I_0 (replacement investment matches calibrated total)
        K_i = Y_i * (d.I_0 / Y_0) / np.maximum(delta_i, 0.01)
        L_i = K_i * 0.4   # leverage ~40% of capital
        D_i = Y_i * 0.5
        E_i = K_i - L_i
        # Scale N_i so total firm employment ≈ H_employed
        H_act = s.H_act
        H_employed = int(H_act * (1 - observed.unemployment_rate_0))

        # Distribute workers proportional to firm output
        N_shares = Y_i / Y_i.sum()
        N_i = np.maximum(1, (N_shares * H_employed).astype(int))
        diff = H_employed - N_i.sum()
        if diff > 0:
            largest = np.argsort(-Y_i)[:diff]
            N_i[largest] += 1

        # Derive alpha_bar_i (labour productivity) so production = Y_i
        # Leontief: Y = min(alpha*N, kappa*K, M/beta) → need alpha*N >= Y_i
        alpha_bar_i = (Y_i / np.maximum(N_i, 1)) * (1 + rng.normal(0, 0.02, I))

        # Wage per worker consistent with production
        w_bar_i = Y_i * 0.55 / np.maximum(N_i, 1)  # ~55% labour share

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
            C_h_i=Y_i * 0.06,
            I_h_i=Y_i * 0.01,
            K_h_i=Y_i * 0.08,
            D_h_i=Y_i * 0.05,
        )

        # ── 3. Workers ────────────────────────────────────────────────────
        H_inact = s.H_inact
        H_unemployed = H_act - H_employed

        # Base wage: labour share (~55%) of GDP spread across employed workers
        w_base = Y_0 * 0.55 / max(H_employed, 1)
        w_h_act = rng.lognormal(np.log(w_base), 0.3, H_act)
        O_h_act = np.zeros(H_act, dtype=int)
        # Assign employed workers to firms (1-indexed: 0=unemployed)
        firm_slots = np.repeat(np.arange(I), np.maximum(N_i, 0)) + 1
        rng.shuffle(firm_slots)
        assigned = min(H_employed, len(firm_slots))
        O_h_act[:assigned] = firm_slots[:assigned]

        Y_h_act = np.where(
            O_h_act > 0,
            w_h_act * (1 - s.tau_SIW - s.tau_INC * (1 - s.tau_SIW)),
            w_h_act * s.theta_UB,
        )

        C_d_h_act = Y_h_act * 0.7
        I_d_h_act = Y_h_act * 0.05
        workers_act = WorkerState(
            Y_h=Y_h_act,
            D_h=d.D_H * Y_h_act,
            K_h=d.K_H * Y_h_act,
            w_h=w_h_act,
            O_h=O_h_act,
            C_d_h=C_d_h_act,
            I_d_h=I_d_h_act,
            C_h=C_d_h_act.copy(),
            I_h=I_d_h_act.copy(),
        )

        w_inact_val = rng.lognormal(np.log(w_base * 0.3), 0.3, H_inact)
        Y_h_inact = w_inact_val * 0.3
        C_d_h_inact = Y_h_inact * 0.5
        workers_inact = WorkerState(
            Y_h=Y_h_inact,
            D_h=d.D_H * Y_h_inact,
            K_h=d.K_H * Y_h_inact,
            w_h=w_inact_val,
            O_h=np.full(H_inact, -1, dtype=int),
            C_d_h=C_d_h_inact,
            I_d_h=np.zeros(H_inact),
            C_h=C_d_h_inact.copy(),
            I_h=np.zeros(H_inact),
        )

        # ── 4. Bank ───────────────────────────────────────────────────────
        mu = sp.mu
        E_k = d.E_k * scale
        Pi_k = mu * L_i.sum() + r_bar_0 * E_k
        bank_Y_h = Pi_k * 0.55 * 0.79  # dividends after tax
        bank = BankState(
            E_k=E_k,
            Pi_k=Pi_k,
            Pi_e_k=Pi_k,
            D_k=D_i.sum() + E_k - L_i.sum(),
            r=r_bar_0 + mu,
            Y_h=bank_Y_h,
            C_d_h=bank_Y_h * 0.6,
            I_d_h=bank_Y_h * 0.05,
            C_h=bank_Y_h * 0.6,
            I_h=bank_Y_h * 0.05,
        )

        # ── 5. Central Bank ───────────────────────────────────────────────
        central_bank = CentralBankState(
            r_bar=r_bar_0,
            r_G=max(r_bar_0 + 0.0015, 0.0),  # coarse term spread over policy rate
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
        C_d_j = np.array(d.gva_shares) * observed.G_0
        government = GovernmentState(
            Y_G=0.0,
            C_G=observed.G_0,
            L_G=d.L_G * scale,
            sb_inact=sb_inact,
            sb_other=sb_other,
            C_d_j=C_d_j,
            C_j=observed.G_0,
            P_j=observed.P_bar_0,
        )

        # ── 7. ROW ────────────────────────────────────────────────────────
        exports = abs(observed.NX_0) * 0.7 + observed.I_0 * 0.05
        imports = exports - observed.NX_0
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
            D_RoW=observed.NX_0 * 4.0,
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
            fci=observed.fci_0,
        )

        state = SimulationState(
            time_index=0,
            rng_state=rng,
            origin_quarter=observed.origin_quarter,
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

        self._normalize_expenditure(
            state,
            SimpleNamespace(C_0=observed.C_0, I_0=observed.I_0),
        )

        # Validate
        validator = InitializationValidator()
        result = validator.validate(state)
        result.raise_if_failed()

        return state

    @staticmethod
    def _extract_observed_targets(
        calib: CalibrationBundle,
        obs_data: ObservedDataset | None,
    ) -> SimpleNamespace:
        """Resolve observed initialization targets from the dataset when available."""
        d = calib.initial_distributions
        mapping = calib.mapping

        if obs_data is None or obs_data.n_periods == 0:
            return SimpleNamespace(
                Y_0=d.Y_0,
                C_0=d.C_0,
                I_0=d.I_0,
                G_0=d.G_0,
                NX_0=d.NX_0,
                unemployment_rate_0=d.unemployment_rate_0,
                fed_funds_rate_annual_0=0.0155,
                fci_0=0.0,
                P_bar_0=d.P_bar_0,
                origin_quarter=calib.reference_quarter,
            )

        y_0 = obs_data.latest_value("GDPC1", d.Y_0) or d.Y_0
        c_0 = obs_data.latest_value("PCECC96", d.C_0) or d.C_0
        resid_0 = obs_data.latest_value("PRFI", d.I_0 * mapping.I_resid_share)
        i_0 = max(resid_0 / max(mapping.I_resid_share, 1e-9), resid_0)
        unemployment_rate_0 = (
            (obs_data.latest_value("UNRATE", d.unemployment_rate_0 * 100.0) or 0.0) / 100.0
        )
        fed_funds_rate_annual_0 = (
            (obs_data.latest_value("FEDFUNDS", 1.55) or 0.0) / 100.0
        )
        fci_0 = obs_data.latest_value("FCI", 0.0) or 0.0
        origin_period = (
            obs_data.latest_period("GDPC1")
            or obs_data.latest_period("PCECC96")
            or obs_data.latest_period()
        )
        scale = y_0 / max(d.Y_0, 1e-9)

        return SimpleNamespace(
            Y_0=y_0,
            C_0=c_0,
            I_0=i_0,
            G_0=d.G_0 * scale,
            NX_0=d.NX_0 * scale,
            unemployment_rate_0=unemployment_rate_0,
            fed_funds_rate_annual_0=fed_funds_rate_annual_0,
            fci_0=fci_0,
            P_bar_0=d.P_bar_0,
            origin_quarter=str(origin_period) if origin_period is not None else calib.reference_quarter,
        )

    @staticmethod
    def _normalize_expenditure(state: SimulationState, d) -> None:
        """
        Scale household consumption and investment so the expenditure-side GDP
        C + I + G + NX matches the calibrated Y_0.
        """
        w_act = state.workers_act
        w_inact = state.workers_inact
        firms = state.firms
        bank = state.bank

        # Current totals
        C_now = (w_act.C_h.sum() + w_inact.C_h.sum()
                 + firms.C_h_i.sum() + bank.C_h)
        I_res_now = (w_act.I_h.sum() + w_inact.I_h.sum()
                     + firms.I_h_i.sum() + bank.I_h)
        I_bus_now = firms.I_i.sum()

        # Scale consumption to match C_0
        if C_now > 0:
            c_scale = d.C_0 / C_now
            w_act.C_h *= c_scale
            w_act.C_d_h *= c_scale
            w_inact.C_h *= c_scale
            w_inact.C_d_h *= c_scale
            firms.C_h_i *= c_scale
            firms.C_d_h_i *= c_scale
            bank.C_h *= c_scale
            bank.C_d_h *= c_scale

        # Scale investment to match I_0
        I_total_now = I_res_now + I_bus_now
        if I_total_now > 0:
            i_scale = d.I_0 / I_total_now
            w_act.I_h *= i_scale
            w_act.I_d_h *= i_scale
            w_inact.I_h *= i_scale
            w_inact.I_d_h *= i_scale
            firms.I_h_i *= i_scale
            firms.I_d_h_i *= i_scale
            firms.I_i *= i_scale
            firms.I_d_i *= i_scale
            bank.I_h *= i_scale
            bank.I_d_h *= i_scale

        # Also scale incomes to be consistent with consumption levels
        Y_act_total = w_act.Y_h.sum()
        C_act_target = w_act.C_h.sum() + w_act.I_h.sum()
        if Y_act_total > 0 and C_act_target > 0:
            y_scale = (C_act_target / 0.75) / Y_act_total  # spending ≈ 75% of income
            w_act.Y_h *= y_scale
            w_act.w_h *= y_scale

        Y_inact_total = w_inact.Y_h.sum()
        C_inact_target = w_inact.C_h.sum()
        if Y_inact_total > 0 and C_inact_target > 0:
            y_scale = (C_inact_target / 0.50) / Y_inact_total
            w_inact.Y_h *= y_scale
            w_inact.w_h *= y_scale
