import json
import logging
import os

from parrottools.logging import (
    clear_log_context,
    configure_logging,
    log_context,
    update_log_context,
    with_log_context,
)


def test_default(caplog, capsys):
    # Before configuring
    logger = logging.getLogger("test")
    logger.info("No log record present")
    assert len(caplog.records) == 0

    # Configure logger
    configure_logging()
    logger = logging.getLogger("test")

    # Log info
    logger.info("Info")
    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"] == "Info"
    assert output["severityText"] == "INFO"

    # Log info with fields
    logger.info("Info", extra={"fields": {"key": "value"}})
    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"]["message"] == "Info"
    assert output["body"]["key"] == "value"

    # Log exception
    try:
        raise KeyError("invalid key")
    except KeyError:
        logging.exception("Raised KeyError")

    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["severityText"] == "ERROR"
    assert output["attributes"]["error.message"] == "Raised KeyError"
    assert output["attributes"]["error.stack_trace"].startswith("Traceback")
    assert output["attributes"]["error.stack_trace"].endswith("KeyError: 'invalid key'")

    # Log with log_context context manager
    with log_context(key="value"):
        with log_context(key2="value2"):
            logging.info("Info")
            captured = capsys.readouterr()
            output = json.loads(captured.err)
            assert output["body"] == "Info"
            assert output["attributes"]["context.key"] == "value"
            assert output["attributes"]["context.key2"] == "value2"

    logging.info("Info")
    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"] == "Info"
    assert 'context.key' not in output["attributes"]
    assert 'context.key2' not in output["attributes"]

    # Log with update_log_context
    update_log_context(key="value")
    logger.info("Info")
    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"] == "Info"
    assert output["attributes"]["context.key"] == "value"

    update_log_context(key2="value2")
    logger.info("Info")
    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"] == "Info"
    assert output["attributes"]["context.key"] == "value"
    assert output["attributes"]["context.key2"] == "value2"

    # Log with clear_log_context
    clear_log_context()
    logger.info("Info")
    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"] == "Info"
    assert output["attributes"] == {"code.function": "test"}

    logger = logging.getLogger()
    logger.handlers.pop()


def test_with_service_params(capsys):
    configure_logging(service_name="Test", service_version="0.0.0", deployment_env="testing")
    logger = logging.getLogger("test_with_service_params")

    logger.info("Info")
    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"] == "Info"
    assert output["resource"]["service.name"] == "Test"
    assert output["resource"]["service.version"] == "0.0.0"
    assert output["resource"]["deployment.environment"] == "testing"

    logger = logging.getLogger()
    logger.handlers.pop()


def test_with_service_envs(capsys):
    os.environ.setdefault("DEPLOYMENT_NAME", "TestEnv")
    os.environ.setdefault("DEPLOYMENT_VERSION", "0.0.0")
    os.environ.setdefault("DEPLOYMENT_ENV", "testing")

    configure_logging()
    logger = logging.getLogger("test_with_service_envs")

    logger.info("Info")

    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"] == "Info"
    assert output["resource"]["service.name"] == "TestEnv"
    assert output["resource"]["service.version"] == "0.0.0"
    assert output["resource"]["deployment.environment"] == "testing"

    logger = logging.getLogger()
    logger.handlers.pop()


@with_log_context("key", "non-existing-key")
def _test_with_log_context_decorator(logger, key):
    __test_with_log_context_decorator(logger, key2="value2")


@with_log_context("key2")
def __test_with_log_context_decorator(logger, key2):
    logger.info("Info")


def test_with_log_context_decorator(capsys):
    configure_logging()
    logger = logging.getLogger("test_with_log_context_decorator")

    _test_with_log_context_decorator(logger, key="value")

    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"] == "Info"
    assert output["attributes"]["context.key"] == "value"
    assert output["attributes"]["context.key2"] == "value2"
    assert "non-existing-key" not in output["attributes"]

    logger.info("Info")
    captured = capsys.readouterr()
    output = json.loads(captured.err)
    assert output["body"] == "Info"
    assert 'context.key' not in output["attributes"]
    assert 'context.key2' not in output["attributes"]

    logger = logging.getLogger()
    logger.handlers.pop()


@with_log_context("key_exc")
def _test_with_exception(logger, key_exc):
    # Make sure this won't remove decorator context
    with log_context(inside_exc="inside_val"):
        pass

    logger.info('Info')

    with log_context(inside_exc="inside_val"):
        raise Exception("exc")


def test_with_exceptions(capsys):
    configure_logging()
    logger = logging.getLogger("test_with_exceptions")

    try:
        _test_with_exception(logger, key_exc="value_exc")
    except Exception:
        logging.exception("_test_with_exception")

    captured = capsys.readouterr()
    outputs = captured.err.splitlines()
    output = json.loads(outputs[0])
    assert output["body"] == "Info"
    assert output["attributes"]['context.key_exc'] == "value_exc"
    assert 'context.inside_exc' not in output["attributes"]

    output = json.loads(outputs[1])
    assert output["attributes"]["error.message"] == "_test_with_exception"
    assert "context.key_exc" not in output["attributes"]
    assert "context.inside_exc" not in output["attributes"]

    logger = logging.getLogger()
    logger.handlers.pop()
