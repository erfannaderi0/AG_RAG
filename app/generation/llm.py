# app/generation/llm.py
"""
Generation step: takes retrieved chunks + a question, returns an answer
from Groq.

Uses langchain_groq.ChatGroq rather than the raw groq SDK — the rest of
this project is already built on LangChain primitives (Document,
text splitters, HuggingFaceEmbeddings) and graph/ will be LangGraph, so
a LangChain chat model is the natural fit for what comes next, rather
than a bespoke provider wrapper.

No RAG-specific error handling here (mirrors retrieval/pipeline.py's
"fail loudly" stance) beyond retrying on Groq's free-tier rate limits,
which are easy to hit even during normal dev/testing and are worth
absorbing automatically rather than crashing the whole pipeline on.
"""

import logging
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
from app.generation.prompts import answer_prompt, format_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model_name,
    temperature=settings.groq_temperature,
    max_tokens=settings.groq_max_tokens,
)

_chain = answer_prompt | _llm


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _invoke(question: str, context: str) -> str:
    response = _chain.invoke({"question": question, "context": context})
    return response.content


def generate(question: str, documents: list[Document]) -> str:
    """
    Generate an answer to `question` grounded in `documents` (the output
    of retrieval.pipeline.retrieve). Retries automatically on Groq
    rate-limit errors; any other failure propagates.
    """
    context = format_context(documents)
    answer = _invoke(question, context)

    logger.info(
        "generate: question=%r -> %d context docs, %d char answer",
        question, len(documents), len(answer),
    )

    return answer


if __name__ == "__main__":
    from app.retrieval.pipeline import retrieve

    q = "business expense meals"
    docs = retrieve(q)
    print(generate(q, docs))
