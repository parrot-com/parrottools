# Logging

## Configure
```python
from parrottools.logging import configure_logging

configure_logging(sentry_handler=True, service_name="App", service_version="0.1.0", deployment_env="staging")
```

## Fields

Structured logging message should be preferred instead of long, unparseable error messages. <br>
We can achieve this using native `logging` library by using `extra` parameter providing key/value `fields` dictionary.

For example, instead of:
```python
# Original logging message:
logging.info("Event {} sent to topic {}.".format(event, topic))

INFO:2021-01-18T13:35:12.360920Z:__main__:Event CreateTask sent to topic transcription.
```

We can use:
```python
# Structured logging message:
logging.info("Failed to send event.", extra={"fields": {"event": event, "topic": topic}})

{
    "timestamp": "2021-01-17T13:35:12.360920Z",
    "severityText": "INFO",
    "severityNumber": 9,
    "attributes": {
        "code.function": "__main__",
        "context.resource_id": "test_resource_1"
    },
    "resource": {
        "service.name": "App",
        "service.version": "0.1.0",
        "deployment.environment": "staging",
        "host.name": "app-pod-xyz-123",
        "telemetry.sdk.name": "parrottools",
        "telemetry.sdk.version": "0.1.0",
        "telemetry.sdk.language": "python"
    },
    "body": {
        "event": "CreateTask",
        "topic": "transcription",
        "message": "Event sent."
    }
}
```

## Exceptions
We can use logging module to handle exception states. <br>
If we configured module with sentry handler, logging module will make sure to send exception to Sentry service, <br>
while adding additional context that will be present in logging message.

```python
try:
    something()
except KeyError as e:
    logger.exception("Failed to do something.")
    # OR
    logger.error("Failed to do something", exc_info=e)
```

## With Log Context

```python
update_log_context(task_id=task_id)

{
   ...
    "attributes": {
        "code.function": "__main__",
        "context.task_id": "123456"
    },
    ...
}
```

```python
@with_log_context('task_id')
def do_task(task_id):
    logging.info("Finished task")

{
   ...
   "attributes": {
      "code.function": "__main__",
      "context.task_id": "123456"
   },
   ...
}
```

```python
def do_task(task_id):
    with log_context(task_id=task_id):
        logging.info("Finished task")

{
   ...
   "attributes": {
      "code.function": "__main__",
      "context.task_id": "123456"
   },
   ...
}
```
