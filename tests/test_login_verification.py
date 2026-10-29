# -*- coding: utf-8 -*-
"""Login must be verified: a saved file is not proof of a usable session."""

from agent_reach.channels import bilibili
from agent_reach.channels.base import Channel
from agent_reach.runtime import cli
from agent_reach.runtime.result import NEED_LOGIN, UPSTREAM_BROKEN, ReachError


class _Channel(Channel):
    name = "dummy"

    def can_handle(self, url: str) -> bool:
        return False


def test_channels_without_a_check_stay_optimistic():
    assert _Channel().verify_login() == (True, "")


def test_bilibili_reports_the_logged_in_user(monkeypatch):
    monkeypatch.setattr(bilibili, "_bili_json",
                        lambda argv, timeout: {"authenticated": True,
                                               "user": {"name": "bili_user"}})
    assert bilibili._verify_bili_login() == (True, "bili_user")


def test_bilibili_rejects_a_session_without_authentication(monkeypatch):
    monkeypatch.setattr(bilibili, "_bili_json", lambda argv, timeout: {"authenticated": False})
    ok, message = bilibili._verify_bili_login()
    assert ok is False
    assert "authenticated" in message


def test_bilibili_reports_the_upstream_login_error(monkeypatch):
    def boom(argv, timeout):
        raise ReachError(NEED_LOGIN, "未登录。使用 bili login 登录。")

    monkeypatch.setattr(bilibili, "_bili_json", boom)
    ok, message = bilibili._verify_bili_login()
    assert ok is False
    assert "未登录" in message


def test_the_channel_exposes_its_own_hint():
    assert "credential.json" in bilibili.BilibiliChannel().login_verify_hint


def test_a_failed_check_becomes_an_actionable_error():
    channel = bilibili.BilibiliChannel()
    error = cli._login_verification_error(channel, False, "no authenticated session")
    assert error is not None
    assert error.code == UPSTREAM_BROKEN
    assert "usable session" in error.message
    assert error.hint == channel.login_verify_hint


def test_a_successful_check_has_no_error():
    assert cli._login_verification_error(_Channel(), True, "bili_user") is None