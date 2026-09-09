# Smart Leave & Expense Approval Agent

An AI-powered approval agent that reads a plain-English leave request or
expense claim, checks it against configurable company policy rules, and
returns a clear verdict — **Auto-Approve**, **Reject**, or **Escalate** —
with a plain-language justification. Built with **LangChain**, a
**deterministic rules engine**, and **OpenAI** models, wrapped in a simple
**Streamlit** UI.

## What it does

1. **Extracts** structured fields from an employee's free-text request —
   dates, leave type, amount, category, etc. — using an LLM with a strict
   JSON output schema (`LangChain` + `Pydantic`).
2. **Checks** the extracted request against hard, config-driven company
   policy rules (leave balance, notice period, expense limits, receipt
   requirements) — pure Python logic, no LLM involved, so the numbers are
   always consistent and auditable.
3. **Reasons** over the rule results with an LLM to produce a final
   verdict and a plain-language explanation a manager or employee can
   actually understand, without ever contradicting the deterministic
   checks.
4. Displays everything — verdict, extracted fields, rule-by-rule
   breakdown — as a clean, approver-friendly report.

## Project structure

```
smart-leave-expense-agent/
├── app.py                    # Streamlit UI (entry point)
├── core/
│   ├── extractor.py          # free text → structured request (LLM)
│   ├── policy_engine.py      # deterministic company policy rules
│   └── decision_agent.py     # rule results → verdict + reasoning (LLM)
├── sample_data/
│   ├── sample_leave_request.txt
│   └── sample_expense_claim.txt
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. **Clone / copy this folder**, then create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Add your OpenAI API key.** Either:
   - Copy `.env.example` to `.env` and paste your key, **or**
   - Paste it directly into the sidebar text box when the app is running.

   Get a key at https://platform.openai.com/api-keys

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```
   It opens automatically at `http://localhost:8501`.

## Try it

- Pick **Leave Request** or **Expense Claim** in the sidebar.
- Paste the contents of `sample_data/sample_leave_request.txt` or
  `sample_data/sample_expense_claim.txt`, or write your own.
- For leave requests, set the employee's leave balance.
- Click **Evaluate**.

## How to talk about this in an interview

- **Why split extraction, policy checks, and reasoning into three
  separate modules?** It mirrors how a real approval workflow should be
  audited: you can see exactly what fields the model pulled out, exactly
  which numeric rules passed or failed, and only then how the model
  explained the outcome — three places to catch and fix a wrong decision
  instead of one opaque model call.
- **Why is the policy engine pure Python instead of an LLM prompt?**
  Leave balances and dollar limits are hard business rules. An LLM can
  paraphrase and reason about *why* a rule matters, but it should never
  be the thing computing "is 6 > 5" — that has to be deterministic so
  every employee is checked against the same numbers every time.
- **What does the LLM actually add, then?** Judgment on borderline
  cases. A rule can fail (e.g. one day short of notice) in a way that's
  still reasonable to approve or worth a manager's second look — the
  reasoning layer is what turns a rigid pass/fail into "Escalate" with a
  human-readable reason, instead of a hard reject.
- **What would you improve at scale?** Pull policy limits and leave
  balances from a real HR/finance system instead of the in-file config;
  add an audit log of every decision + rule snapshot; add a human
  approval step in the UI for anything the agent escalates rather than
  just displaying the recommendation.

## Notes

- The policy numbers in `core/policy_engine.py` (leave notice periods,
  expense category limits) are illustrative — swap in your actual
  company policy.
- Default model is `gpt-4o-mini` for cost efficiency; swap the `model`
  parameter in `core/extractor.py` / `core/decision_agent.py` for a
  stronger model if needed.
