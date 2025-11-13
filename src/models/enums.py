"""Enums matching database types"""

from enum import Enum


class JobStatus(str, Enum):
    """Job status enum matching database job_status type"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogLevel(str, Enum):
    """Log level enum matching database log_level type"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"
