import logging
from types import SimpleNamespace

from celery import shared_task
from django.test import TestCase

from config.celery import (
    REQUEST_ID_HEADER,
    USER_ID_HEADER,
    add_request_context_headers,
    bind_task_logging_context,
    log_task_finished,
)
from core.structured_logging import (
    RequestContextFilter,
    bind_request_context,
    request_id_var,
    reset_request_context,
    task_id_var,
)


@shared_task(name="core.tests.log_something")
def log_something():
    logging.getLogger("questlog.test").info("inside the task")
    return task_id_var.get()


def context_of(record_name="questlog.test"):
    record = logging.LogRecord(record_name, logging.INFO, __file__, 1, "message", (), None)
    RequestContextFilter().filter(record)
    return vars(record)


class CeleryLoggingContextTest(TestCase):
    def test_queued_tasks_carry_the_request_context(self):
        headers: dict = {}
        tokens = bind_request_context("req-1", "user-1")
        try:
            add_request_context_headers(headers=headers)
        finally:
            reset_request_context(tokens)

        self.assertEqual(headers, {REQUEST_ID_HEADER: "req-1", USER_ID_HEADER: "user-1"})

    def test_task_logs_carry_the_queuing_request_and_the_task(self):
        request = SimpleNamespace(get={REQUEST_ID_HEADER: "req-1", USER_ID_HEADER: "user-1"}.get)
        task = SimpleNamespace(name="tracking.tasks.sync_bgg_plays", request=request)

        with self.assertLogs("questlog.tasks", "INFO") as logs:
            bind_task_logging_context(task_id="task-1", task=task)
            during = context_of()
            log_task_finished(task_id="task-1", state="SUCCESS")

        self.assertEqual(
            (during["request_id"], during["user_id"], during["task_id"], during["task_name"]),
            ("req-1", "user-1", "task-1", "tracking.tasks.sync_bgg_plays"),
        )
        after = context_of()
        self.assertIsNone(after["task_id"])
        self.assertIsNone(after["request_id"])
        finished = vars(logs.records[-1])
        self.assertEqual(finished["state"], "SUCCESS")
        self.assertGreaterEqual(finished["duration_ms"], 0)

    def test_scheduled_tasks_use_their_task_id_as_request_id(self):
        result = log_something.apply(task_id="beat-task-1")

        self.assertEqual(result.get(), "beat-task-1")
        self.assertIsNone(request_id_var.get())
