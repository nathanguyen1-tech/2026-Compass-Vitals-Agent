"""Care Flow Graph — LangGraph orchestrator for Screening → Proposer → Critic pipeline.

Intake Agent runs separately (multi-turn chat). Once intake is complete,
this graph runs as a single-pass pipeline.
"""

from functools import partial

import structlog
from langgraph.graph import END, StateGraph

from app.agents.critic_agent import critic_node
from app.agents.proposer_agent import proposer_node
from app.agents.screening_agent import screening_node
from app.agents.state import CareFlowState
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()

MAX_CRITIC_LOOPS = 2


def route_after_critic(state: CareFlowState) -> str:
    """Conditional edge: after critic, either finish or loop back to proposer."""
    if state.get("critic_approved"):
        return END

    loops = state.get("_critic_loops", 0)
    if loops >= MAX_CRITIC_LOOPS:
        logger.warning(
            "care_flow.max_loops_reached",
            case_id=state.get("case_id"),
            loops=loops,
        )
        return END  # Stop looping — needs human review

    logger.info(
        "care_flow.critic_rejected_loop",
        case_id=state.get("case_id"),
        loop=loops,
    )
    return "proposer"


def build_care_flow_graph(
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> StateGraph:
    """Build the care flow StateGraph.

    Returns a compiled graph that runs: screening → proposer → critic
    with conditional loop back to proposer if critic rejects.
    """
    # Create partial functions that bind gateway and phi to each node
    screening = partial(screening_node, llm_gateway=llm_gateway, phi_deidentifier=phi_deidentifier)
    proposer = partial(proposer_node, llm_gateway=llm_gateway, phi_deidentifier=phi_deidentifier)
    critic = partial(critic_node, llm_gateway=llm_gateway, phi_deidentifier=phi_deidentifier)

    graph = StateGraph(CareFlowState)

    # Add nodes
    graph.add_node("screening", screening)
    graph.add_node("proposer", proposer)
    graph.add_node("critic", critic)

    # Linear edges
    graph.add_edge("screening", "proposer")
    graph.add_edge("proposer", "critic")

    # Conditional edge: critic → END or → proposer (loop)
    graph.add_conditional_edges("critic", route_after_critic)

    # Entry point
    graph.set_entry_point("screening")

    return graph.compile()
