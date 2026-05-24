"""Summarizer runtime tuning (threads, unload, token cap)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from voxpost.summarize import (
    EmailSummarizer,
    _chat_max_new_tokens,
    _resolved_cpu_threads,
    resolved_torch_device,
    sample_mail_event,
)
from voxpost.user_config import SummarizeConfig


def test_resolved_cpu_threads_auto_uses_half_cores():
    cfg = SummarizeConfig(cpu_threads=0)
    with patch("voxpost.summarize.os.cpu_count", return_value=8):
        assert _resolved_cpu_threads(cfg) == 4


def test_resolved_cpu_threads_explicit():
    cfg = SummarizeConfig(cpu_threads=3)
    assert _resolved_cpu_threads(cfg) == 3


def test_chat_max_new_tokens_from_config(tmp_path):
    (tmp_path / "voxpost.toml").write_text(
        "[summarize]\nchat_max_new_tokens = 24\n",
        encoding="utf-8",
    )
    assert _chat_max_new_tokens(tmp_path) == 24
    assert _chat_max_new_tokens(tmp_path, body_words=200) == 128


def test_chat_max_new_tokens_scales_for_long_mail(tmp_path):
    assert _chat_max_new_tokens(tmp_path, body_words=30) == 96
    assert _chat_max_new_tokens(tmp_path, body_words=200) == 128


def test_unload_clears_pipe():
    summarizer = EmailSummarizer()
    summarizer._pipe = (MagicMock(), MagicMock())
    summarizer._backend = "chat"
    summarizer.unload()
    assert summarizer._pipe is None
    assert summarizer._backend is None


def test_resolved_torch_device_auto_prefers_cuda():
    with patch("voxpost.summarize._torch_backend_available") as mock_avail:
        mock_avail.side_effect = lambda name: name == "cuda"
        assert resolved_torch_device("auto") == "cuda"


def test_resolved_torch_device_gpu_alias():
    with patch("voxpost.summarize._torch_backend_available", return_value=True):
        assert resolved_torch_device("gpu") == "cuda"


def test_resolved_torch_device_falls_back_to_cpu():
    with patch("voxpost.summarize._torch_backend_available", return_value=False):
        assert resolved_torch_device("cuda") == "cpu"


def test_ensure_loaded_moves_model_to_configured_device(tmp_path):
    summarizer = EmailSummarizer(config_dir=tmp_path, model="Qwen/Qwen3.5-0.8B")
    mock_tokenizer = MagicMock()
    mock_model = MagicMock()
    mock_model.to.return_value = mock_model

    with patch("voxpost.summarize._load_summarize_config") as mock_cfg:
        mock_cfg.return_value = SummarizeConfig(device="cuda", cpu_threads=2)
        with patch("voxpost.summarize.resolved_torch_device", return_value="cuda"):
            with patch("voxpost.summarize._apply_torch_threads") as mock_threads:
                with patch("transformers.AutoTokenizer.from_pretrained", return_value=mock_tokenizer):
                    with patch(
                        "transformers.AutoModelForCausalLM.from_pretrained",
                        return_value=mock_model,
                    ):
                        summarizer._ensure_loaded()

    mock_threads.assert_not_called()
    mock_model.to.assert_called_once_with("cuda")
    mock_model.eval.assert_called_once()
    assert summarizer._torch_device == "cuda"


def test_ensure_loaded_applies_thread_cap_and_dtype(tmp_path):
    summarizer = EmailSummarizer(config_dir=tmp_path, model="Qwen/Qwen3.5-0.8B")
    mock_tokenizer = MagicMock()
    mock_model = MagicMock()

    with patch("voxpost.summarize._load_summarize_config") as mock_cfg:
        mock_cfg.return_value = SummarizeConfig(
            cpu_threads=2,
            load_dtype="float16",
        )
        with patch("voxpost.summarize._apply_torch_threads") as mock_threads:
            with patch("transformers.AutoTokenizer.from_pretrained", return_value=mock_tokenizer):
                with patch(
                    "transformers.AutoModelForCausalLM.from_pretrained",
                    return_value=mock_model,
                ) as mock_from_pretrained:
                    summarizer._ensure_loaded()

    mock_threads.assert_called_once_with(2)
    kwargs = mock_from_pretrained.call_args.kwargs
    assert kwargs.get("low_cpu_mem_usage") is True
    assert kwargs.get("dtype") is not None


def test_summarize_chat_uses_configured_max_new_tokens(tmp_path):
    summarizer = EmailSummarizer(config_dir=tmp_path, model="Qwen/Qwen3.5-0.8B")
    mock_tokenizer = MagicMock()
    mock_tokenizer.apply_chat_template.return_value = "prompt"
    mock_tokenizer.return_value = {"input_ids": MagicMock(shape=(1, 5))}
    mock_model = MagicMock()
    mock_model.generate.return_value = MagicMock()
    mock_tokenizer.decode.return_value = "Short summary."
    summarizer._pipe = (mock_tokenizer, mock_model)

    with patch("voxpost.summarize._chat_max_new_tokens", return_value=24):
        line = summarizer._summarize_chat("From: a\nBody text")
    assert line == "Short summary."
    assert mock_model.generate.call_args.kwargs["max_new_tokens"] == 24


def test_summarize_chat_invokes_ensure_loaded():
    summarizer = EmailSummarizer(model="Qwen/Qwen3.5-0.8B")
    mock_tokenizer = MagicMock()
    mock_tokenizer.apply_chat_template.return_value = "prompt"
    mock_tokenizer.return_value = {"input_ids": MagicMock(shape=(1, 3))}
    mock_model = MagicMock()
    mock_model.generate.return_value = MagicMock()
    mock_tokenizer.decode.return_value = "Short summary."
    summarizer._pipe = (mock_tokenizer, mock_model)

    with patch.object(summarizer, "_ensure_loaded") as mock_load:
        summarizer._summarize_chat("From: a\nBody")
    mock_load.assert_called_once()
