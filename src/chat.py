"""Document-only chat: structured draft, source checks, then independent verification."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from src import usage
from src.config import validated_openai_base_url
from src.diagnostics import safe_identifier, token_count
from src.layout import ParseResult
from src.models import CHAT_MODEL
from src.prompts import render_prompt

MAX_QUESTION = 2000
MAX_CONTEXT_BYTES = 200_000
OUT_OF_SCOPE = "I can only answer questions about this document."
NOT_FOUND = "That information is not in the parsed pages."
UNVERIFIED = "I couldn't verify an answer from the parsed pages."
UNAVAILABLE = "Document chat is temporarily unavailable."


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    page: int
    quote: str


class Statement(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str
    evidence: list[Evidence]


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    decision: Literal["answer", "not_found", "out_of_scope"]
    statements: list[Statement]


class Verification(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    approved: bool


@dataclass
class ChatResult:
    answer: str
    status: str
    usage: list[dict] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)


def document_pages(result: ParseResult | None) -> dict[int, str]:
    if result is None:
        return {}
    failed = set(result.content_filtered_pages)
    failed.update(d.page for d in result.page_diagnostics if d.outcome != "parsed")
    return {
        page.page: text
        for page in result.pages if page.page not in failed
        if any(block.text.strip() or any(cell.strip() for row in (block.table or []) for cell in row)
               for block in page.blocks)
        if (text := "\n\n".join(
            "\n".join(" | ".join(row) for row in block.table)
            if block.type == "table" and block.table else block.text
            for block in page.blocks
        ).strip())
    }


def _payload(messages: list[dict], schema: type[BaseModel]) -> dict:
    payload = dict(model=CHAT_MODEL, reasoning={"effort": "medium"}, input=messages,
                   text={"format": {"type": "json_schema", "name": schema.__name__,
                                    "strict": True, "schema": schema.model_json_schema()}},
                   store=False, max_output_tokens=8192)
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise ValueError("context_limit")
    return payload


def _call(client, schema, prompt_name, data, result):
    messages = [{"role": "system", "content": render_prompt(prompt_name)},
                {"role": "user", "content": json.dumps(data, ensure_ascii=False)}]
    payload = _payload(messages, schema)
    metadata = None
    known = False
    diagnostic = {"stage": prompt_name, "status": "failed"}
    try:
        response = client.responses.create(**payload)
        diagnostic["request_id"] = safe_identifier(getattr(response, "_request_id", None))
        diagnostic["model"] = safe_identifier(response.model)
        data = response.model_dump()
        counts = data.get("usage") or {}
        inp, out = token_count(counts.get("input_tokens")), token_count(counts.get("output_tokens"))
        known = inp is not None and out is not None
        details = counts.get("input_tokens_details") or {}
        metadata = {"input_tokens": inp, "output_tokens": out, "input_token_details": {
            "cache_read": token_count(details.get("cached_tokens")),
            "cache_write": token_count(details.get("cache_write_tokens"))}}
        if data.get("status") != "completed":
            raise ValueError("incomplete")
        output = data.get("output") or []
        if any(item.get("type") not in ("message", "reasoning") for item in output):
            raise ValueError("unexpected_output")
        if any(part.get("type") != "output_text" for item in output
               if item.get("type") == "message" for part in item.get("content", [])):
            raise ValueError("refused")
        parsed = schema.model_validate_json(response.output_text)
        diagnostic["status"] = "validated"
        return parsed
    finally:
        usage.record(prompt_name, CHAT_MODEL, metadata, usage_known=known, entries=result.usage)
        result.diagnostics.append(diagnostic)


def _normalize(text):
    return " ".join(text.split())


def _validated_text(draft: Draft, pages: dict[int, str]) -> str:
    if not draft.statements or len(draft.statements) > 12:
        raise ValueError("empty_or_long_answer")
    rendered = []
    for statement in draft.statements:
        text = statement.text.strip()
        if not text or re.search(r"[\r\n]|^#|```|<[^>]+>|!?\[[^\]]*\]\(|https?://", text):
            raise ValueError("invalid_style")
        if not statement.evidence or len(statement.evidence) > 12:
            raise ValueError("missing_evidence")
        for evidence in statement.evidence:
            quote = _normalize(evidence.quote)
            if not quote or evidence.page not in pages or quote not in _normalize(pages[evidence.page]):
                raise ValueError("invalid_evidence")
        refs = ", ".join(str(p) for p in sorted({e.page for e in statement.evidence}))
        rendered.append(f"{text} (p. {refs})")
    answer = " ".join(rendered)
    if len(answer.split()) > 120 or len(answer) > 2000:
        raise ValueError("answer_limit")
    return answer


def answer_document_question(parse_result, question, history=(), *, client=None) -> ChatResult:
    result = ChatResult(UNVERIFIED, "blocked")
    pages = document_pages(parse_result)
    if not pages:
        return ChatResult("Parse document pages before using chat.", "no_document")
    if not isinstance(question, str) or not question.strip() or len(question) > MAX_QUESTION:
        return ChatResult("Enter a document question of 1–2,000 characters.", "invalid_question")
    recent = [{"question": turn["question"], "answer": turn["answer"]}
              for turn in history if turn.get("status") == "answered"][-6:]
    data = {"pages": [{"page": p, "text": t} for p, t in sorted(pages.items())],
            "question": question, "history": recent}
    owned = client is None
    try:
        # Reserve room for the verification candidate before either paid request.
        if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > MAX_CONTEXT_BYTES - 30_000:
            return ChatResult("Parsed text is too large for chat. Parse a smaller page range.", "context_limit")
        if owned:
            if not os.environ.get("OPENAI_API_KEY"):
                return ChatResult("OPENAI_API_KEY is not set.", "configuration_error")
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"],
                            base_url=validated_openai_base_url(),
                            max_retries=0, timeout=60)
        draft = _call(client, Draft, "chat-answer", data, result)
        if draft.decision != "answer":
            if draft.statements:
                return result
            result.answer = NOT_FOUND if draft.decision == "not_found" else OUT_OF_SCOPE
            result.status = draft.decision
            return result
        try:
            answer = _validated_text(draft, pages)
        except ValueError:
            return result
        verified = _call(client, Verification, "chat-verify",
                         {**data, "candidate": draft.model_dump()}, result)
        if verified.approved:
            result.answer, result.status = answer, "answered"
    except Exception:
        # Never expose provider errors, raw completions, or rejected candidates.
        result.answer, result.status = UNAVAILABLE, "error"
    finally:
        if owned and client is not None:
            client.close()
    return result
