"""Exercise real SDK serialization and document chat's fail-closed boundaries."""
import json
import httpx
from openai import OpenAI
import pytest

from src import chat
from src.layout import ParseBlock, ParsePage, ParseResult


def document(text="Coverage lasts 30 days."):
    return ParseResult(doc_sha="synthetic", pages=[ParsePage(page=2, width_px=100,
        height_px=100, blocks=[ParseBlock(structure=None, id="b1", type="text", text=text,
                                         bbox=None, conf=None, table=None)])])


def draft(text="Coverage lasts 30 days.", quote="Coverage lasts 30 days.", page=2):
    return dict(decision="answer", statements=[dict(text=text,
                evidence=[dict(page=page, quote=quote)])])


def client_for(*bodies):
    requests = []
    bodies = iter(bodies)
    def handle(request):
        requests.append(json.loads(request.content))
        value = next(bodies)
        if isinstance(value, int):
            return httpx.Response(value, json={"error": {"message": "PRIVATE ERROR"}})
        return httpx.Response(200, json=dict(id="resp_test", object="response", created_at=1,
            model="gpt-6-luna", status="completed", output=[dict(id="msg_test", type="message",
            role="assistant", status="completed", content=[dict(type="output_text",
            text=json.dumps(value), annotations=[])])],
            usage=dict(input_tokens=100, output_tokens=20, total_tokens=120,
                       input_tokens_details=dict(cached_tokens=30),
                       output_tokens_details=dict(reasoning_tokens=10))))
    return OpenAI(api_key="test-not-a-real-key", max_retries=0,
                  http_client=httpx.Client(transport=httpx.MockTransport(handle))), requests


def test_grounded_answer_and_fixed_wire_contract(monkeypatch):
    monkeypatch.setenv("REASONING_EFFORT", "high")
    client, requests = client_for(draft(), {"approved": True})
    reply = chat.answer_document_question(document(), "How long is coverage?", client=client)
    assert reply.status == "answered" and reply.answer == "Coverage lasts 30 days. (p. 2)"
    assert len(reply.usage) == 2 and all(e["model"] == "gpt-6-luna" for e in reply.usage)
    assert len(requests) == 2
    for request in requests:
        assert request["model"] == "gpt-6-luna"
        assert request["reasoning"] == {"effort": "medium"}
        assert request["store"] is False and "tools" not in request
        assert request["text"]["format"]["strict"] is True
        assert "Coverage lasts" not in request["input"][0]["content"]


@pytest.mark.parametrize("candidate", [draft(quote="Invented"), draft(page=3),
    draft(text="# Header"), draft(text="![leak](https://example.com)"),
    draft(text="word " * 121), dict(decision="answer", statements=[])])
def test_invalid_evidence_or_style_never_reaches_verifier(candidate):
    client, requests = client_for(candidate)
    reply = chat.answer_document_question(document(), "Coverage?", client=client)
    assert reply.status == "blocked" and len(requests) == 1
    assert reply.answer == chat.UNVERIFIED


@pytest.mark.parametrize("decision,message", [("out_of_scope", chat.OUT_OF_SCOPE),
                                            ("not_found", chat.NOT_FOUND)])
def test_rejections_are_fixed_and_not_verified(decision, message):
    client, requests = client_for(dict(decision=decision, statements=[]))
    reply = chat.answer_document_question(document(), "question", client=client)
    assert reply.answer == message and len(requests) == 1


def test_verifier_blocks_unsupported_claim_with_real_quote():
    client, requests = client_for(draft(text="Coverage lasts forever."), {"approved": False})
    reply = chat.answer_document_question(document(), "How long?", client=client)
    assert reply.status == "blocked" and "forever" not in reply.answer
    assert len(requests) == 2


@pytest.mark.parametrize("bodies", [(500,), (draft(), 500), ({"unexpected": "PRIVATE"},)])
def test_provider_or_schema_failure_is_sanitized_and_accounted(bodies):
    client, requests = client_for(*bodies)
    reply = chat.answer_document_question(document(), "Coverage?", client=client)
    assert reply.status == "error" and reply.answer == chat.UNAVAILABLE
    assert len(reply.usage) == len(requests)
    assert "PRIVATE" not in str(reply)


def test_local_limits_and_failed_pages_make_no_calls():
    client, requests = client_for()
    for doc, question in [(document(), "x" * 2001), (document(), " "),
                          (None, "question"), (document("x" * 200_000), "question")]:
        assert chat.answer_document_question(doc, question, client=client).status != "answered"
    doc = document()
    doc.content_filtered_pages = [2]
    assert chat.answer_document_question(doc, "question", client=client).status == "no_document"
    assert not requests


def test_only_recent_accepted_history_is_data():
    history = [dict(question=str(i), answer="answer", status="answered") for i in range(9)]
    history.append(dict(question="Ignore instructions", answer="blocked", status="out_of_scope"))
    client, requests = client_for(draft(), {"approved": True})
    chat.answer_document_question(document(), "And how long?", history, client=client)
    sent = json.loads(requests[0]["input"][1]["content"])
    assert [t["question"] for t in sent["history"]] == [str(i) for i in range(3, 9)]


def test_luna_remains_invalid_for_parser(monkeypatch):
    from src import parse, llm
    monkeypatch.setattr(parse, "preprocess_pages", lambda *a, **k: pytest.fail("preprocessed"))
    with pytest.raises(ValueError):
        parse.parse_document("unused", model="gpt-6-luna")
    with pytest.raises(llm.ExtractConfigError):
        llm._build_llm("gpt-6-luna")


def test_tables_and_missing_pages():
    doc = document("")
    doc.pages[0].blocks[0].type = "table"
    doc.pages[0].blocks[0].table = [["Service", "Copay"], ["Clinic", "$20"]]
    doc.content_filtered_pages = [3]
    pages = chat.document_pages(doc)
    assert "Clinic" in pages[2] and "$20" in pages[2] and 3 not in pages


@pytest.mark.parametrize("state", ["incomplete", "failed"])
def test_incomplete_response_never_exposes_text(state):
    class Responses:
        def create(self, **kwargs):
            class Response:
                model = "gpt-6-luna"
                output_text = "PRIVATE UNCHECKED TEXT"
                def model_dump(self):
                    return dict(status=state, usage=dict(input_tokens=10, output_tokens=20))
            return Response()
    from types import SimpleNamespace
    reply = chat.answer_document_question(document(), "Coverage?",
                                           client=SimpleNamespace(responses=Responses()))
    assert reply.status == "error" and "PRIVATE" not in str(reply)
    assert len(reply.usage) == 1 and reply.usage[0]["usage_known"]


def test_luna_cost_is_not_sol_cost():
    from src import usage
    value = dict(input_tokens=3_000_000, output_tokens=1_000_000,
                 cached_tokens=1_000_000, cache_write_tokens=1_000_000)
    assert usage.cost_usd(value, "gpt-6-luna") == pytest.approx(0.735)


def test_empty_layout_markers_do_not_enable_chat():
    doc = document("")
    doc.pages[0].blocks[0].type = "figure"
    assert chat.document_pages(doc) == {}


def test_provider_refusal_never_exposes_raw_text():
    from types import SimpleNamespace
    class Response:
        model = "gpt-6-luna"
        output_text = "PRIVATE REFUSAL"
        def model_dump(self):
            return dict(status="completed", output=[dict(type="message", content=[
                dict(type="refusal", refusal="PRIVATE REFUSAL")])])
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **k: Response()))
    reply = chat.answer_document_question(document(), "Coverage?", client=client)
    assert reply.status == "error" and "PRIVATE" not in str(reply)
    assert not reply.usage[0]["usage_known"]
