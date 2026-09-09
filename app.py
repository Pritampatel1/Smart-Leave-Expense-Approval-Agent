"""
app.py
------
Streamlit front-end for the Smart Leave & Expense Approval Agent.

Flow:
  1. User picks Leave Request or Expense Claim, and pastes the request
     in plain English (plus a couple of context fields).
  2. extractor pulls structured fields out of the free text (LLM).
  3. policy_engine runs deterministic, config-driven company rules
     against those fields (no LLM — pure logic).
  4. decision_agent (LLM) turns the rule results into a final verdict:
     Auto-Approve / Reject / Escalate, with a plain-language reason.
  5. Everything is rendered as a clean, approver-friendly report.

Run with:  streamlit run app.py
"""

import os
import streamlit as st
from dotenv import load_dotenv

from core.extractor import extract_leave_request, extract_expense_claim
from core.policy_engine import check_leave_policy, check_expense_policy
from core.decision_agent import get_decision

load_dotenv()

st.set_page_config(
    page_title="Smart Leave & Expense Approval Agent",
    page_icon="🗂️",
    layout="wide",
)

VERDICT_STYLE = {
    "Auto-Approve": ("✅", "success"),
    "Reject": ("❌", "error"),
    "Escalate": ("🕵️", "warning"),
}

# ---------- Sidebar ----------
with st.sidebar:
    st.title("🗂️ Leave & Expense Agent")
    st.caption("LangChain + rules-engine + LLM reasoning")

    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Your key is used only for this session and never stored.",
    )
    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input

    st.divider()
    request_kind = st.radio("Request type", ["🌴 Leave Request", "💳 Expense Claim"])
    st.divider()
    st.markdown(
        "**How it works**\n"
        "1. Extract structured fields from free text\n"
        "2. Run deterministic company policy rules\n"
        "3. LLM reasons over the results into a verdict\n"
        "4. Auto-Approve, Reject, or Escalate to a manager"
    )
    st.divider()
    st.caption("Built with Streamlit · LangChain · OpenAI")

st.header("Smart Leave & Expense Approval Agent")

# =====================================================================
# LEAVE REQUEST FLOW
# =====================================================================
if request_kind == "🌴 Leave Request":
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📝 Leave Request")
        leave_text = st.text_area(
            "Paste the employee's request",
            height=180,
            placeholder="e.g. Hi, I'd like to take leave from Oct 10 to Oct 14 for a "
                        "family function. This is casual leave, submitting this today.",
        )

    with col2:
        st.subheader("📊 Context")
        leave_balance = st.number_input("Employee's current leave balance (days)", min_value=0.0, value=10.0, step=0.5)
        st.caption("This comes from the HR system in a real deployment — entered manually here for the demo.")

    analyze_clicked = st.button("🔍 Evaluate Leave Request", type="primary", use_container_width=True)
    st.divider()

    if analyze_clicked:
        if not os.getenv("OPENAI_API_KEY"):
            st.error("Please enter your OpenAI API key in the sidebar first.")
        elif not leave_text.strip():
            st.error("Please paste the leave request text.")
        else:
            try:
                with st.spinner("Extracting request details with LLM..."):
                    info = extract_leave_request(leave_text)

                with st.spinner("Running policy checks..."):
                    check = check_leave_policy(info, leave_balance)

                summary = (
                    f"{info.employee_name} requested {info.total_days} day(s) of {info.leave_type} leave "
                    f"from {info.start_date} to {info.end_date}. Reason: {info.reason}. "
                    f"Notice given: {info.notice_days_given} day(s)."
                )

                with st.spinner("Reasoning over the result..."):
                    decision = get_decision(summary, check)

                st.success("Evaluation complete!")

                icon, style = VERDICT_STYLE.get(decision.verdict, ("ℹ️", "info"))
                getattr(st, style)(f"{icon} **{decision.verdict}** — {decision.justification}")

                if decision.conditions:
                    st.markdown("**Conditions:**")
                    for c in decision.conditions:
                        st.markdown(f"- {c}")

                st.divider()
                profile_col, rules_col = st.columns(2)

                with profile_col:
                    st.subheader("👤 Extracted Request")
                    st.markdown(f"**Employee:** {info.employee_name}")
                    st.markdown(f"**Leave type:** {info.leave_type}")
                    st.markdown(f"**Dates:** {info.start_date} → {info.end_date}")
                    st.markdown(f"**Total days:** {info.total_days}")
                    st.markdown(f"**Notice given:** {info.notice_days_given} day(s)")
                    st.markdown(f"**Reason:** {info.reason}")

                with rules_col:
                    st.subheader("📋 Policy Rule Checks")
                    for r in check.rules:
                        mark = "✅" if r.passed else "❌"
                        st.markdown(f"{mark} **{r.rule}**")
                        st.caption(r.detail)

            except Exception as e:
                st.error(f"Something went wrong: {e}")
    else:
        st.info("Paste a leave request and set the leave balance, then click **Evaluate Leave Request**.")

# =====================================================================
# EXPENSE CLAIM FLOW
# =====================================================================
else:
    st.subheader("💳 Expense Claim")
    expense_text = st.text_area(
        "Paste the employee's expense claim",
        height=180,
        placeholder="e.g. Submitting a client dinner expense of $180 for the Acme project, "
                    "receipt attached, category is client entertainment.",
    )

    analyze_clicked = st.button("🔍 Evaluate Expense Claim", type="primary", use_container_width=True)
    st.divider()

    if analyze_clicked:
        if not os.getenv("OPENAI_API_KEY"):
            st.error("Please enter your OpenAI API key in the sidebar first.")
        elif not expense_text.strip():
            st.error("Please paste the expense claim text.")
        else:
            try:
                with st.spinner("Extracting claim details with LLM..."):
                    info = extract_expense_claim(expense_text)

                with st.spinner("Running policy checks..."):
                    check = check_expense_policy(info)

                summary = (
                    f"{info.employee_name} claimed {info.currency} {info.amount} for {info.category} "
                    f"({info.description}). Project: {info.project_code or 'N/A'}. "
                    f"Receipt provided: {info.has_receipt}."
                )

                with st.spinner("Reasoning over the result..."):
                    decision = get_decision(summary, check)

                st.success("Evaluation complete!")

                icon, style = VERDICT_STYLE.get(decision.verdict, ("ℹ️", "info"))
                getattr(st, style)(f"{icon} **{decision.verdict}** — {decision.justification}")

                if decision.conditions:
                    st.markdown("**Conditions:**")
                    for c in decision.conditions:
                        st.markdown(f"- {c}")

                st.divider()
                profile_col, rules_col = st.columns(2)

                with profile_col:
                    st.subheader("🧾 Extracted Claim")
                    st.markdown(f"**Employee:** {info.employee_name}")
                    st.markdown(f"**Category:** {info.category}")
                    st.markdown(f"**Amount:** {info.currency} {info.amount}")
                    st.markdown(f"**Project code:** {info.project_code or 'N/A'}")
                    st.markdown(f"**Receipt provided:** {'Yes' if info.has_receipt else 'No'}")
                    st.markdown(f"**Description:** {info.description}")

                with rules_col:
                    st.subheader("📋 Policy Rule Checks")
                    for r in check.rules:
                        mark = "✅" if r.passed else "❌"
                        st.markdown(f"{mark} **{r.rule}**")
                        st.caption(r.detail)

            except Exception as e:
                st.error(f"Something went wrong: {e}")
    else:
        st.info("Paste an expense claim, then click **Evaluate Expense Claim**.")
