# app/graph/state.py

from typing import TypedDict

from langchain_core.documents import Document


class AgRagState(TypedDict):
    # --- entry ---
    query: str

    # --- input guardrail (screen_input node) ---
    allowed: bool | None
    input_reason: str | None
    refusal_message: str | None

    # --- retrieval ---
    documents: list[Document]

    # --- generation ---
    answer: str | None

    # --- output guardrail (screen_output node) ---
    passed: bool | None
    output_reason: str | None
    final_answer: str | None
