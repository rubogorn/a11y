import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import sys
import inspect
from typing import Optional
import os

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
            fmt = '%(asctime)s - %(thread)d - %(filename)s-%(funcName)s:%(lineno)d - %(levelname)s: %(message)s'
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

def get_logger(name: str, log_dir: str = 'output/logs') -> logging.Logger:
    """Configure and return a logger that writes to both console and file
    
    Args:
        name: Name of the logger
        log_dir: Directory to store log files
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create timestamp for log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_path / f"{name}_{timestamp}.log"
    
    # Create logger
    logger = logging.getLogger(name)
    
    # If logger already has handlers, return it
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Create console handler with color formatting
    console_handler = logging.StreamHandler(sys.__stdout__)  # Use sys.__stdout__ to avoid recursion
    console_handler.setFormatter(ColorFormatter(include_timestamp=False))
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # Create file handler with detailed formatting
    file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
    file_handler.setFormatter(ColorFormatter(include_timestamp=True))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # Log initial message
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger

def configure_root_logger(log_dir: str = "output/logs") -> None:
    """Configure the root logger to capture all output
    
    Args:
        log_dir: Directory for log files
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create timestamp for log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_path / f"root_{timestamp}.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Create console handler with color formatting
    console_handler = logging.StreamHandler(sys.__stdout__)  # Use sys.__stdout__ to avoid recursion
    console_handler.setFormatter(ColorFormatter(include_timestamp=False))
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Create file handler with detailed formatting
    file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
    file_handler.setFormatter(ColorFormatter(include_timestamp=True))
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # Log initial message
    root_logger.info(f"Root logging initialized. Log file: {log_file}")

def log_command_output(logger: logging.Logger, command: str, output: str, error: str = None):
    """Log command execution output
    
    Args:
        logger: Logger instance
        command: Command that was executed
        output: Command output
        error: Error output (if any)
    """
    logger.info(f"Command executed: {command}")
    if output:
        logger.info(f"Command output:\n{output}")
    if error:
        logger.error(f"Command error:\n{error}")

def log_file_operation(logger: logging.Logger, operation: str, path: Path, success: bool = True, error: Exception = None):
    """Log file operations with detailed information
    
    Args:
        logger: Logger instance
        operation: Type of operation (create, read, write, delete)
        path: Path of the file/directory
        success: Whether the operation was successful
        error: Exception if operation failed
    """
    if success:
        logger.debug(f"File operation - {operation}: {path}")
    else:
        logger.error(f"File operation failed - {operation}: {path}")
        if error:
            logger.error(f"Error details: {str(error)}")

def log_directory_contents(logger: logging.Logger, path: Path, max_depth: int = 3):
    """Log the contents of a directory
    
    Args:
        logger: Logger instance
        path: Directory path to log
        max_depth: Maximum depth for recursive logging
    """
    def _log_dir_contents(current_path: Path, current_depth: int = 0):
        if current_depth > max_depth:
            return
            
        indent = "  " * current_depth
        try:
            for item in current_path.iterdir():
                if item.is_file():
                    logger.debug(f"{indent}File: {item.name}")
                elif item.is_dir():
                    logger.debug(f"{indent}Dir:  {item.name}/")
                    _log_dir_contents(item, current_depth + 1)
        except Exception as e:
            logger.error(f"Error reading directory {current_path}: {str(e)}")
    
    logger.info(f"Directory contents for: {path}")
    _log_dir_contents(path)
