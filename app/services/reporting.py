from __future__ import annotations

import json
import re

from openai import OpenAI

from app.core.config import settings
from app.models.schemas import ExecutiveReport, SiteSummary, WorkerCompliance


def clean_report_text(value: str) -> str:
    cleaned = value.replace("`", "")
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned.strip())
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
    cleaned = re.sub(r"^[-*]\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -:")


def parse_openai_report(text: str) -> tuple[str, str, list[str]]:
    lines = [clean_report_text(line) for line in text.splitlines() if clean_report_text(line)]
    if not lines:
        return "AI Safety Summary", "", []

    title = lines[0][:80]
    summary_candidates: list[str] = []
    actions: list[str] = []

    for line in lines[1:]:
        lowered = line.lower()
        if lowered.startswith("action item") or lowered.startswith("action items"):
            continue
        if len(actions) < 3 and (
            lowered.startswith("action")
            or lowered.startswith("immediate")
            or lowered.startswith("supervisor")
            or lowered.startswith("re-scan")
            or lowered.startswith("review")
            or lowered.startswith("halt")
        ):
            actions.append(clean_report_text(re.sub(r"^action\s*:?\s*", "", line, flags=re.IGNORECASE)))
            continue
        if not summary_candidates:
            summary_candidates.append(line)
        elif len(actions) < 3:
            actions.append(line)

    summary = summary_candidates[0] if summary_candidates else "Operational safety summary generated."
    return title, summary, actions[:3]


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
                                "You are an industrial safety analyst. Respond in plain text only, with no markdown. "
                                "Format exactly as: first line title, second line one-sentence summary, then three "
                                "action lines. Be specific, operational, and suitable for an enterprise dashboard."
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

    title, summary, actions = parse_openai_report(text)
    if not actions:
        actions = [
            "Review the flagged non-compliant workers and trigger a spot correction.",
            "Re-scan the affected zone after corrective action.",
            "Track repeat missing-item patterns for training improvements.",
        ]
    return ExecutiveReport(source="openai", title=title, summary=summary, actions=actions)
