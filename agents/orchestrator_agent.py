"""Master Orchestrator Agent: plan, execute, review, and expose trace."""
from .shared_agent import review, run_pipeline

__all__ = ["review", "run_pipeline"]
