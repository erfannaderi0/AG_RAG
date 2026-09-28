# app/graph/nodes.py

from app.generation.llm import generate
from app.graph.state import AgRagState
from app.guardrails.pipeline import guard_query, guard_response
from app.retrieval.pipeline import retrieve
from db.guardrail_log import log_guardrail_decision


def screen_input(state: AgRagState) -> dict:
    query = state["query"]
    allowed, reason, refusal_message = guard_query(query)

    log_guardrail_decision(query, "input", allowed, reason)

    return {
        "allowed": allowed,
        "input_reason": reason,
        "refusal_message": refusal_message,
    }


def retrieve_node(state: AgRagState) -> dict:
    documents = retrieve(state["query"])
    return {"documents": documents}


def generate_node(state: AgRagState) -> dict:
    answer = generate(state["query"], state["documents"])
    return {"answer": answer}


def screen_output(state: AgRagState) -> dict:
    passed, final_answer, reason = guard_response(
        state["query"], state["answer"], state["documents"]
    )

    log_guardrail_decision(state["query"], "output", passed, reason)

    return {
        "passed": passed,
        "output_reason": reason,
        "final_answer": final_answer,
    }
