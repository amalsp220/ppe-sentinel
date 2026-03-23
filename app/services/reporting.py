from __future__ import annotations

import json

from openai import OpenAI

from app.core.config import settings
from app.models.schemas import ExecutiveReport, SiteSummary, WorkerCompliance


def build_rule_based_report(
    filename: str,
    media_type: str,
    site_summary: SiteSummary,
    workers: list[WorkerCompliance],
    required_items: list[str],
) -> ExecutiveReport:
    if site_summary.non_compliant_workers == 0 and site_summary.total_workers > 0:
        summary = (
            f"{filename} was analyzed as a {media_type}. All {site_summary.total_workers} detected workers met "
            f"the required PPE policy for {', '.join(required_items)}."
        )
        actions = [
            "Keep this upload as a positive reference sample for shift leads.",
            "Continue periodic spot checks to make sure compliance stays above 95%.",
        ]
    else:
        missing_categories = ", ".join(site_summary.missing_items) or "multiple categories"
        summary = (
            f"{filename} shows {site_summary.non_compliant_workers} non-compliant workers out of "
            f"{site_summary.total_workers} detected. Missing PPE is concentrated in {missing_categories}."
        )
        actions = [
            "Escalate the flagged zone to the floor supervisor for an immediate PPE correction round.",
            "Capture a follow-up scan after the correction to verify the compliance rate has improved.",
            "Review induction signage near site entry points if the same missing items recur across uploads.",
        ]
    return ExecutiveReport(source="rules", title="Shift Safety Snapshot", summary=summary, actions=actions)


def build_openai_report(
    filename: str,
    media_type: str,
    site_summary: SiteSummary,
    workers: list[WorkerCompliance],
    required_items: list[str],
) -> ExecutiveReport:
    if not settings.openai_api_key:
        return build_rule_based_report(filename, media_type, site_summary, workers, required_items)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        payload = {
            "filename": filename,
            "media_type": media_type,
            "required_items": required_items,
            "site_summary": site_summary.model_dump(),
            "workers": [worker.model_dump() for worker in workers],
        }
        response = client.responses.create(
            model=settings.openai_model,
            max_output_tokens=500,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are an industrial safety analyst. Write a concise executive summary plus 3 "
                                "action items. Be specific, operational, and suitable for an enterprise dashboard."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": json.dumps(payload, indent=2)}],
                },
            ],
        )
        text = (response.output_text or "").strip()
    except Exception:
        return build_rule_based_report(filename, media_type, site_summary, workers, required_items)

    if not text:
        return build_rule_based_report(filename, media_type, site_summary, workers, required_items)

    lines = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
    title = lines[0][:80] if lines else "AI Safety Summary"
    summary = lines[1] if len(lines) > 1 else text
    actions = [line for line in lines[2:5]]
    if not actions:
        actions = [
            "Review the flagged non-compliant workers and trigger a spot correction.",
            "Re-scan the affected zone after corrective action.",
            "Track repeat missing-item patterns for training improvements.",
        ]
    return ExecutiveReport(source="openai", title=title, summary=summary, actions=actions)
