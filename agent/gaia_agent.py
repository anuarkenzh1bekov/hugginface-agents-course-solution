"""GaiaAgent: an OpenAI function-calling agent for the GAIA benchmark."""
from __future__ import annotations

import json
import os
import re
import time

from openai import OpenAI, RateLimitError

from agent_tools import TOOL_SCHEMAS, dispatch
from .prompts import SYSTEM_PROMPT

DEFAULT_API_URL = "https://agents-course-unit4-scoring.hf.space"
DEFAULT_MODEL = "gpt-4o"  # vision-capable; overridable via OPENAI_MODEL


class GaiaAgent:
    def __init__(
        self,
        model: str | None = None,
        api_url: str = DEFAULT_API_URL,
        max_steps: int = 8,
    ) -> None:
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=5)
        self.model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        self.api_url = api_url
        self.max_steps = max_steps
        print(f"GaiaAgent initialized (model={self.model}).")

    def __call__(self, question: str, task_id: str | None = None, file_name: str | None = None) -> str:
        context = {
            "client": self.client,
            "model": self.model,
            "api_url": self.api_url,
            "task_id": task_id,
            "file_name": file_name,
        }

        user_content = question
        if file_name:
            user_content += f"\n\n[An attached file is available: {file_name}]"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        for _ in range(self.max_steps):
            response = self._chat(
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            messages.append(msg)

            if not msg.tool_calls:
                return self._extract_final(msg.content or "")

            for call in msg.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = dispatch(call.function.name, context, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result[:12000],
                    }
                )

        # Ran out of steps: force a final answer from the accumulated context.
        messages.append(
            {"role": "user", "content": "Stop using tools now and give your FINAL ANSWER."}
        )
        final = self._chat(messages=messages)
        return self._extract_final(final.choices[0].message.content or "")

    def _chat(self, **kwargs):
        """chat.completions.create with our own backoff on rate limits (TPM)."""
        delay = 2.0
        for attempt in range(6):
            try:
                return self.client.chat.completions.create(
                    model=self.model, temperature=0, **kwargs
                )
            except RateLimitError:
                if attempt == 5:
                    raise
                print(f"Rate limited; retrying in {delay:.0f}s...")
                time.sleep(delay)
                delay = min(delay * 2, 30)

    @classmethod
    def _extract_final(cls, text: str) -> str:
        """Pull out the answer after 'FINAL ANSWER:' and normalize it."""
        match = re.search(r"FINAL ANSWER:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
        answer = match.group(1).strip() if match else text.strip()
        # Take only the first line to avoid trailing explanations.
        answer = answer.splitlines()[0].strip() if answer else answer
        return cls._normalize(answer)

    @staticmethod
    def _normalize(answer: str) -> str:
        """Light, exact-match-safe cleanup that won't corrupt a correct value."""
        answer = answer.strip()
        # Drop markdown emphasis/code formatting the model sometimes adds.
        answer = answer.replace("**", "").replace("`", "").strip()
        # Strip a single pair of surrounding quotes.
        if len(answer) >= 2 and answer[0] in "\"'" and answer[-1] == answer[0]:
            answer = answer[1:-1].strip()
        # Remove a leading article (GAIA forbids articles in string answers).
        answer = re.sub(r"^(the|a|an)\s+", "", answer, flags=re.IGNORECASE)
        # Trim trailing sentence punctuation, keep internal commas/decimals.
        return answer.strip().rstrip(".")
