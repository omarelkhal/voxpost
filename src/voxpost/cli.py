"""Voxpost CLI — connect and listen (Block 1)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from voxpost.config import _default_config_dir, load_settings
from voxpost.events import NewMailEvent
from voxpost.gcp_setup import run_setup
from voxpost.console import print_listen_intro
from voxpost.listen import run_listen
from voxpost.oauth import get_gmail_service, get_profile_email, load_credentials, run_connect_flow
from voxpost.summarize import (
    DEFAULT_MODEL_ID,
    download_summarizer_model,
    resolved_model_id,
    sample_mail_event,
    summarize_mail_event,
)
from voxpost.user_config import load_user_config
from voxpost.tts import (
    download_supertonic_models,
    supertonic_speaker_from_user_config,
    test_speak,
)


@click.group()
@click.version_option(package_name="voxpost")
def main() -> None:
    """Local Gmail event daemon — Block 1: detect new inbox mail."""


@main.command("setup-gcp")
@click.option("--project", default=None, help="GCP project (default: gcloud config project)")
@click.option("--topic", default="voxpost-gmail", show_default=True)
@click.option("--subscription", default="voxpost-gmail-pull", show_default=True)
def setup_gcp(project: str | None, topic: str, subscription: str) -> None:
    """
    Create Pub/Sub topic/subscription and IAM via gcloud.

    Writes ~/.config/voxpost/gcp.json. Grants your gcloud user Pub/Sub subscriber
    so you can use Application Default Credentials (no service account key file).
    """
    try:
        summary = run_setup(_default_config_dir(), project, topic, subscription)
    except Exception as err:  # noqa: BLE001 — surface gcloud errors to user
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)

    click.echo("GCP setup complete.")
    click.echo(f"  Project:      {summary['project']}")
    click.echo(f"  Topic:        {summary['topic']}")
    click.echo(f"  Subscription: {summary['subscription']}")
    click.echo(f"  Subscriber:   {summary['account']}")
    click.echo(f"  Config:       {summary['config_path']}")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. gcloud auth application-default login")
    click.echo("  2. Copy OAuth Desktop client JSON to ~/.config/voxpost/client_secret.json")
    click.echo("  3. voxpost connect")
    click.echo("  4. voxpost listen")


@main.command()
@click.option(
    "--port",
    default=8765,
    show_default=True,
    help="Local OAuth callback port (use 0 for any free port)",
)
def connect(port: int) -> None:
    """Sign in with Google and store OAuth credentials."""
    try:
        settings = load_settings()
    except ValueError as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)

    creds = run_connect_flow(
        settings.token_path, settings.oauth_client_secrets, port=port
    )
    service = get_gmail_service(creds)
    email = get_profile_email(service)
    click.echo(f"Connected as {email}")
    click.echo(f"Token saved to {settings.token_path}")


@main.command()
@click.option(
    "--summarize",
    is_flag=True,
    help="Block 3: emit SummarizedMailEvent JSON (local model) instead of raw mail events",
)
@click.option(
    "--speak",
    is_flag=True,
    help="Block 4: summarize and speak each event locally (implies --summarize)",
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Emit NewMailEvent / SummarizedMailEvent JSON on stdout (scripting mode)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed module logs (default: human-readable pipeline only)",
)
def listen(summarize: bool, speak: bool, json_mode: bool, verbose: bool) -> None:
    """Start Gmail watch and Pub/Sub listener."""
    try:
        settings = load_settings()
    except ValueError as err:
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)

    creds = load_credentials(settings.token_path, settings.oauth_client_secrets)
    if creds is None:
        click.echo("Not connected. Run: voxpost connect", err=True)
        sys.exit(1)

    if speak:
        summarize = True

    if not json_mode:
        print_listen_intro(summarize=summarize, speak=speak, json_mode=json_mode)

    run_listen(
        settings,
        summarize=summarize,
        speak=speak,
        json_mode=json_mode,
        verbose=verbose,
    )


@main.group()
def summarize() -> None:
    """Block 3 — local email summarization (mT5 XLSum default)."""


@summarize.command("download")
def summarize_download() -> None:
    """Download the summarizer model for fully offline use."""
    config_dir = _default_config_dir()
    model_id = resolved_model_id(config_dir)
    from voxpost.summarize import resolved_summarize_backend

    backend = resolved_summarize_backend(config_dir)
    try:
        path = download_summarizer_model(config_dir, model=model_id)
    except Exception as err:  # noqa: BLE001
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    if backend == "ollama":
        click.echo(f"Ollama model ready: {model_id}")
        click.echo(f"  Host: {load_user_config(config_dir).summarize.ollama_host}")
    else:
        click.echo(f"Model downloaded: {path}")
        click.echo(f"Model id: {model_id}")
        if model_id == DEFAULT_MODEL_ID:
            click.echo("Note: mT5 XLSum is ~2.3GB; first load may take a minute on CPU.")
    click.echo("Test with: voxpost summarize test")


@summarize.command("test")
@click.option(
    "--sample/--no-sample",
    default=True,
    show_default=True,
    help="Use built-in sample NewMailEvent",
)
@click.option("--event-json", default=None, help="NewMailEvent JSON string")
@click.option(
    "--file",
    "event_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a NewMailEvent JSON file (one object)",
)
@click.option(
    "--show-input",
    is_flag=True,
    help="Print model input prefix before the summary",
)
def summarize_test(
    sample: bool,
    event_json: str | None,
    event_file: str | None,
    show_input: bool,
) -> None:
    """Summarize a NewMailEvent locally and print SummarizedMailEvent JSON."""
    config_dir = _default_config_dir()
    try:
        if event_json:
            event = NewMailEvent.from_json(event_json)
        elif event_file:
            event = NewMailEvent.from_json(Path(event_file).read_text(encoding="utf-8"))
        elif sample:
            event = sample_mail_event()
        else:
            click.echo("Provide --event-json, --file, or use --sample.", err=True)
            sys.exit(1)

        if show_input:
            from voxpost.summarize import build_model_input

            model_id = resolved_model_id(config_dir)
            click.echo(f"Model: {model_id}", err=True)
            click.echo("Model input:", err=True)
            click.echo(build_model_input(event), err=True)
            click.echo("", err=True)

        result = summarize_mail_event(
            event,
            config_dir=config_dir,
            local_files_only=False,
        )
    except Exception as err:  # noqa: BLE001
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)

    click.echo(result.to_json())
    click.echo("", err=True)
    click.echo(f"Speakable line: {result.speakable_line}", err=True)


@summarize.command("speech-check")
@click.option(
    "--offline",
    is_flag=True,
    help="Use only locally downloaded model weights",
)
@click.option(
    "--model",
    default=None,
    help="Hugging Face model id (default: config or VOXPOST_SUMMARIZER_MODEL)",
)
@click.option(
    "--auto-grade",
    is_flag=True,
    help="Apply keyword/heuristic grading (default: manual review output only)",
)
@click.option(
    "--compare-formats",
    is_flag=True,
    help="A/B plain vs structured JSON input (chat models only; uses --auto-grade)",
)
@click.option(
    "--workers",
    default=1,
    show_default=True,
    type=click.IntRange(1, 16),
)
@click.option(
    "--cases",
    default=None,
    help="Comma-separated case ids (default: all fixtures)",
)
def summarize_speech_check(
    offline: bool,
    model: str | None,
    auto_grade: bool,
    compare_formats: bool,
    workers: int,
    cases: str | None,
) -> None:
    """Run sample emails through the summarizer for speakable-line review."""
    from voxpost.config import _default_config_dir
    from voxpost.speech_check_parallel import estimated_worker_ram_mb, recommended_workers, resolve_workers
    from voxpost.speech_check_runner import (
        _parse_case_ids,
        format_check_report,
        format_comparison_report,
        format_manual_review_report,
        run_format_comparison,
        run_model_review,
        run_speech_check,
    )
    from voxpost.speech_check_runner import filter_speech_cases
    from voxpost.summarize import resolved_model_id

    config_dir = _default_config_dir()
    model_id = model or resolved_model_id(config_dir)
    case_ids = _parse_case_ids(cases)
    case_count = len(filter_speech_cases(case_ids))
    effective_workers = resolve_workers(workers, case_count=case_count)
    if effective_workers > 1:
        click.echo(
            f"Using {effective_workers} workers "
            f"(~{estimated_worker_ram_mb(effective_workers)} MB RAM; "
            f"~{max(1, (os.cpu_count() or 4) // effective_workers)} PyTorch threads each).",
            err=True,
        )
    elif workers == 1 and case_count > 4:
        hint = recommended_workers(case_count=case_count)
        click.echo(
            f"Tip: with {case_count} cases and plenty of RAM, try --workers {hint} for faster runs.",
            err=True,
        )
    try:
        if compare_formats:
            rows = run_format_comparison(
                config_dir=config_dir,
                local_files_only=offline,
                model=model,
                case_ids=case_ids,
                workers=effective_workers,
            )
            click.echo(format_comparison_report(rows, model_id=model_id))
        elif auto_grade:
            results = run_speech_check(
                config_dir=config_dir,
                local_files_only=offline,
                model=model,
                case_ids=case_ids,
                workers=effective_workers,
            )
            click.echo(format_check_report(results, model_id=model_id))
        else:
            results = run_model_review(
                config_dir=config_dir,
                local_files_only=offline,
                model=model,
                case_ids=case_ids,
                workers=effective_workers,
            )
            click.echo(format_manual_review_report(results, model_id=model_id))
    except Exception as err:  # noqa: BLE001
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)


@summarize.command("prompt-check")
@click.option(
    "--model",
    default=None,
    help="HF Inference model id (default: Qwen/Qwen3-235B-A22B-Instruct-2507)",
)
@click.option(
    "--input-format",
    type=click.Choice(["plain", "structured"], case_sensitive=False),
    default=None,
    help="Chat input format (default: voxpost.toml chat_input_format)",
)
@click.option(
    "--compare-formats",
    is_flag=True,
    help="Run plain and structured JSON input back-to-back",
)
@click.option(
    "--cases",
    default=None,
    help="Comma-separated case ids (default: all fixtures)",
)
@click.option(
    "--provider",
    default=None,
    help="HF inference provider (e.g. featherless-ai for Qwen3.5-2B)",
)
def summarize_prompt_check(
    model: str | None,
    input_format: str | None,
    compare_formats: bool,
    cases: str | None,
    provider: str | None,
) -> None:
    """Prompt oracle: run speech-check via HF Inference (cloud, not shipped).

    Uses the same Voxpost system/user prompts as local chat-LMs but calls
    Hugging Face Inference API — no local weights, no fallbacks. Requires HF
    token (HF_TOKEN or huggingface-cli login). For prompt engineering only.
    """
    from voxpost.config import _default_config_dir
    from voxpost.hf_inference_prompt import DEFAULT_HF_PROMPT_MODEL
    from voxpost.speech_check_runner import (
        _parse_case_ids,
        format_check_report,
        format_hf_prompt_report,
        run_hf_prompt_check,
    )
    from voxpost.summarize import resolved_chat_input_format

    config_dir = _default_config_dir()
    model_id = model or DEFAULT_HF_PROMPT_MODEL
    case_ids = _parse_case_ids(cases)
    fmt_default = resolved_chat_input_format(config_dir)

    provider_note = f", provider={provider}" if provider else ""
    click.echo(
        f"HF prompt check — {model_id} (cloud inference, no fallbacks{provider_note})",
        err=True,
    )
    try:
        if compare_formats:
            for fmt in ("plain", "structured"):
                click.echo(f"\n--- input_format={fmt} ---\n", err=True)
                results = run_hf_prompt_check(
                    model=model_id,
                    config_dir=config_dir,
                    case_ids=case_ids,
                    input_format=fmt,
                    provider=provider,
                )
                click.echo(format_hf_prompt_report(results, model_id=model_id, input_format=fmt))
        else:
            fmt = (input_format or fmt_default).lower()
            results = run_hf_prompt_check(
                model=model_id,
                config_dir=config_dir,
                case_ids=case_ids,
                input_format=fmt,
                provider=provider,
            )
            click.echo(format_hf_prompt_report(results, model_id=model_id, input_format=fmt))
    except Exception as err:  # noqa: BLE001
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)


@summarize.command("resource-check")
@click.option(
    "--offline",
    is_flag=True,
    help="Use only locally downloaded model weights",
)
@click.option(
    "--model",
    default=None,
    help="Hugging Face model id (default: config or VOXPOST_SUMMARIZER_MODEL)",
)
@click.option(
    "--scenario",
    type=click.Choice(["warm", "cold", "baseline", "all"], case_sensitive=False),
    default="warm",
    show_default=True,
    help="warm=listen daemon (load once); cold=reload per email; baseline=no model",
)
@click.option(
    "--cases",
    default=None,
    help="Comma-separated speech-check case ids (default: all fixtures)",
)
def summarize_resource_check(
    offline: bool,
    model: str | None,
    scenario: str,
    cases: str | None,
) -> None:
    """Measure CPU and RAM per email fixture (speech-check cases)."""
    from voxpost.config import _default_config_dir
    from voxpost.resource_check_runner import ResourceScenario, format_resource_report, run_resource_check
    from voxpost.summarize import resolved_model_id

    config_dir = _default_config_dir()
    case_ids = tuple(c.strip() for c in cases.split(",") if c.strip()) if cases else None
    scenarios = (
        [ResourceScenario.WARM, ResourceScenario.COLD, ResourceScenario.BASELINE]
        if scenario.lower() == "all"
        else [ResourceScenario(scenario.lower())]
    )
    try:
        for idx, scen in enumerate(scenarios):
            report = run_resource_check(
                config_dir=config_dir,
                local_files_only=offline,
                model=model,
                scenario=scen,
                case_ids=case_ids,
            )
            if idx > 0:
                click.echo("")
            click.echo(format_resource_report(report))
    except Exception as err:  # noqa: BLE001
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)


@main.group()
def tts() -> None:
    """Block 4 — local text-to-speech (Supertonic 3)."""


@tts.command("download")
def tts_download() -> None:
    """Download Supertonic ONNX assets for fully offline TTS."""
    try:
        path = download_supertonic_models()
    except Exception as err:  # noqa: BLE001
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    click.echo(f"Supertonic model downloaded: {path}")
    click.echo("Test with: voxpost tts test")


@tts.command("warmup")
def tts_warmup() -> None:
    """Load Supertonic model and voice style without speaking."""
    try:
        supertonic_speaker_from_user_config(_default_config_dir()).warmup()
    except Exception as err:  # noqa: BLE001
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    click.echo("Supertonic TTS warmed up.")


@tts.command("test")
@click.argument("text", default="Voxpost is ready.")
def tts_test(text: str) -> None:
    """Synthesize and play one line locally."""
    try:
        test_speak(text)
    except Exception as err:  # noqa: BLE001
        click.echo(f"Error: {err}", err=True)
        sys.exit(1)
    click.echo(f"Spoke: {text}", err=True)


if __name__ == "__main__":
    main()
