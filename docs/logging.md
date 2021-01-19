# Logging

## Data model

Field Name     |Description
---------------|--------------------------------------------
timestamp      |Time when the event occurred.
severityText   |The severity text (also known as log level).
severityNumber |Numerical value of the severity.
body           |The body of the log record.
resource       |Describes the source of the log.
attributes     |Additional information about the event.

#### Body
A value containing the body of the log record (see the description of any type above).
Can be for example a human-readable string message (including multi-line)
describing the event in a free form or it can be a structured data composed of arrays and maps of other values.
Can vary for each occurrence of the event coming from the same source.

#### Resource
Resource                |Description
------------------------|--------------------------------------------
service.name            |Logical name of the service.
service.version         |The version string of the service API or implementation.
host.name               |Name of the host. On Unix systems, it may contain what the hostname command returns, or the fully qualified hostname, or another name specified by the user.
deployment.environment  | Name of the deployment environment (aka deployment tier).
telemetry.sdk.name      |The name of the telemetry SDK as defined above.
telemetry.sdk.language  |The language of the telemetry SDK.
telemetry.sdk.version   |The version string of the telemetry SDK.

#### Attributes
Attribute               |Description
------------------------|--------------------------------------------
code.function           |The method or function name, or equivalent.
exception.message       |The exception message.
exception.stacktrace    |A stacktrace as a string in the natural representation for the language runtime. The representation is to be determined and documented by each language SIG.
context.<KEY>           |Custom key/value attribute with additional information provided explicitly inside code.


## Configure
```python
from parrottools.logging import configure_logging

configure_logging(sentry_enabled=True, service_name="App", service_version="0.1.0", deployment_env="staging")
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
logging.info("Event sent.", extra={"fields": {"event": event, "topic": topic}})

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
