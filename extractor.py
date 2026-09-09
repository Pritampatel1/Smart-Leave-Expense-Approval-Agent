"""
extractor.py
------------
Uses an LLM (via LangChain) to turn an employee's free-text leave or
expense request into a clean, structured object. This is the
"understanding" layer of the pipeline — employees phrase requests very
differently ("need 3 days off for a wedding", "taking Fri-Mon for a
family emergency"), so plain regex can't reliably pull out dates,
amounts, and categories.
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate


class LeaveRequestInfo(BaseModel):
    employee_name: str = Field(description="Employee's name if present, else 'Unknown'")
    leave_type: str = Field(description="One of: Sick, Casual, Earned, Unpaid, WFH, Other")
    start_date: str = Field(description="Start date of leave, in YYYY-MM-DD if determinable, else as written")
    end_date: str = Field(description="End date of leave, in YYYY-MM-DD if determinable, else as written")
    total_days: float = Field(description="Total number of leave days requested")
    reason: str = Field(description="Short reason given for the leave")
    notice_days_given: float = Field(
        description="How many days in advance of the start date this request was submitted. "
        "Estimate 0 if it reads as a same-day / emergency request and no other info is given."
    )


class ExpenseClaimInfo(BaseModel):
    employee_name: str = Field(description="Employee's name if present, else 'Unknown'")
    category: str = Field(description="One of: Travel, Meals, Accommodation, Client Entertainment, Software/Subscriptions, Office Supplies, Other")
    amount: float = Field(description="Claimed amount as a number, no currency symbol")
    currency: str = Field(description="Currency code, e.g. USD, INR, EUR. Default to USD if unclear")
    description: str = Field(description="Short description of what the expense was for")
    project_code: Optional[str] = Field(default=None, description="Project or client code if mentioned, else null")
    has_receipt: bool = Field(description="Whether the employee states a receipt/invoice is attached")


_LEAVE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a precise HR request-parsing assistant. Extract only information "
            "that is explicitly present or clearly implied in the request text. Do not "
            "invent details. {format_instructions}",
        ),
        ("human", "Leave request text:\n\n{request_text}"),
    ]
)

_EXPENSE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a precise finance request-parsing assistant. Extract only information "
            "that is explicitly present or clearly implied in the claim text. Do not invent "
            "details. {format_instructions}",
        ),
        ("human", "Expense claim text:\n\n{request_text}"),
    ]
)


def extract_leave_request(request_text: str, model: str = "gpt-4o-mini") -> LeaveRequestInfo:
    """Run leave request text through an LLM to get a structured LeaveRequestInfo."""
    parser = PydanticOutputParser(pydantic_object=LeaveRequestInfo)
    llm = ChatOpenAI(model=model, temperature=0)
    chain = _LEAVE_PROMPT | llm | parser
    return chain.invoke(
        {"request_text": request_text, "format_instructions": parser.get_format_instructions()}
    )


def extract_expense_claim(request_text: str, model: str = "gpt-4o-mini") -> ExpenseClaimInfo:
    """Run expense claim text through an LLM to get a structured ExpenseClaimInfo."""
    parser = PydanticOutputParser(pydantic_object=ExpenseClaimInfo)
    llm = ChatOpenAI(model=model, temperature=0)
    chain = _EXPENSE_PROMPT | llm | parser
    return chain.invoke(
        {"request_text": request_text, "format_instructions": parser.get_format_instructions()}
    )
