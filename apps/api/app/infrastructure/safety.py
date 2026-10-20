"""Prompt / response guards: block obvious clinical-advice patterns in LLM output."""
import re

_CLINICAL_PATTERNS = (
    re.compile(p, re.I)
    for p in (
        r"\b(take|stop|start|increase|decrease)\s+(the\s+)?(medication|medicine|dose|dosage)\b",
        r"\b(you should|patient should)\s+(take|use|avoid)\b",
        r"\b(diagnos(e|is)|prescrib(e|ed|ing))\b",
        r"\b(chemotherapy|radiation therapy|surgical intervention)\b",
    )
)

_DISCLAIMER = (
    " This is an administrative pre-submission check only — not medical advice."
)


def contains_clinical_advice(text: str) -> bool:
    return any(p.search(text) for p in _CLINICAL_PATTERNS)


def guard_analysis_fields(parsed: dict) -> dict:
    """Strip or neutralize fields that look like clinical advice; never fail the HTTP request."""
    out = dict(parsed)
    for key in ("explanation", "suggestedFix", "falsePositiveReasoning"):
        val = out.get(key)
        if isinstance(val, str) and contains_clinical_advice(val):
            out[key] = (
                "Administrative validation note only: refer to payer policy and a licensed reviewer. "
                "Automated clinical-style wording was suppressed."
                + _DISCLAIMER
            )
    return out
