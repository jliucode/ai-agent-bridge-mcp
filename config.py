"""
配置文件
包含项目的各种配置，如日志配置、LLM配置等。
所有敏感信息通过环境变量注入，不硬编码在代码中。
"""

import logging
import os

# 默认输出目录配置
DEFAULT_OUTPUT_DIR = os.getenv("DEFAULT_OUTPUT_DIR", "output")

# LLM API 配置 — 从环境变量读取
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_MODEL_NAME = os.getenv("DASHSCOPE_MODEL_NAME", "qwen-max")

# 服务器配置
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))


# 日志配置
def setup_logging(log_level=logging.INFO, log_file=None):
    """
    设置日志配置
    
    Args:
        log_level: 日志级别，默认为INFO
        log_file: 日志文件路径，如果为None则只输出到控制台
    """
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # 清除现有的处理器
    logger.handlers.clear()

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 如果指定了日志文件，则创建文件处理器
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        # 默认情况下，按年/月创建日志目录并输出到日志文件
        import datetime
        now = datetime.datetime.now()
        year_month_dir = os.path.join('logs', str(now.year), f'{now.month:02d}')
        os.makedirs(year_month_dir, exist_ok=True)
        
        # 生成带时间戳的日志文件名
        timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')
        default_log_file = os.path.join(year_month_dir, f'app_{timestamp}.log')
        
        file_handler = logging.FileHandler(default_log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


# 默认日志配置
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
