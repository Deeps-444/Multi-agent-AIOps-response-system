"""Log Investigation Agent – investigates error patterns, timeouts, and exceptions."""

from app.incident_tools import inspect_logs
from app.models import EvidenceFinding, IncidentInput


def investigate_logs(incident: IncidentInput) -> EvidenceFinding:
    """
    Investigate logs for the given incident.

    Uses the deterministic tool and adds rule-based hypotheses.
    Explicitly handles missing logs and weak evidence so the
    orchestrator can decide whether to gather more data.
    """
    finding = inspect_logs(incident)

    hypotheses: list[str] = []
    evidence_text = " ".join(finding.evidence).lower()

    if not finding.evidence:
        observation = (
            "No error-related log lines found in the supplied sample. "
            "Evidence is currently insufficient to support a log-based root cause."
        )
        next_step = "Request a wider log time window or additional log sources."
    else:
        if "timeout" in evidence_text or "database connection" in evidence_text:
            hypotheses.append("Database connection acquisition failures / pool pressure")
        if "failed to create order" in evidence_text:
            hypotheses.append("Order creation failing due to downstream DB issues")
        if "exception" in evidence_text:
            hypotheses.append("Unhandled exception path contributing to errors")

        observation = finding.observation
        if hypotheses:
            observation += f" Possible causes: {'; '.join(hypotheses)}."
        else:
            observation += " Error signals present but no strong pattern matched yet."

        next_step = (
            finding.suggested_next_step
            or "Correlate these log findings with metrics and recent deployment timeline."
        )

    return EvidenceFinding(
        source="log_agent",
        observation=observation,
        evidence=finding.evidence,
        suggested_next_step=next_step,
    )
