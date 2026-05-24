from voxpost.events import NewMailEvent
from voxpost.summarize import (
    DEFAULT_MODEL_ID,
    _chat_system_prompt,
    _clean_chat_briefing,
    _flan_prompt,
    _tts_speech_rules,
    build_model_input,
    format_chat_user_message,
    sample_mail_event,
    wrap_model_input,
)


def test_default_model_is_xlsum():
    assert DEFAULT_MODEL_ID == "csebuetnlp/mT5_multilingual_XLSum"


def test_build_model_input_is_body_only_for_xlsum():
    event = sample_mail_event()
    text = build_model_input(event)
    assert "TTSTask:" not in text
    assert "text-to-speech" not in text
    assert "summarize_brief:" not in text
    assert "From:" not in text
    assert "Subject:" not in text
    assert "staging deploy failed" in text
    assert "migration step timed out" in text


def test_build_model_input_truncates_long_body():
    event = NewMailEvent(
        account_id="a@b.com",
        message_id="m1",
        thread_id="t1",
        history_id="1",
        subject="Hi",
        body="x" * 5000,
    )
    text = build_model_input(event)
    assert "…" in text
    assert len(text) < 5000


def test_wrap_model_input_adds_flan_prompt():
    body = "Bonjour, pouvez-vous m'appeler?"
    wrapped = wrap_model_input(body, model_id="google/flan-t5-base", lang="fr")
    assert wrapped.startswith("Output language: fr only.")
    assert "Create a spoken assistant briefing for this email." in wrapped
    assert "Voxpost" in wrapped
    assert "never the Gmail forwarder" in wrapped
    assert "Always reply in fr only" in wrapped
    assert body in wrapped
    assert wrap_model_input(body, model_id="csebuetnlp/mT5_multilingual_XLSum", lang="en") == (
        "Write a spoken assistant briefing in en only — "
        "the configured output language, never the email language. "
        + body
    )


def test_wrap_model_input_xlsum_uses_configured_language_not_email():
    body = "Bonjour, votre colis est en route."
    wrapped = wrap_model_input(
        body,
        model_id="csebuetnlp/mT5_multilingual_XLSum",
        lang="en",
    )
    assert "in en only" in wrapped
    assert "never the email language" in wrapped
    assert body in wrapped


def test_chat_system_prompt_includes_speakable_contract():
    prompt = _chat_system_prompt(structured=False, lang="en", body_words=200)
    assert "Voxpost" in prompt
    assert "CLASSIFY FIRST" in prompt
    assert "never the Gmail forwarder" in prompt
    assert "PRESERVE FACTS" in prompt
    assert "BANNED PHRASES" in prompt


def test_wrap_model_input_t5gemma2_uses_ul2_summarize_prefix():
    body = "Your package will arrive tomorrow."
    wrapped = wrap_model_input(
        body,
        model_id="google/t5gemma-2-270m-270m",
        lang="en",
    )
    assert wrapped.startswith("summarize in en: ")
    assert "Voxpost" not in wrapped
    assert body in wrapped


def test_build_model_input_t5gemma2_is_body_only():
    event = sample_mail_event()
    text = build_model_input(event, model_id="google/t5gemma-2-270m-270m")
    assert "From:" not in text
    assert "Subject:" not in text
    assert "staging deploy failed" in text.lower()


def test_chat_system_prompt_requires_configured_language():
    en = _chat_system_prompt(structured=False, lang="en", body_words=30)
    fr = _chat_system_prompt(structured=False, lang="fr", body_words=30)
    assert "Output language: en only" in en
    assert "Never reply in the email's language" in en
    assert "Always reply in en only" in en
    assert "never the email language" in en
    assert "Output language: fr only" in fr
    assert "Always reply in fr only" in fr


def test_chat_system_prompt_includes_spam_rubric():
    prompt = _chat_system_prompt(structured=False, lang="en", body_words=30)
    lower = prompt.lower()
    assert "spam" in lower
    assert "always important" in lower
    assert "tie-breaker" in lower
    assert "you should buy" in lower
    assert "security alert" in lower or "security alerts" in lower


def test_tts_speech_rules_generic_language_code():
    rules = _tts_speech_rules("de")
    assert "Always reply in de only" in rules
    assert "never the email language" in rules
    assert "TTS NUMBER RULES" in rules


def test_flan_prompt_includes_assistant_contract_and_language():
    prompt = _flan_prompt(body_words=200, lang="en")
    lower = prompt.lower()
    assert "voxpost" in lower
    assert "spam" in lower
    assert "Always reply in en only" in prompt
    assert "deadlines" in lower or "limits" in lower


def test_chat_system_prompt_same_for_structured():
    plain = _chat_system_prompt(structured=False, lang="en", body_words=30)
    structured = _chat_system_prompt(structured=True, lang="en", body_words=30)
    assert plain == structured


def test_format_chat_user_message_plain():
    msg = format_chat_user_message("From: Alex\nSubject: Hi\nBody text", structured=False)
    assert msg.startswith("EMAIL\n")
    assert "Output the briefing only" in msg


def test_format_chat_user_message_structured():
    msg = format_chat_user_message('{"is_forward": true}', structured=True)
    assert "structured fields" in msg
    assert "never envelope_from" in msg
    assert "Output the briefing only" in msg


def test_clean_chat_briefing_strips_thinking_and_preamble():
    raw = "Here is the briefing: Security alert from Berlin."
    assert _clean_chat_briefing(raw) == "Security alert from Berlin."
    raw_think = "<think>reasoning</think> Done."
    assert _clean_chat_briefing(raw_think) == "Done."


def test_flan_prompt_long_mail_includes_action_and_limits():
    prompt = _flan_prompt(body_words=200, lang="en")
    lower = prompt.lower()
    assert "voxpost" in lower
    assert "deadlines" in lower or "limits" in lower


def test_build_model_input_flan_includes_from_and_subject():
    event = sample_mail_event()
    text = build_model_input(event, model_id="google/flan-t5-base")
    assert "From:" in text
    assert "Subject:" in text
    assert "staging deploy failed" in text


def test_build_model_input_qwen_includes_from_and_subject():
    event = sample_mail_event()
    text = build_model_input(event, model_id="Qwen/Qwen2.5-0.5B-Instruct")
    assert "From:" in text
    assert "Subject:" in text
    assert "staging deploy failed" in text


def test_build_model_input_smollm_includes_from_and_subject():
    event = sample_mail_event()
    text = build_model_input(event, model_id="HuggingFaceTB/SmolLM2-1.7B-Instruct")
    assert "From:" in text
    assert "Subject:" in text
    assert "staging deploy failed" in text


def test_build_model_input_phi_includes_from_and_subject():
    event = sample_mail_event()
    text = build_model_input(event, model_id="microsoft/Phi-4-mini-instruct")
    assert "From:" in text
    assert "Subject:" in text
    assert "staging deploy failed" in text


def test_new_mail_event_from_json_roundtrip():
    original = sample_mail_event()
    restored = NewMailEvent.from_json(original.to_json())
    assert restored.message_id == original.message_id
    assert restored.subject == original.subject
    assert restored.attachment_count == 1
    assert restored.attachments[0].filename == "error.log"
