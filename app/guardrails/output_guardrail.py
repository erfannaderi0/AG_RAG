# app/guardrails/output_guardrail.py
"""
Checks whether a generated answer is grounded in the retrieved context,
and lightly polishes it if so. Combines the post-processing step and the
response guardrail into a single Groq call (per the MVP design decision
to avoid a second full LLM pass for formatting alone).

Uses groq_guardrail_model_name (smaller/faster than generation's model).

The fixed fallback message is applied in code, not trusted from the
model's output, when grounded=False — deterministic and can't be
talked around by the model producing unexpected text in that field.
"""

import json
import logging
import re
import sys
from pathlib import Path

if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

from groq import RateLimitError
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.generation.prompts import format_context
from app.guardrails.prompts import output_guardrail_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FIXED_FALLBACK_MESSAGE = (
    "I don't have enough grounded information in the source documents to answer that confidently."
)

_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_guardrail_model_name,
    temperature=settings.groq_guardrail_temperature,
    max_tokens=settings.groq_guardrail_max_tokens,
    reasoning_effort=settings.groq_guardrail_reasoning_effort,
    reasoning_format="hidden",
)

_chain = output_guardrail_prompt | _llm


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _invoke(question: str, context: str, answer: str) -> str:
    response = _chain.invoke({"question": question, "context": context, "answer": answer})
    return response.content


def _parse_verdict(raw: str) -> dict:
    """Extracts the JSON object from the model's response. Raises if none is found."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in guardrail response: {raw!r}")
    return json.loads(match.group(0))


def check_response(question: str, answer: str, documents: list[Document]) -> tuple[bool, str]:
    """
    Returns (passed, final_answer).
    - passed=True: final_answer is the (possibly lightly polished) answer.
    - passed=False: final_answer is the fixed fallback message, regardless
      of what the model returned in that field.
    On any parsing failure, fails open (passes the original answer through
    unmodified) with a warning logged.
    """
    context = format_context(documents)
    raw = _invoke(question, context, answer)

    try:
        verdict = _parse_verdict(raw)
        grounded = bool(verdict["grounded"])
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.warning("output guardrail: failed to parse verdict (%s), failing open. raw=%r", e, raw)
        return True, answer

    logger.info("check_response: question=%r -> grounded=%s", question, grounded)

    if not grounded:
        return False, FIXED_FALLBACK_MESSAGE

    final_answer = verdict.get("final_answer") or answer
    return True, final_answer


if __name__ == "__main__":
    from app.generation.llm import generate
    from app.retrieval.pipeline import retrieve

    q = "business expense meals"
    docs = retrieve(q)
    answer = generate(q, docs)
    passed, final_answer = check_response(q, answer, docs)
    print(f"passed={passed}")
    print(final_answer)
