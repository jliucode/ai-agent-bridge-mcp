"""
Configuration file
Contains various project configurations such as logging, LLM settings, etc.
All sensitive information is injected via environment variables, not hardcoded.
"""

import logging
import os

# Default output directory configuration
DEFAULT_OUTPUT_DIR = os.getenv("DEFAULT_OUTPUT_DIR", "output")

# LLM API configuration — read from environment variables
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_MODEL_NAME = os.getenv("DASHSCOPE_MODEL_NAME", "qwen-max")

# Server configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))


# Logging configuration
def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Set up logging configuration

    Args:
        log_level: Log level, defaults to INFO
        log_file: Log file path, if None only outputs to console
    """
    # Create log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # If log file is specified, create file handler
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        # By default, create log directory by year/month and output to log file
        import datetime
        now = datetime.datetime.now()
        year_month_dir = os.path.join('logs', str(now.year), f'{now.month:02d}')
        os.makedirs(year_month_dir, exist_ok=True)

        # Generate timestamped log file name
        timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')
        default_log_file = os.path.join(year_month_dir, f'app_{timestamp}.log')

        file_handler = logging.FileHandler(default_log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


# Default log configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'