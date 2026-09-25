from laya_voice_browser_win.policy import evaluate
from laya_voice_browser_win.types import Element, ModelDecision, Snapshot


def snapshot(*elements):
    return Snapshot("https://example.com", "Example", "Example page", tuple(elements), "fingerprint")


def choice(selected, probabilities, confidence=0.9):
    return {"type": "choice", "choice": selected, "probabilities": probabilities, "confidence": confidence}


def base_answers(intent):
    return {
        "intent": choice(intent, {intent: 0.95, "none": 0.05}),
        "site": choice("none", {"none": 0.9, "google": 0.1}),
        "complete": {"type": "noul", "noul": 0.97, "confidence": 0.97},
        "is_command": {"type": "noul", "noul": 0.98, "confidence": 0.98},
        "destructive": {"type": "noul", "noul": 0.02, "confidence": 0.98},
        "scroll_amount": {"type": "score", "score": 1.0},
        "tab_direction": choice("none", {"none": 0.8, "next": 0.2}),
    }


def test_safe_closed_action_can_run_on_partial_speech():
    answers = base_answers("go_back")
    decision = ModelDecision(answers, {"text": [], "url": []}, 8.0, "test", {"transcript": "take me back"})
    result = evaluate(decision, snapshot(), final=False, silent_seconds=0.1)
    assert result.verdict == "act"
    assert result.action == {"type": "back"}


def test_explicit_site_name_overrides_weak_model_site_head():
    answers = base_answers("navigate_url")
    answers["site"] = choice("google", {"google": 0.56, "wikipedia": 0.28, "none": 0.16})
    decision = ModelDecision(
        answers,
        {"text": [], "url": []},
        8.0,
        "test",
        {"transcript": "go to wikipedia"},
    )
    result = evaluate(decision, snapshot(), final=False, silent_seconds=0.1)
    assert result.verdict == "act"
    assert result.action == {"type": "navigate", "url": "https://en.wikipedia.org/wiki/Main_Page"}


def test_open_amazon_cannot_be_rerouted_by_the_model_site_head():
    answers = base_answers("navigate_url")
    answers["site"] = choice("github", {"github": 0.6, "amazon": 0.3, "none": 0.1})
    decision = ModelDecision(
        answers,
        {"text": [], "url": []},
        8.0,
        "test",
        {"transcript": "open Amazon"},
    )
    result = evaluate(decision, snapshot(), final=True, silent_seconds=1.0)
    assert result.verdict == "act"
    assert result.action == {"type": "navigate", "url": "https://www.amazon.com/"}
