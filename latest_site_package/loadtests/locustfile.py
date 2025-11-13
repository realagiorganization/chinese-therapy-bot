"""
Locust-based load tests for the MindWell backend.

This suite exercises the chat turn endpoint (non-streaming mode) together with
therapist listing APIs to approximate a typical therapy session workflow. The
host is configured via Locust's `--host` flag or the `MW_BACKEND_HOST`
environment variable.
"""

from __future__ import annotations

import os
import random
import uuid
from locust import HttpUser, between, events, task

# Sample prompts that resemble real therapy interactions.
PROMPTS: tuple[str, ...] = (
    "我最近晚上总是睡不着，感觉很焦虑，可以帮我吗？",
    "I have been feeling burnt out at work and I do not know how to talk to my manager.",
    "最近和伴侣的沟通特别困难，总是吵架，我应该怎么办？",
    "Can you recommend relaxation techniques for managing sudden panic attacks?",
    "我担心自己的情绪会影响家人，想知道有没有合适的心理咨询师。",
    "I keep ruminating about mistakes I made years ago. How can I break the loop?",
)


@events.test_start.add_listener
def _set_default_host(environment, **_kwargs) -> None:
    """Allow `MW_BACKEND_HOST` env var to override the Locust host."""
    env_host = os.getenv("MW_BACKEND_HOST")
    if env_host:
        environment.host = env_host


class MindWellChatUser(HttpUser):
    """
    Simulated chat user.

    Each user maintains its own session identifier and alternates between chat
    turns and lightweight therapist discovery calls.
    """

    wait_time = between(1.5, 4.0)

    def on_start(self) -> None:
        self.user_id = str(uuid.uuid4())
        self.session_id: str | None = None

    @task(4)
    def chat_turn(self) -> None:
        prompt = random.choice(PROMPTS)
        payload = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "message": prompt,
            "locale": "zh-CN" if prompt and prompt[0] > "\u4e00" else "en-US",
            "enable_streaming": False,
        }

        with self.client.post(
            "/api/chat/message",
            json=payload,
            name="chat:turn",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected status {response.status_code}")
                return

            try:
                body = response.json()
            except ValueError as exc:
                response.failure(f"Invalid JSON: {exc}")
                return

            session_id = body.get("session_id")
            if session_id:
                self.session_id = session_id
            else:
                response.failure("Missing session_id in response.")

    @task(1)
    def list_therapists(self) -> None:
        params = {
            "locale": random.choice(("zh-CN", "en-US")),
            "recommended": random.choice((None, True)),
            "price_max": random.choice((None, 800, 1200)),
        }
        # Drop None values so the query string stays concise.
        filtered_params = {key: value for key, value in params.items() if value is not None}

        with self.client.get(
            "/api/therapists/",
            params=filtered_params,
            name="therapists:list",
        ) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected status {response.status_code}")
                return
            try:
                body = response.json()
            except ValueError as exc:
                response.failure(f"Invalid JSON: {exc}")
                return

            if not isinstance(body.get("therapists"), list):
                response.failure("Therapist payload missing or malformed.")

    @task(1)
    def fetch_reports(self) -> None:
        if not self.session_id:
            return

        params = {
            "user_id": self.user_id,
            "locale": random.choice(("zh-CN", "en-US")),
        }
        with self.client.get(
            "/api/reports/journey",
            params=params,
            name="reports:journey",
        ) as response:
            if response.status_code == 404:
                # Acceptable when summaries are not yet generated.
                response.success()
                return
            if response.status_code != 200:
                response.failure(f"Unexpected status {response.status_code}")
                return
            try:
                response.json()
            except ValueError as exc:
                response.failure(f"Invalid JSON: {exc}")
