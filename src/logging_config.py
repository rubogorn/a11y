import logging
from pathlib import Path
from datetime import datetime

class ColorFormatter(logging.Formatter):
    """Custom formatter adding colors to levelnames"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

    def format(self, record):
        # Add colors based on log level
        if record.levelno == logging.INFO:
            color = self.GREEN
        elif record.levelno == logging.WARNING:
            color = self.YELLOW
        elif record.levelno == logging.ERROR:
            color = self.RED
        else:
            color = self.BLUE
        
        # Only add color if it's not a simple message
        if not hasattr(record, 'simple_message'):
            record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)

def ui_message(logger: logging.Logger, message: str, level: int = logging.INFO) -> None:
    """
    Log a message that should appear in the UI without logging decorators
    
    Args:
        logger: The logger instance to use
        message: The message to display
        level: The logging level (default: INFO)
    """
    # Create a special record for UI messages
    record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname='',
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    # Mark as UI message to skip timestamp/level formatting
    record.simple_message = True
    record.message = message
    
    # Handle the record (this will use any configured handlers)
    logger.handle(record)
    
def setup_logger(name: str, log_dir: Path = None) -> logging.Logger:
    """
    Set up and return a configured logger instance
    
    Args:
        name: Name of the logger
        log_dir: Directory for log files (optional)
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Console handler with color formatting
    console_handler = logging.StreamHandler()
    console_formatter = ColorFormatter('%(message)s')  # Simplified format for UI messages
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if log_dir is provided
    if log_dir:
        try:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"{name}_{timestamp}.log"
            
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.error(f"Failed to set up file logging: {e}")
    
    return logger

def get_logger(name: str, log_dir: str = None) -> logging.Logger:
    """
    Get or create a logger with the given name
    
    Args:
        name: Name of the logger
        log_dir: Directory for log files (optional)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only set up the logger if it hasn't been configured
    if not logger.handlers:
        logger = setup_logger(name, Path(log_dir) if log_dir else None)
    
    return logger