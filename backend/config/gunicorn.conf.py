"""
Gunicorn settings for production.

With PROMETHEUS_MULTIPROC_DIR set, every worker writes its metrics to files in that directory so /metrics/ can report
totals across workers. When a worker exits, its live gauges must be dropped, or they would be reported forever.
"""

import os

from prometheus_client import multiprocess


def child_exit(server, worker):
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.mark_process_dead(worker.pid)
