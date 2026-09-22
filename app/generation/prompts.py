# app/generation/prompts.py
"""
Prompt templates for the generation step.

Scope is deliberately narrow: this file only holds the prompt that turns
(retrieved context + question) into an answer. Guardrail prompts (input
screening, groundedness/hallucination checks, etc.) belong in the
guardrails/ module, not here — they're a separate pipeline stage with a
different lifecycle and possibly a different, cheaper model.
"""

from langchain_core.prompts import ChatPromptTemplate

ANSWER_SYSTEM_PROMPT = """You are an assistant answering questions using only the provided context.

Rules:
- Answer using only information found in the context below. Do not use outside knowledge.
- If the context does not contain enough information to answer, say so plainly instead of guessing.
- Be concise and direct. Do not repeat the question back.
- When helpful, mention which source the information came from (the context includes source metadata)."""

ANSWER_USER_PROMPT = """Context:
{context}

Question: {question}

Answer:"""

answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", ANSWER_SYSTEM_PROMPT),
        ("human", ANSWER_USER_PROMPT),
    ]
)


def format_context(documents) -> str:
    """
    Turns a list of LangChain Documents (as returned by retrieval.pipeline.retrieve)
    into a single context string for the answer prompt, tagging each chunk with
    its source so the model can cite it if asked to.
    """
    blocks = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source") or doc.metadata.get("title") or f"doc_{i}"
        blocks.append(f"[{i}] (source: {source})\n{doc.page_content}")
    return "\n\n".join(blocks)
