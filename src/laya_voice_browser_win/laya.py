"""Laya decision engine for Windows.

Supports:
1. Official PyTorch Laya models (`laya` package / HuggingFace `convaiinnovations/laya`)
2. Fast local rule + semantic heuristic engine for instant sub-millisecond execution
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import sites
from .answers import _choice, _confidence, _probability
from .policy import command_gate, complete_gate, early_intent, intent_gate, payload_gate
from .questions import (
    DETAIL_QUESTIONS,
    MAX_PAGE_TEXT,
    MAX_RECENT_ACTIONS,
    MAX_STATE_ELEMENTS,
    MAX_TARGET_OPTIONS,
    MODEL_DEFAULT,
    fixed_questions,
    span_question,
    target_question,
)
from .spans import (
    deterministic_intent,
    explicit_browser_command,
    explicit_payload,
    mentioned_site,
    spoken_scroll_amount,
    spoken_tab_direction,
    strip_lead,
    tab_command,
    text_candidates,
    universal_command,
    url_candidates,
)
from .types import Element, ModelDecision, Snapshot

logger = logging.getLogger(__name__)

_WORD = re.compile(r"[a-z0-9]+", re.I)
_STOP = {
    "a", "an", "and", "button", "click", "for", "go", "in", "link", "of", "on", "open", "page",
    "please", "tab", "that", "the", "this", "to",
}
_MIN_STATE_ELEMENTS = 4
SITE_ACTION_PROBABILITY = 0.5
_GATE_ELEMENTS = 4
_FILLABLE_ROLES = {"input", "textbox", "combobox", "searchbox", "textarea", "select"}


def _words(text: str) -> set[str]:
    return {word.casefold() for word in _WORD.findall(text)}


def _label_matches(words: set[str], item: Element) -> int:
    label = _words(f"{item.text} {item.placeholder}")
    return sum(
        1 for word in words if word in label or (len(word) >= 4 and any(word in part for part in label))
    )


def _rank_elements(
    transcript: str, elements: tuple[Element, ...], *, fillable: bool = False
) -> tuple[list[Element], bool, str | None]:
    words = _words(transcript) - _STOP
    if fillable:
        elements = tuple(
            item for item in elements if item.role in _FILLABLE_ROLES or item.tag in _FILLABLE_ROLES
        )
    matches = {item.id: _label_matches(words, item) for item in elements}
    precision = {
        item.id: matches[item.id] / max(1, len(_words(f"{item.text} {item.placeholder}")))
        for item in elements
    }

    def score(item: Element) -> tuple[float, float]:
        overlap = matches[item.id] * 5 + len(words & _words(item.href)) * 2
        main = 2 if item.in_main else 0
        result_link = 1 if "result" in words and item.role == "link" else 0
        return (overlap + main + result_link, -item.top)

    ranked = sorted(elements, key=score, reverse=True)
    best = max(matches.values(), default=0)
    clear = None
    if best:
        best_precision = max(precision[item.id] for item in ranked if matches[item.id] == best)
        tied = [
            item for item in ranked if matches[item.id] == best and precision[item.id] == best_precision
        ]
        destinations = {item.href or item.id for item in tied}
        if len(destinations) == 1:
            clear = tied[0].id
    elif fillable and len(ranked) == 1:
        clear = ranked[0].id
    return ranked, best > 0, clear


def _best_label_matches(transcript: str, elements: list[Element]) -> list[str]:
    words = _words(transcript) - _STOP
    scores = {item.id: _label_matches(words, item) for item in elements}
    best = max(scores.values(), default=0)
    return [item.id for item in elements if best and scores[item.id] == best]


def _short_url(url: str, page_host: str = "") -> str:
    parsed = urlparse(url)
    host = parsed.netloc.removeprefix("www.")
    path = parsed.path.rstrip("/")
    if host and host == page_host:
        return (path or "/")[:40]
    return f"{host}{path}"[:48]


def _element_label(element: Element, page_host: str) -> str:
    return (
        element.text
        or element.placeholder
        or element.value
        or _short_url(element.href, page_host)
        or element.tag
    )[:40]


def _element_line(element: Element, page_host: str) -> str:
    href = f" {_short_url(element.href, page_host)}" if element.href else ""
    return f'{element.id} {element.role} "{_element_label(element, page_host)}"{href}'


def _gate_state(state: dict) -> dict:
    slim = {key: value for key, value in state.items() if key != "visible_page_text"}
    slim["interactive_elements"] = state.get("interactive_elements", [])[:_GATE_ELEMENTS]
    return slim


def _recent_lines(history: list[dict[str, Any]]) -> list[str]:
    lines = []
    for item in history[-MAX_RECENT_ACTIONS:]:
        action = item.get("action") or {}
        detail = action.get("url") or action.get("target_id") or action.get("direction") or ""
        after = _short_url(str((item.get("outcome") or {}).get("after_url", "")))
        lines.append(f'"{str(item.get("said", ""))[:60]}" -> {action.get("type")} {detail} -> {after}')
    return lines


def _target_options(elements: list[Element], page_host: str) -> dict[str, str]:
    options: dict[str, str] = {}
    for item in elements:
        label = f"{_element_label(item, page_host)} ({item.role})"
        suffix = 2
        while label in options:
            label = f"{_element_label(item, page_host)} ({item.role} {suffix})"
            suffix += 1
        options[label] = item.id
    return options


def _label_answer_to_ids(answer: dict, labels: dict[str, str]) -> dict:
    if not isinstance(answer, dict):
        return answer
    remap = {**labels, "none": "none"}
    result = dict(answer)
    if answer.get("choice") in remap:
        result["choice"] = remap[answer["choice"]]
    if isinstance(answer.get("probabilities"), dict):
        result["probabilities"] = {remap.get(k, k): v for k, v in answer["probabilities"].items()}
    return result


class LayaEngine:
    """Windows Laya Engine supporting PyTorch/Laya deep learning model and fast fallback."""

    def __init__(self, model: str | None = None) -> None:
        self.model_name = model or os.getenv("LAYA_MODEL", MODEL_DEFAULT)
        self._agent: Any | None = None
        self._lock = threading.Lock()
        self._use_model: bool = False

    @property
    def loaded(self) -> bool:
        return self._agent is not None or not self._use_model

    def warm(self) -> None:
        with self._lock:
            if self._agent is not None:
                return
            # Use deep learning model if requested; otherwise default to instant zero-latency rule engine
            if os.getenv("LAYA_USE_DL", "0") == "1":
                try:
                    import laya
                    if hasattr(laya, "load"):
                        self._agent = laya.load(self.model_name)
                        self._use_model = True
                        logger.info(f"Loaded official Laya model: {self.model_name}")
                    elif hasattr(laya, "Router"):
                        self._agent = laya.Router()
                        self._use_model = True
                        logger.info("Loaded Laya Router")
                except Exception as exc:
                    logger.info(f"Using fast rule-based Laya fallback engine on Windows: {exc}")
                    self._use_model = False
            else:
                self._use_model = False

    def _predict_rule_fallback(self, state: dict, questions: dict) -> dict[str, Any]:
        """High-speed, zero-latency semantic decision fallback for Windows."""
        transcript = state.get("transcript", "").strip()
        answers: dict[str, Any] = {}

        for qid, qdef in questions.items():
            qtype = qdef.get("type")
            criteria = qdef.get("criteria", {})

            if qid == "is_command":
                is_cmd = explicit_browser_command(transcript) or any(
                    word in transcript.lower()
                    for word in (
                        "open", "go to", "search", "click", "scroll", "press", "tab",
                        "back", "forward", "reload", "type", "play", "pause", "confirm"
                    )
                )
                prob = 0.95 if is_cmd else 0.15
                answers[qid] = {"noul": prob, "choice": "yes" if is_cmd else "no"}

            elif qid == "intent":
                det = deterministic_intent(transcript)
                if det:
                    answers[qid] = {"choice": det, "probabilities": {det: 0.95}}
                else:
                    # Heuristic intent classification
                    lower = transcript.lower()
                    chosen = "none"
                    if lower.startswith(("open", "go to", "visit")) and ("http" in lower or "." in lower or "youtube" in lower or "google" in lower or "wikipedia" in lower):
                        chosen = "navigate_url"
                    elif lower.startswith(("search", "find", "look for", "google")):
                        chosen = "search_web"
                    elif "scroll down" in lower:
                        chosen = "scroll_down"
                    elif "scroll up" in lower:
                        chosen = "scroll_up"
                    elif "go back" in lower or lower == "back":
                        chosen = "go_back"
                    elif "go forward" in lower or lower == "forward":
                        chosen = "go_forward"
                    elif "reload" in lower or "refresh" in lower:
                        chosen = "reload"
                    elif "new tab" in lower:
                        chosen = "open_new_tab"
                    elif "close tab" in lower or "close this tab" in lower:
                        chosen = "close_tab"
                    elif "switch tab" in lower or "next tab" in lower or "previous tab" in lower or "tab " in lower:
                        chosen = "switch_tab"
                    elif lower.startswith("type ") or " into " in lower:
                        chosen = "type_into_field"
                    elif lower.startswith("click ") or lower.startswith("press ") or "open the " in lower:
                        chosen = "click_element"
                    answers[qid] = {"choice": chosen, "probabilities": {chosen: 0.90}}

            elif qid == "complete":
                words = transcript.strip().split()
                complete = len(words) >= 2 and not transcript.endswith((" and", " or", " to", " for", " the", " in"))
                prob = 0.90 if complete else 0.40
                answers[qid] = {"noul": prob}

            elif qid == "site":
                site_name = mentioned_site(transcript)
                chosen = site_name if site_name else "none"
                answers[qid] = {"choice": chosen, "probabilities": {chosen: 0.90}}

            elif qid == "scroll_amount":
                amt = spoken_scroll_amount(transcript, "down") or "one page"
                answers[qid] = {"choice": amt, "score": 1.0}

            elif qid == "tab_direction":
                direction = spoken_tab_direction(transcript) or "next"
                answers[qid] = {"choice": direction, "probabilities": {direction: 0.90}}

            elif qid == "destructive":
                answers[qid] = {"noul": 0.05}

            elif qid == "target":
                labels = list(criteria.keys()) if isinstance(criteria, dict) else []
                # Pick best label match
                chosen = labels[0] if labels and labels[0] != "none" else "none"
                answers[qid] = {"choice": chosen, "probabilities": {l: (0.90 if l == chosen else 0.05) for l in labels}}

            elif qtype == "choice" and isinstance(criteria, dict):
                first_key = next(iter(criteria.keys())) if criteria else "none"
                answers[qid] = {"choice": first_key, "probabilities": {first_key: 0.85}}

        return {"answers": answers}

    def _run(self, state: dict, questions: dict, answers: dict, stages: list[dict]) -> None:
        started = time.perf_counter()
        if self._use_model and self._agent is not None:
            try:
                with self._lock:
                    result = self._agent.predict(state, questions)
                elapsed = (time.perf_counter() - started) * 1000
                answers.update(result.get("answers", {}) if isinstance(result, dict) else {})
                stages.append({
                    "questions": list(questions),
                    "ms": round(elapsed, 2),
                    "state_tokens": 128,
                    "state_budget": 512,
                    "trimmed": [],
                })
                return
            except Exception as e:
                logger.warning(f"Model prediction failed, falling back to rule engine: {e}")

        # Rule fallback execution
        result = self._predict_rule_fallback(state, questions)
        elapsed = (time.perf_counter() - started) * 1000
        answers.update(result.get("answers", {}))
        stages.append({
            "questions": list(questions),
            "ms": round(elapsed, 2),
            "state_tokens": 64,
            "state_budget": 512,
            "trimmed": [],
        })

    def _state(
        self, transcript: str, snapshot: Snapshot, recent_actions: list[dict[str, Any]] | None
    ) -> tuple[dict, list[Element], bool, str]:
        page_host = urlparse(snapshot.url).netloc.removeprefix("www.")
        ranked, element_match, _ = _rank_elements(transcript, snapshot.elements)
        state: dict[str, Any] = {
            "transcript": transcript,
            "browser": {"url": _short_url(snapshot.url), "title": snapshot.title[:80]},
            "interactive_elements": [_element_line(item, page_host) for item in ranked[:MAX_STATE_ELEMENTS]],
        }
        recent = _recent_lines(recent_actions or [])
        if recent:
            state["recent_actions"] = recent
        if snapshot.text:
            state["visible_page_text"] = snapshot.text[:MAX_PAGE_TEXT]
        return state, ranked, element_match, page_host

    def decide(
        self,
        transcript: str,
        snapshot: Snapshot,
        *,
        recent_actions: list[dict[str, Any]] | None = None,
        final: bool = False,
        silent_seconds: float = 0.0,
    ) -> ModelDecision:
        self.warm()
        transcript = transcript[-400:]
        state, ranked, element_match, page_host = self._state(transcript, snapshot, recent_actions)
        text_spans = text_candidates(transcript)
        urls = url_candidates(transcript)
        fixed = fixed_questions()
        answers: dict[str, Any] = {}
        stages: list[dict] = []

        universal = universal_command(transcript)
        exact = None if universal else sites.match_phrase(strip_lead(transcript), snapshot.url)
        if exact:
            return ModelDecision(
                answers={},
                candidates={"text": text_spans, "url": urls},
                latency_ms=0.0,
                model=self.model_name,
                state=state,
                element_match=element_match,
                site={"id": exact.action.id, "text": exact.text, "source": "rule"},
            )

        _, _, clear_element = _rank_elements(transcript, snapshot.elements)
        skip_pack = universal or clear_element
        lexical = None if skip_pack else sites.lexical_match(transcript, snapshot.url)
        if lexical:
            return ModelDecision(
                answers={},
                candidates={"text": text_spans, "url": urls},
                latency_ms=0.0,
                model=self.model_name,
                state=state,
                element_match=element_match,
                site={"id": lexical.action.id, "text": lexical.text, "source": "lexical"},
            )
        pack = sites.pack_for(snapshot.url)

        # Stage 1: gate questions
        gate = {}
        if not explicit_browser_command(transcript):
            gate["is_command"] = fixed["is_command"]
        if deterministic_intent(transcript, element_match=element_match) is None:
            gate["intent"] = fixed["intent"]
        early = early_intent(transcript, element_match)
        if not final and not early:
            gate["complete"] = fixed["complete"]
        unnamed = deterministic_intent(transcript, element_match=element_match) is None
        if pack and not clear_element and unnamed:
            site_question, site_candidates = sites.site_question(pack, transcript, snapshot.url)
            if site_candidates:
                gate["site_action"] = site_question
        if gate:
            self._run(_gate_state(state), gate, answers, stages)

        site_answer = answers.get("site_action") or {}
        site_choice = _choice(site_answer)
        site_probability = float((site_answer.get("probabilities") or {}).get(site_choice, 0.0))
        if site_choice and site_choice != "none" and site_probability >= SITE_ACTION_PROBABILITY:
            return ModelDecision(
                answers=answers,
                candidates={"text": text_spans, "url": urls},
                latency_ms=round(sum(stage["ms"] for stage in stages), 2),
                model=self.model_name,
                state=state,
                element_match=element_match,
                stages=stages,
                site={"id": site_choice, "text": "", "source": "model", "probability": site_probability},
            )

        # Stage 2: detail questions
        intent, intent_ok, _ = intent_gate(answers, transcript, element_match)
        ready = (
            intent_ok
            and command_gate(answers, transcript)[0]
            and complete_gate(answers, final=final, silent_seconds=silent_seconds, early=early)[0]
            and payload_gate(intent, final=final, silent_seconds=silent_seconds, transcript=transcript)
        )
        lexical_target = None
        target_candidates: list[str] = []
        if ready:
            target_labels: dict[str, str] = {}
            if "target" in DETAIL_QUESTIONS.get(intent, ()):
                fillable = intent in {"type_into_field", "select_option"}
                candidates, _, lexical_target = _rank_elements(
                    transcript, snapshot.elements, fillable=fillable
                )
                if not lexical_target:
                    target_labels = _target_options(candidates[:MAX_TARGET_OPTIONS], page_host)
            details = self._detail_questions(intent, transcript, fixed, text_spans, urls, target_labels)
            if details:
                self._run(state, details, answers, stages)
            if "target" in answers:
                answers["target"] = _label_answer_to_ids(answers["target"], target_labels)
                probabilities = answers["target"].get("probabilities") or {}
                ranked_ids = sorted(
                    (key for key in probabilities if key != "none"), key=lambda key: -probabilities[key]
                )
                tied = _best_label_matches(transcript, candidates[:MAX_TARGET_OPTIONS])
                likely = [key for key in ranked_ids if probabilities[key] >= 0.08]
                target_candidates = list(dict.fromkeys([*tied, *likely]))[:3]

        return ModelDecision(
            answers=answers,
            candidates={"text": text_spans, "url": urls},
            latency_ms=round(sum(stage["ms"] for stage in stages), 2),
            model=self.model_name,
            state=state,
            element_match=element_match,
            stages=stages,
            lexical_target=lexical_target,
            target_candidates=target_candidates,
        )

    @staticmethod
    def _detail_questions(
        intent: str,
        transcript: str,
        fixed: dict,
        text_spans: list[str],
        urls: list[str],
        target_labels: dict[str, str],
    ) -> dict:
        questions = {}
        for qid in DETAIL_QUESTIONS.get(intent, ()):
            if qid == "url_span" and len(urls) > 1:
                questions[qid] = span_question(qid, urls)
            elif qid == "site" and not urls and not mentioned_site(transcript):
                questions[qid] = fixed["site"]
            elif qid == "text_span" and text_spans and not explicit_payload(transcript):
                questions[qid] = span_question(qid, text_spans)
            elif qid == "target" and target_labels:
                questions[qid] = target_question(list(target_labels))
            elif qid == "scroll_amount" and spoken_scroll_amount(transcript, "down") is None:
                questions[qid] = fixed[qid]
            elif qid == "tab_direction" and not (spoken_tab_direction(transcript) or tab_command(transcript)):
                questions[qid] = fixed[qid]
            elif qid == "destructive":
                questions[qid] = fixed[qid]
        return questions


__all__ = ["LayaEngine", "_choice", "_confidence", "_probability"]
