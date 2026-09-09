
from django.db import transaction
import logging
from enterprise_hrms.api.exceptions import HRMSBaseException

logger = logging.getLogger(__name__)

class BusinessTransaction:
    """
    Context manager for wrapping business logic in a database transaction,
    providing structured error handling and logging.
    """
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self._atomic = transaction.atomic()
        
    def __enter__(self):
        logger.info(f"Starting BusinessTransaction: {self.operation_name}")
        self._atomic.__enter__()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"BusinessTransaction '{self.operation_name}' failed: {exc_type.__name__} - {exc_val}")
            # Rollback occurs automatically in the inner atomic context
            self._atomic.__exit__(exc_type, exc_val, exc_tb)
            
            # Optionally re-raise custom exceptions directly or wrap others
            if issubclass(exc_type, HRMSBaseException):
                return False # re-raise
            else:
                return False # re-raise other unexpected errors as well
        else:
            logger.info(f"BusinessTransaction '{self.operation_name}' completed successfully.")
            self._atomic.__exit__(exc_type, exc_val, exc_tb)
            return False # allow normal execution to proceed
