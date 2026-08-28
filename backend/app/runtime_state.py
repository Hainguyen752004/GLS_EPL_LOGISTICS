from threading import Lock


class RuntimeState:
    def __init__(self):
        self._lock = Lock()
        self._migration_failed = False
        self._migration_failure_correlation_id = None
        self._migration_failure_code = None

    @property
    def migration_failed(self):
        with self._lock:
            return self._migration_failed

    @property
    def migration_failure_correlation_id(self):
        with self._lock:
            return self._migration_failure_correlation_id

    @property
    def migration_failure(self):
        with self._lock:
            if not self._migration_failed:
                return None
            return self._migration_failure_code, self._migration_failure_correlation_id

    def record_migration_failure(self, correlation_id=None, code="DATABASE_SCHEMA_INVALID"):
        with self._lock:
            self._migration_failed = True
            self._migration_failure_correlation_id = correlation_id
            self._migration_failure_code = code

    def record_database_success(self):
        """Connection success deliberately cannot erase a migration failure."""

    def record_migration_success(self):
        with self._lock:
            self._migration_failed = False
            self._migration_failure_correlation_id = None
            self._migration_failure_code = None


runtime_state = RuntimeState()
