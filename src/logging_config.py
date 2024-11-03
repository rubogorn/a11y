import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import sys
import inspect
from typing import Optional

class ColorFormatter(logging.Formatter):
    """Custom formatter adding colors to levelnames and improved formatting"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[94m',    # Blue
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[95m', # Magenta
        'RESET': '\033[0m'      # Reset
    }

    def __init__(self, include_timestamp=True):
        self.include_timestamp = include_timestamp
        if include_timestamp:
            fmt = '%(asctime)s - %(levelname)s - %(message)s'
            datefmt = '%Y-%m-%d %H:%M:%S'
        else:
            fmt = '%(levelname)s: %(message)s'
            datefmt = None
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record):
        # Save original values
        orig_levelname = record.levelname
        orig_msg = record.msg

        # Apply colors if not a simple message and output is to terminal
        if not getattr(record, 'simple_message', False) and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
            # Only apply color to string messages
            if isinstance(record.msg, str):
                record.msg = f"{color}{record.msg}{self.COLORS['RESET']}"

        # Format the message
        formatted_message = super().format(record)

        # Restore original values
        record.levelname = orig_levelname
        record.msg = orig_msg

        return formatted_message

class LogPathManager:
    """Manages log file paths and directory creation"""
    
    def __init__(self, base_dir: str = "output/results/logs"):
        self.base_path = Path(base_dir)
        self._ensure_log_directory()

    def _ensure_log_directory(self) -> None:
        """Ensure the log directory exists"""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            sys.stderr.write(f"Failed to create log directory: {e}\n")
            sys.exit(1)

    def get_log_file_path(self, logger_name: str) -> Path:
        """Generate a log file path with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.base_path / f"{logger_name}_{timestamp}.log"

def setup_logger(
    name: str,
    log_dir: str = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up and configure a logger with both console and file handlers
    
    Args:
        name: Logger name
        log_dir: Directory for log files (optional)
        console_level: Logging level for console output
        file_level: Logging level for file output
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(min(console_level, file_level))

    # Remove any existing handlers
    logger.handlers = []

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = ColorFormatter(include_timestamp=False)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler (if log_dir is provided)
    if log_dir:
        try:
            path_manager = LogPathManager(log_dir)
            log_file = path_manager.get_log_file_path(name)
            
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_file),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(file_level)
            
            file_formatter = ColorFormatter(include_timestamp=True)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.error(f"Failed to set up file logging: {e}")

    return logger

def ui_message(message: str, level: str = "info") -> None:
    """
    Log a message with UI formatting
    
    Args:
        message: Message to log
        level: Logging level (default: info)
    """
    caller_frame = inspect.currentframe().f_back
    module_name = inspect.getmodule(caller_frame).__name__
    logger = logging.getLogger(module_name)
    
    # Convert string level to numeric logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Add simple_message flag to indicate UI formatting
    record = logging.makeLogRecord({
        'msg': message,
        'levelno': numeric_level,
        'levelname': logging.getLevelName(numeric_level),
        'pathname': caller_frame.f_code.co_filename,
        'lineno': caller_frame.f_lineno,
        'args': (),
        'exc_info': None,
        'name': module_name,
        'simple_message': True  # Add this flag
    })
    
    logger.handle(record)

def get_logger(name: str, log_dir: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Prevent adding handlers if they already exist
    if logger.handlers:
        return logger
        
    # Set base logging level
    logger.setLevel(logging.INFO)
    
    # Create formatters with different formats for console and file
    console_formatter = ColorFormatter('%(levelname)s: %(message)s')  # Simplified console output
    file_formatter = ColorFormatter('%(asctime)s - %(thread)d - %(filename)s-%(funcName)s:%(lineno)d - %(levelname)s: %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger

def configure_root_logger(
    log_dir: str = "output/results/logs",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG
) -> None:
    """
    Configure the root logger with both file and console handlers
    
    Args:
        log_dir: Directory for log files
        console_level: Logging level for console output
        file_level: Logging level for file output
    """
    root_logger = get_logger(
        'root',
        log_dir=log_dir,
        console_level=console_level,
        file_level=file_level
    )
    
    # Set as root logger
    logging.root = root_logger