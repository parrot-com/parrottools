import contextvars
import json
import logging
import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, Optional, Union

import sentry_sdk
import structlog
from structlog.contextvars import (
    STRUCTLOG_KEY_PREFIX,
    bind_contextvars,
    unbind_contextvars,
)

from parrottools.__version__ import __title__, __version__

# Following OpenTelemetry Data Model
# https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/logs/data-model.md#displaying-severity
SEVERITY_NUMBER_MAPPING = {
    "TRACE": 1,
    "DEBUG": 5,
    "INFO": 9,
    "WARNING": 13,
    "WARN": 13,
    "ERROR": 17,
    "FATAL": 21,
    "CRITICAL": 21,
}
CONTEXTVARS_KEY = "__contextvars"


def clear_log_context() -> None:
    unbind_contextvars(CONTEXTVARS_KEY)


def update_log_context(**kwargs) -> Dict[str, Any]:
    original_ctx = {}
    # Structlog is using Python native contextvars library.
    # This is currently only way how to access Structlog context variables outside megre_contextvars method.
    for key, val in contextvars.copy_context().items():
        if key.name == f'{STRUCTLOG_KEY_PREFIX}{CONTEXTVARS_KEY}' and val is not Ellipsis:
            original_ctx = val
            break

    new_context = original_ctx.copy()
    new_context.update(kwargs)
    bind_contextvars(__contextvars=new_context)
    return original_ctx


@contextmanager
def log_context(**kwargs):
    original_ctx = update_log_context(**kwargs)
    try:
        yield
    finally:
        bind_contextvars(__contextvars=original_ctx)


def with_log_context(*context_kwargs):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            items = {arg: kwargs[arg] for arg in context_kwargs if arg in kwargs}
            original_ctx = update_log_context(**items)
            try:
                result = function(*args, **kwargs)
            finally:
                bind_contextvars(__contextvars=original_ctx)

            return result

        return wrapper

    return decorator


class CustomProcessor:
    def __init__(
        self,
        service_name: Optional[str] = None,
        service_version: Optional[str] = None,
        deployment_env: Optional[str] = None,
        sentry_enabled: bool = False,
    ) -> None:

        # Application can specify this parameters when configuring the module.
        # If not present, fallback to environment variables that should be present from
        # Kubernetes deployment downward API from deployment metadata.
        if service_name is None:
            service_name = os.environ.get("DEPLOYMENT_NAME", f"unknown_service:{__file__}")
        if service_version is None:
            service_version = os.environ.get("DEPLOYMENT_VERSION", None)
        if deployment_env is None:
            deployment_env = os.environ.get("DEPLOYMENT_ENV", None)

        self.service_name = service_name
        self.service_version = service_version
        self.deployment_env = deployment_env
        self.sentry_enabled = sentry_enabled

    def __call__(self, _: logging.Logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Formats logging event into structured log."""
        # Log fields follow OpenTelemetry specification:
        # https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/logs/data-model.md

        # Severity section
        log_level = method_name.upper()
        event_dict["severityText"] = log_level
        event_dict["severityNumber"] = SEVERITY_NUMBER_MAPPING[log_level]

        # Attributes section
        # Additional information about the specific event occurrence.
        attributes = {"code.function": event_dict.pop("logger", "")}

        if CONTEXTVARS_KEY in event_dict:
            for k, v in event_dict.pop(CONTEXTVARS_KEY, {}).items():
                attributes[f"context.{k}"] = v

        event_dict["attributes"] = attributes

        # Resources section
        # Describes the source of the log.
        event_dict["resource"] = {
            "service.name": self.service_name,
            "telemetry.sdk.name": __title__,
            "telemetry.sdk.version": __version__,
            "telemetry.sdk.language": "python",
        }

        if self.service_version is not None:
            event_dict["resource"]["service.version"] = self.service_version
        if self.deployment_env is not None:
            event_dict["resource"]["deployment.environment"] = self.deployment_env

        hostname = os.environ.get("HOSTNAME", os.uname().nodename)
        if hostname is not None:
            event_dict["resource"]["host.name"] = hostname

        # In case of exc_info is added to logging.
        # Either using `logger.exception()` or `logger.error("...", exc_info=e)`.
        if "exception" in event_dict:
            attributes["exception.message"] = event_dict.pop("event")
            attributes["exception.stacktrace"] = event_dict.pop("exception")

            # If sentry is enabled add event_dict as additional context.
            if self.sentry_enabled:
                sentry_sdk.set_context("context", event_dict)
                sentry_sdk.capture_exception()

        # Body section
        # A value containing the body of the log record.
        fields = event_dict["_record"].__dict__.get("fields")
        if fields is not None:
            fields["message"] = event_dict.pop("event")
            event_dict["body"] = fields
        elif "event" in event_dict:
            event_dict["body"] = {"message": event_dict.pop("event")}

        return event_dict


def configure_logging(
    level: Union[str, int] = logging.INFO,
    sentry_enabled: bool = False,
    service_name: Optional[str] = None,
    service_version: Optional[str] = None,
    deployment_env: Optional[str] = None,
    pretty_print: bool = False,
) -> None:
    """Configure logging for the project.
    Configure should be called before importing the logging module.

    Usage:
        from parrottools.logging import configure_logging
        configure_logging(sentry_enabled=False, service_name="App", service_version="0.1.0", deployment_env="staging")

        import logging
        logger = logging.getLogger(__name__)
    """
    foreign_pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        CustomProcessor(service_name, service_version, deployment_env, sentry_enabled),
    ]

    if pretty_print:
        processor = structlog.processors.JSONRenderer(json.dumps, indent=4)
    else:
        processor = structlog.processors.JSONRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=processor,
        foreign_pre_chain=foreign_pre_chain,
    )

    if sentry_enabled:
        sentry_sdk.init()

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(stream_handler)
