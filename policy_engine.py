"""
policy_engine.py
-----------------
Deterministic, config-driven policy checks — the part of the pipeline
that must NEVER be left to an LLM's judgment. Leave balances and expense
limits are hard numeric rules; an LLM should reason over the *outcome*
of these checks, not decide them, so approvals stay consistent and
auditable.
"""

from dataclasses import dataclass, field
from typing import List

from core.extractor import LeaveRequestInfo, ExpenseClaimInfo

# ---- Company policy config (would normally come from a DB / HR system) ----

LEAVE_POLICY = {
    "min_notice_days": {"Casual": 2, "Earned": 5, "Sick": 0, "WFH": 1, "Unpaid": 7, "Other": 3},
    "max_consecutive_days_auto_approve": 5,
}

EXPENSE_POLICY = {
    "auto_approve_limit": {
        "Travel": 500,
        "Meals": 75,
        "Accommodation": 300,
        "Client Entertainment": 150,
        "Software/Subscriptions": 200,
        "Office Supplies": 100,
        "Other": 50,
    },
    "receipt_required_above": 25,
}


@dataclass
class RuleResult:
    rule: str
    passed: bool
    detail: str


@dataclass
class PolicyCheckResult:
    rules: List[RuleResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.rules)

    @property
    def failed_rules(self) -> List[RuleResult]:
        return [r for r in self.rules if not r.passed]


def check_leave_policy(info: LeaveRequestInfo, leave_balance: float) -> PolicyCheckResult:
    """
    Apply deterministic leave rules:
      1. Sufficient leave balance for the requested type (skips for Unpaid).
      2. Minimum notice period met for the leave type (skips for Sick).
      3. Whether the duration is within the auto-approve threshold.
    """
    rules = []

    if info.leave_type != "Unpaid":
        has_balance = leave_balance >= info.total_days
        rules.append(RuleResult(
            rule="Sufficient leave balance",
            passed=has_balance,
            detail=f"Requested {info.total_days} day(s); balance available: {leave_balance} day(s).",
        ))
    else:
        rules.append(RuleResult(
            rule="Sufficient leave balance",
            passed=True,
            detail="Unpaid leave — balance check not applicable.",
        ))

    required_notice = LEAVE_POLICY["min_notice_days"].get(info.leave_type, 3)
    notice_ok = info.leave_type == "Sick" or info.notice_days_given >= required_notice
    rules.append(RuleResult(
        rule="Minimum notice period",
        passed=notice_ok,
        detail=f"{required_notice} day(s) notice required for {info.leave_type} leave; "
               f"{info.notice_days_given} day(s) given.",
    ))

    within_auto_limit = info.total_days <= LEAVE_POLICY["max_consecutive_days_auto_approve"]
    rules.append(RuleResult(
        rule="Within auto-approve duration threshold",
        passed=within_auto_limit,
        detail=f"Auto-approve threshold is {LEAVE_POLICY['max_consecutive_days_auto_approve']} day(s); "
               f"requested {info.total_days} day(s).",
    ))

    return PolicyCheckResult(rules=rules)


def check_expense_policy(info: ExpenseClaimInfo) -> PolicyCheckResult:
    """
    Apply deterministic expense rules:
      1. Amount within the category's auto-approve limit.
      2. Receipt provided if the amount is above the receipt-required threshold.
    """
    rules = []

    limit = EXPENSE_POLICY["auto_approve_limit"].get(info.category, EXPENSE_POLICY["auto_approve_limit"]["Other"])
    within_limit = info.amount <= limit
    rules.append(RuleResult(
        rule="Within category auto-approve limit",
        passed=within_limit,
        detail=f"{info.category} limit is {info.currency} {limit}; claimed {info.currency} {info.amount}.",
    ))

    receipt_needed = info.amount > EXPENSE_POLICY["receipt_required_above"]
    receipt_ok = (not receipt_needed) or info.has_receipt
    rules.append(RuleResult(
        rule="Receipt provided when required",
        passed=receipt_ok,
        detail=(
            f"Receipt required above {info.currency} {EXPENSE_POLICY['receipt_required_above']}; "
            f"{'provided' if info.has_receipt else 'not provided'}."
        ),
    ))

    return PolicyCheckResult(rules=rules)
