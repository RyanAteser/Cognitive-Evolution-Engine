from cee.adapters.base import DomainDefinition
from cee.core.schemas import Task

class GeneralResearchAdapter:
    definition = DomainDefinition("general", "General analytical and research tasks.",
        ["rubric_score", "factual_support", "uncertainty_handling"],
        ["Do not reward verbosity or unsupported confidence."])
    def build_task(self, prompt: str, metadata=None):
        return Task("general-task", "general", prompt, metadata or {})
    def score(self, task, output):
        # Require a task-specific rubric; do not invent accuracy metrics.
        return 0.0, {"requires_external_rubric": 1.0}
