from cee.core.error_correction import (
    Claim,
    CognitiveErrorCorrector,
    ReasoningTrace,
)


def test_detects_divergent_answers_and_conflicting_claims():
    corrector = CognitiveErrorCorrector()
    traces = (
        ReasoningTrace("a", "yes", (Claim("trend", "up", ("s1",)),), ("s1",)),
        ReasoningTrace("b", "no", (Claim("trend", "down", ("s2",)),), ("s2",)),
    )
    codes = {item.code for item in corrector.detect(traces)}
    assert "ANSWER_DIVERGENCE" in codes
    assert "CLAIM_CONTRADICTION" in codes


def test_decodes_supported_answer_over_unsupported_answer():
    corrector = CognitiveErrorCorrector(minimum_margin=0.05)
    traces = (
        ReasoningTrace(
            "supported", "The result is 42.",
            (Claim("result", "42", ("source-1",)),),
            ("source-1",), 0.8,
        ),
        ReasoningTrace(
            "unsupported", "The result is 17.",
            (Claim("result", "17"),),
            (), 0.9,
        ),
    )
    report = corrector.decode(traces, {"source-1"})
    assert report.answer == "The result is 42."
    assert report.selected_agent == "supported"
    assert not report.abstained


def test_abstains_when_evidence_is_insufficient():
    corrector = CognitiveErrorCorrector()
    traces = (
        ReasoningTrace("a", "maybe A", confidence=0.5),
        ReasoningTrace("b", "maybe B", confidence=0.5),
    )
    report = corrector.decode(traces, set())
    assert report.abstained
    assert report.answer is None


def test_declared_errors_create_syndrome_and_penalty():
    corrector = CognitiveErrorCorrector(minimum_margin=0.01)
    traces = (
        ReasoningTrace("clean", "answer", confidence=0.8, evidence_ids=("e1",)),
        ReasoningTrace(
            "flawed", "other", confidence=0.9, evidence_ids=("e2",),
            declared_errors=("calculation failed",),
        ),
    )
    report = corrector.decode(traces, {"e1", "e2"})
    assert any(s.code == "DECLARED_ERROR" for s in report.syndromes)
    assert report.selected_agent == "clean"
