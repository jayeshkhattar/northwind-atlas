"""OpenTelemetry tracing for the Atlas chain.

Off by default. Set ATLAS_TRACING to turn it on:
  console   print finished spans as JSON to stderr
  otlp      send to any OTLP/HTTP collector (uses OTEL_EXPORTER_OTLP_ENDPOINT)
  langfuse  send to Langfuse's OTLP endpoint (uses LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL)

With nothing set, the OpenTelemetry API hands back a no-op tracer, so every span
below costs almost nothing and the quickstart needs no credentials.
"""
import base64
import json
import os
import sys
import time
from contextlib import contextmanager

from opentelemetry import trace

_configured = False


def init_tracing(provider=None):
    """Install a TracerProvider once. Tests pass their own provider."""
    global _configured
    if provider is not None:
        trace.set_tracer_provider(provider)
        _configured = True
        return
    if _configured:
        return
    _configured = True

    mode = os.getenv("ATLAS_TRACING", "").strip().lower()
    if mode in ("", "off", "none", "0"):
        return

    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": "northwind-atlas"}))
    if mode == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=sys.stderr)))
    elif mode == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    elif mode == "langfuse":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        base = os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/")
        auth = base64.b64encode(
            f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
        ).decode()
        exporter = OTLPSpanExporter(
            endpoint=f"{base}/api/public/otel/v1/traces",
            headers={"Authorization": f"Basic {auth}"},
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        raise ValueError(f"Unknown ATLAS_TRACING={mode!r} (use console, otlp, langfuse, or leave unset)")
    trace.set_tracer_provider(provider)


def tracer():
    return trace.get_tracer("atlas")


def _attr(value):
    # OTel attributes must be primitives (or lists of them); anything else goes in as JSON.
    if isinstance(value, (str, bool, int, float)):
        return value
    return json.dumps(value, default=str)


def set_attrs(span, **attrs):
    for key, value in attrs.items():
        if value is not None:
            span.set_attribute(key, _attr(value))


@contextmanager
def span(name, kind="span", **attrs):
    """A span with a Langfuse observation type and a latency_ms attribute."""
    with tracer().start_as_current_span(name) as s:
        set_attrs(s, **{"langfuse.observation.type": kind}, **attrs)
        start = time.perf_counter()
        try:
            yield s
        finally:
            s.set_attribute("latency_ms", round((time.perf_counter() - start) * 1000, 1))


def record_llm_response(s, msg):
    """Token usage and stop reason from an Anthropic Messages response."""
    usage = msg.usage
    set_attrs(
        s,
        **{
            "gen_ai.response.model": getattr(msg, "model", None),
            "gen_ai.response.stop_reason": msg.stop_reason,
            "gen_ai.usage.input_tokens": usage.input_tokens,
            "gen_ai.usage.output_tokens": usage.output_tokens,
            "gen_ai.usage.cache_creation_input_tokens": usage.cache_creation_input_tokens or 0,
            "gen_ai.usage.cache_read_input_tokens": usage.cache_read_input_tokens or 0,
        },
    )


@contextmanager
def llm_span(purpose, model, max_tokens):
    with span(
        f"llm.{purpose}",
        kind="generation",
        **{"gen_ai.system": "anthropic", "gen_ai.request.model": model, "gen_ai.request.max_tokens": max_tokens},
    ) as s:
        yield s
