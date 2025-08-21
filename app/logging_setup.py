# app/logging_setup.py
import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/app.log",
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 5,
) -> None:
    """
    Configure application-wide logging with both console and rotating file handler.

    Args:
        log_level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        log_file: Path to the log file
        max_bytes: Max log file size before rotation
        backup_count: Number of rotated files to keep
    """
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setFormatter(formatter)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        handlers=[console_handler, file_handler],
    )

    logging.getLogger("kafka").setLevel(logging.WARNING)  # reduce Kafka noise
    logging.getLogger("aiokafka").setLevel(logging.WARNING)


# Example usage
if __name__ == "__main__":
    setup_logging("DEBUG")
    logger = logging.getLogger("test")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.error("Error message")
