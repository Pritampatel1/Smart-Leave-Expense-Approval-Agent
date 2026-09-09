"""
decision_agent.py
------------------
The "reasoning" layer. It never re-decides the hard numeric rules —
those already ran in policy_engine.py — it explains the outcome in
plain language and makes the final call:

  - Auto-Approve   : all policy rules passed
  - Reject         : a hard rule failed with no reasonable exception
  - Escalate       : borderline case that needs a human manager's judgment

Separating deterministic rule-checking from LLM reasoning keeps the
agent auditable: you can always see *why* a request was flagged before
trusting the verdict, and a rule failure can never be silently
overridden by the model.
"""

from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.policy_engine import PolicyCheckResult


class DecisionResult(BaseModel):
    verdict: str = Field(description="One of: Auto-Approve, Reject, Escalate")
    justification: str = Field(description="2-3 sentence plain-language explanation of the decision")
    conditions: List[str] = Field(
        default_factory=list,
        description="Any conditions the employee/manager should note (e.g. 'attach receipt before payout'). Empty list if none.",
    )


_DECISION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a fair, consistent approval agent for a company's leave and expense "
            "workflow. You are given a set of policy rule check results that have ALREADY "
            "been computed deterministically — you must NOT contradict them or invent new "
            "numeric limits. Your job is to:\n"
            "1. Decide 'Auto-Approve' only if every rule passed.\n"
            "2. Decide 'Reject' if a rule failed for a reason that is clearly outside policy "
            "and there is no ambiguity (e.g. duration far over threshold with weak reason).\n"
            "3. Decide 'Escalate' if a rule failed but the case is borderline or context makes "
            "it reasonable for a human manager to review (e.g. missed notice by 1 day for a "
            "genuine family reason).\n"
            "Be concise, neutral, and never invent facts not present in the input. "
            "{format_instructions}",
        ),
        (
            "human",
            "Request summary:\n{request_summary}\n\n"
            "Policy rule results:\n{rule_results}",
        ),
    ]
)


def _format_rules(check: PolicyCheckResult) -> str:
    lines = []
    for r in check.rules:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"- [{status}] {r.rule}: {r.detail}")
    return "\n".join(lines)


def get_decision(request_summary: str, check: PolicyCheckResult, model: str = "gpt-4o-mini") -> DecisionResult:
    """
    Ask the LLM to turn a set of already-computed policy rule results into
    a final human-readable verdict. Works for both leave and expense flows —
    both feed in a plain-text summary of the request plus the rule results.
    """
    parser = PydanticOutputParser(pydantic_object=DecisionResult)
    llm = ChatOpenAI(model=model, temperature=0)
    chain = _DECISION_PROMPT | llm | parser

    return chain.invoke(
        {
            "request_summary": request_summary,
            "rule_results": _format_rules(check),
            "format_instructions": parser.get_format_instructions(),
        }
    )
