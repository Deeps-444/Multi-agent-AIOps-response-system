"""Metrics Investigation Agent – interprets latency, error rate, CPU, and DB pool signals."""

from app.incident_tools import inspect_metrics
from app.models import EvidenceFinding, IncidentInput


def investigate_metrics(incident: IncidentInput) -> EvidenceFinding:
    """
    Investigate metrics for the given incident.

    Uses the deterministic tool and adds rule-based hypotheses.
    Explicitly surfaces missing metrics and mixed signals so the
    orchestrator can request further investigation when evidence conflicts.
    """
    finding = inspect_metrics(incident)

    hypotheses: list[str] = []
    evidence_text = " ".join(finding.evidence).lower()
    has_pool = "database connection pool" in evidence_text
    has_latency = "latency" in evidence_text
    has_5xx = "5xx" in evidence_text
    has_cpu = "cpu" in evidence_text

    if not finding.evidence:
        observation = (
            "No supplied metric crossed the starter thresholds. "
            "Either the service is healthy on these signals or key metrics are missing."
        )
        next_step = "Verify whether required metrics are present and thresholds are appropriate."
    else:
        if has_pool:
            hypotheses.append("Database connection pool near exhaustion")
        if has_latency:
            hypotheses.append("Elevated p95 latency indicating slow downstream calls")
        if has_5xx:
            hypotheses.append("High HTTP 5xx rate – service is returning errors")
        if has_cpu:
            hypotheses.append("High CPU usage on the service")

        observation = finding.observation
        if hypotheses:
            observation += f" Supporting signals: {'; '.join(hypotheses)}."

        # Light contradiction / mixed-signal note for the orchestrator
        if has_pool and not has_latency and not has_5xx:
            observation += " Note: pool pressure is high but latency/5xx are not elevated in the current sample."
        elif (has_latency or has_5xx) and not has_pool:
            observation += " Note: error/latency signals present without clear pool exhaustion."

        next_step = (
            finding.suggested_next_step
            or "Cross-check with logs and recent changes; investigate if signals conflict."
        )

    return EvidenceFinding(
        source="metrics_agent",
        observation=observation,
        evidence=finding.evidence,
        suggested_next_step=next_step,
    )
