from app.services.reporting import clean_report_text, parse_openai_report


def test_clean_report_text_strips_markdown() -> None:
    assert clean_report_text("### **Executive Summary**") == "Executive Summary"
    assert clean_report_text("1. **Immediate Stop/Correct**") == "Immediate Stop/Correct"


def test_parse_openai_report_extracts_summary_and_actions() -> None:
    title, summary, actions = parse_openai_report(
        """
        ### Executive Summary
        **PPE compliance is 0%** for required items helmet and vest.
        ### Action Items
        1. **Immediate Stop/Correct**
        2. Supervisor to halt the activity until a helmet is worn.
        3. Re-scan the zone after corrective action.
        """
    )
    assert title == "Executive Summary"
    assert "PPE compliance is 0%" in summary
    assert len(actions) == 3
