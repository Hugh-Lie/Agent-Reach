# -*- coding: utf-8 -*-
"""Bilibili account actions: watch history, favourite folders and followings."""

import pytest

from agent_reach.channels import bilibili
from agent_reach.runtime.result import ReachError


def _channel():
    return bilibili.BilibiliChannel()


def test_account_actions_are_declared():
    names = {a.name for a in _channel().actions}
    assert {"history", "favorites", "following"} <= names


def test_history_maps_watch_history_to_items(monkeypatch):
    seen = {}

    def fake(argv, timeout):
        seen["argv"] = argv
        return {"page": 2, "count": 1, "items": [{
            "id": "BV1", "bvid": "BV1", "title": "A video",
            "author": "Uploader", "viewed_at": "2026-10-29T10:00:00"}]}

    monkeypatch.setattr(bilibili, "_bili_json", fake)
    items = _channel()._cli_history(page=2, limit=5, timeout=5)
    assert seen["argv"][0] == "history"
    assert "--page" in seen["argv"] and "2" in seen["argv"]
    assert items == [{
        "title": "A video",
        "url": "https://www.bilibili.com/video/BV1",
        "author": "Uploader",
        "published_at": None,
        "text": "viewed at 2026-10-29T10:00:00",
        "raw": {
            "id": "BV1", "bvid": "BV1", "title": "A video",
            "author": "Uploader", "viewed_at": "2026-10-29T10:00:00"},
    }]


def test_history_respects_the_limit(monkeypatch):
    monkeypatch.setattr(bilibili, "_bili_json", lambda argv, timeout: {
        "items": [{"bvid": f"BV{i}", "title": f"v{i}"} for i in range(10)]})
    assert len(_channel()._cli_history(page=1, limit=3, timeout=5)) == 3


def test_favorites_without_folder_lists_the_folders(monkeypatch):
    seen = {}

    def fake(argv, timeout):
        seen["argv"] = argv
        return [{"id": 42, "title": "Later", "media_count": 7}]

    monkeypatch.setattr(bilibili, "_bili_json", fake)
    items = _channel()._cli_favorites(fav_id=None, page=1, limit=5, timeout=5)
    assert seen["argv"] == ["favorites"]
    assert items[0]["title"] == "Later"
    assert "42" in items[0]["text"] and "7" in items[0]["text"]


def test_favorites_with_folder_lists_the_videos(monkeypatch):
    seen = {}

    def fake(argv, timeout):
        seen["argv"] = argv
        return {"folder_id": 42, "page": 1, "has_more": False, "items": [
            {"id": "BV9", "bvid": "BV9", "title": "Saved", "duration": "10:00",
             "upper": {"name": "Uploader"}}]}

    monkeypatch.setattr(bilibili, "_bili_json", fake)
    items = _channel()._cli_favorites(fav_id=42, page=1, limit=5, timeout=5)
    assert seen["argv"][:2] == ["favorites", "42"]
    assert items[0]["url"] == "https://www.bilibili.com/video/BV9"
    assert items[0]["author"] == "Uploader"


def test_favorites_rejects_a_non_positive_folder_id(monkeypatch):
    monkeypatch.setattr(bilibili, "_bili_json", lambda argv, timeout: [])
    with pytest.raises(ReachError) as exc:
        _channel()._cli_favorites(fav_id=0, page=1, limit=5, timeout=5)
    assert exc.value.code == "BAD_INPUT"


def test_following_maps_followed_accounts(monkeypatch):
    monkeypatch.setattr(bilibili, "_bili_json", lambda argv, timeout: {
        "page": 1, "total": 1, "items": [{"id": "123", "name": "Someone", "sign": "hi"}]})
    items = _channel()._cli_following(page=1, limit=5, timeout=5)
    assert items[0]["title"] == "Someone"
    assert items[0]["url"] == "https://space.bilibili.com/123"
    assert items[0]["text"] == "hi"


def test_account_actions_ask_for_a_login_when_the_session_is_missing(monkeypatch):
    def not_logged_in(argv, timeout):
        raise ReachError("NEED_LOGIN", "not logged in")

    monkeypatch.setattr(bilibili, "_bili_json", not_logged_in)
    with pytest.raises(ReachError) as exc:
        _channel()._cli_history(page=1, limit=5, timeout=5)
    assert exc.value.code == "NEED_LOGIN"
    assert "agent-reach login bilibili" in (exc.value.hint or "")
