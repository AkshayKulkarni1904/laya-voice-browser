from __future__ import annotations

from laya_voice_browser_win.laya import LayaEngine
from laya_voice_browser_win.types import Element, Snapshot


def test_laya_engine_decide_navigation():
    engine = LayaEngine()
    engine.warm()

    snapshot = Snapshot(
        url="https://example.com",
        title="Example Domain",
        text="Example Domain",
        elements=(Element(id="e01", role="link", text="More information", tag="a"),),
        fingerprint="fp123",
    )

    decision = engine.decide("open youtube.com", snapshot)
    assert decision is not None
    assert decision.model is not None


def test_laya_engine_decide_click():
    engine = LayaEngine()
    engine.warm()

    snapshot = Snapshot(
        url="https://example.com",
        title="Example Domain",
        text="Example Domain",
        elements=(Element(id="e01", role="link", text="More information", tag="a"),),
        fingerprint="fp123",
    )

    decision = engine.decide("click more information", snapshot)
    assert decision is not None
