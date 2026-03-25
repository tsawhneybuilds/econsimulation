"""USMacroEngine: wraps the 33-step quarterly ABM transition loop."""
from __future__ import annotations

import copy
import time
from typing import Optional

from src.engine.core.state import SimulationState
from src.engine.shocks.shock_protocol import ShockProtocol, NoShock


class USMacroEngine:
    """
    U.S. Macro ABM Engine.

    Implements BeforeIT.jl's step!() order, adapted for U.S. data.
    All transitions are pure functions that mutate state in-place.
    """

    def step(
        self,
        state: SimulationState,
        shock: Optional[ShockProtocol] = None,
    ) -> SimulationState:
        """
        Execute one quarterly step of the ABM.

        Order mirrors BeforeIT.jl one_step.jl exactly:
        1.  finance_insolvent_firms
        2.  set_growth_inflation_expectations
        3.  set_epsilon (ROW shocks)
        4.  set_growth_inflation_row
        5.  set_central_bank_rate
        6.  shock (optional)
        7.  set_bank_rate
        8.  set_firms_expectations_and_decisions
        9.  search_and_matching_credit
        10. search_and_matching_labour
        11. set_firms_wages
        12. set_firms_production
        13. update_workers_wages
        14. set_gov_social_benefits
        15. set_bank_expected_profits
        16. set_households_budget_act
        17. set_households_budget_inact
        18. set_households_budget_firms
        19. set_households_budget_bank
        20. set_gov_expenditure
        21. set_rotw_import_export
        22. search_and_matching (goods market)
        23. set_inflation_priceindex
        24. set_sector_specific_priceindex
        25. set_capital_formation_priceindex
        26. set_households_priceindex
        27. set_firms_stocks
        28. set_firms_profits
        29. set_bank_profits
        30. set_bank_equity
        31. set_households_income_act/inact/firms/bank
        32. set_households_deposits_act/inact/firms/bank
        33. set_central_bank_equity / set_gov_revenues / set_gov_loans
            set_firms_deposits / set_firms_loans / set_firms_equity
            set_rotw_deposits / set_bank_deposits
            set_gross_domestic_product
            set_time
        """
        from src.engine.transitions.expectations import (
            set_growth_inflation_expectations, set_epsilon, set_growth_inflation_row,
        )
        from src.engine.transitions.central_bank import set_central_bank_rate, set_bank_rate
        from src.engine.transitions.firms import (
            set_firms_expectations_and_decisions, set_firms_wages,
            set_firms_production, set_firms_stocks, set_firms_profits,
            set_firms_deposits, set_firms_loans, set_firms_equity,
        )
        from src.engine.transitions.credit_market import search_and_matching_credit
        from src.engine.transitions.labour_market import (
            search_and_matching_labour, update_workers_wages,
        )
        from src.engine.transitions.household_budgets import (
            set_gov_social_benefits, set_bank_expected_profits,
            set_households_budget_act, set_households_budget_inact,
            set_households_budget_firms, set_households_budget_bank,
        )
        from src.engine.transitions.government import (
            set_gov_expenditure, set_gov_revenues, set_gov_loans,
        )
        from src.engine.transitions.trade import set_rotw_import_export, set_rotw_deposits
        from src.engine.transitions.goods_market import search_and_matching
        from src.engine.transitions.accounting import (
            set_inflation_priceindex, set_sector_specific_priceindex,
            set_capital_formation_priceindex, set_households_priceindex,
            set_households_income_act, set_households_income_inact,
            set_households_income_firms, set_households_income_bank,
            set_households_deposits_act, set_households_deposits_inact,
            set_households_deposits_firms, set_households_deposits_bank,
            set_bank_profits, set_bank_equity, set_bank_deposits,
            set_central_bank_equity, set_gross_domestic_product, set_time,
            finance_insolvent_firms,
        )

        if shock is None:
            shock = NoShock()

        # ── Step 1: Handle insolvent firms ──────────────────────────────
        finance_insolvent_firms(state)

        # ── Steps 2-4: Expectations and ROW update ───────────────────────
        set_growth_inflation_expectations(state)
        set_epsilon(state)
        set_growth_inflation_row(state)

        # ── Steps 5-7: Central bank and bank rates ────────────────────────
        set_central_bank_rate(state)
        shock.apply(state)        # Step 6: optional shock
        set_bank_rate(state)

        # ── Step 8: Firm decisions ─────────────────────────────────────────
        set_firms_expectations_and_decisions(state)

        # ── Steps 9-13: Credit/labour markets and production ──────────────
        search_and_matching_credit(state)
        search_and_matching_labour(state)
        set_firms_wages(state)
        set_firms_production(state)
        update_workers_wages(state)

        # ── Steps 14-19: Household budgets ─────────────────────────────────
        set_gov_social_benefits(state)
        set_bank_expected_profits(state)
        set_households_budget_act(state)
        set_households_budget_inact(state)
        set_households_budget_firms(state)
        set_households_budget_bank(state)

        # ── Steps 20-21: Government + trade ───────────────────────────────
        set_gov_expenditure(state)
        set_rotw_import_export(state)

        # ── Step 22: Goods market clearing ────────────────────────────────
        search_and_matching(state)

        # ── Steps 23-26: Price indices ────────────────────────────────────
        set_inflation_priceindex(state)
        set_sector_specific_priceindex(state)
        set_capital_formation_priceindex(state)
        set_households_priceindex(state)

        # ── Steps 27-30: Firm/bank stocks and profits ─────────────────────
        set_firms_stocks(state)
        set_firms_profits(state)
        set_bank_profits(state)
        set_bank_equity(state)

        # ── Steps 31-32: Income and deposits ──────────────────────────────
        set_households_income_act(state)
        set_households_income_inact(state)
        set_households_income_firms(state)
        set_households_income_bank(state)
        set_households_deposits_act(state)
        set_households_deposits_inact(state)
        set_households_deposits_firms(state)
        set_households_deposits_bank(state)

        # ── Step 33: Final accounting ─────────────────────────────────────
        set_central_bank_equity(state)
        set_gov_revenues(state)
        set_gov_loans(state)
        set_firms_deposits(state)
        set_firms_loans(state)
        set_firms_equity(state)
        set_rotw_deposits(state)
        set_bank_deposits(state)
        set_gross_domestic_product(state)
        set_time(state)

        return state

    def run(
        self,
        state: SimulationState,
        T: int,
        shock: Optional[ShockProtocol] = None,
    ) -> SimulationState:
        """Run T steps. Returns mutated state."""
        if shock is None:
            shock = NoShock()
        for _ in range(T):
            self.step(state, shock=shock)
        return state
