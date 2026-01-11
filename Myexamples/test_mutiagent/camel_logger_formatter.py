#!/usr/bin/env python3
"""
CAMEL Native Logger Formatter
Replaces custom OutputFormatter with CAMEL framework's native logging system

Based on CAMEL logger.py implementation, provides OutputFormatter-compatible interface
while leveraging CAMEL's advanced logging features: file output, level management, environment variable configuration
"""

import logging
import sys
from typing import Optional

from camel.logger import get_logger, set_log_level, set_log_file


class CamelLoggerFormatter:
    """
    CAMEL native logging system based formatter
    Provides OutputFormatter-compatible interface while leveraging CAMEL's advanced features
    """
    
    # ANSI color codes - maintain visual compatibility
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m', 
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'bold': '\033[1m',
        'underline': '\033[4m',
        'reset': '\033[0m'
    }
    
    def __init__(self, logger_name: str = "hypothesis_generation", 
                 log_level: str = "INFO", 
                 log_file: Optional[str] = None,
                 enable_colors: bool = True):
        """
        Initialize CAMEL native logger formatter
        
        Args:
            logger_name: Logger name, will automatically add 'camel.' prefix
            log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path
            enable_colors: Whether to enable color output
        """
        # Use CAMEL native logger
        self.logger = get_logger(logger_name)
        self.enable_colors = enable_colors and sys.stdout.isatty()
        
        # Set log level
        set_log_level(log_level)
        
        # Set log file (if specified)
        if log_file:
            set_log_file(log_file)
            
        self.logger.info(f"CAMEL Logger Formatter initialized: {logger_name}")
    
    def _colorize(self, text: str, color: str) -> str:
        """Add color to text (if enabled)"""
        if self.enable_colors:
            return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
        return text
    
    def success(self, message: str):
        """Success message - use INFO level + green color"""
        colored_msg = self._colorize(f"[SUCCESS] {message}", 'green')
        # Print directly to maintain color, while logging to file
        print(colored_msg)
        self.logger.info(f"SUCCESS: {message}")
    
    def error(self, message: str):
        """Error message - use ERROR level + red color"""
        colored_msg = self._colorize(f"[ERROR] {message}", 'red')
        print(colored_msg)
        self.logger.error(message)
    
    def warning(self, message: str):
        """Warning message - use WARNING level + yellow color"""
        colored_msg = self._colorize(f"[WARNING] {message}", 'yellow')
        print(colored_msg)
        self.logger.warning(message)
    
    def info(self, message: str):
        """Info message - use INFO level + blue color"""
        colored_msg = self._colorize(f"[INFO] {message}", 'blue')
        print(colored_msg)
        self.logger.info(message)
    
    def debug(self, message: str):
        """Debug message - use DEBUG level"""
        colored_msg = self._colorize(f"[DEBUG] {message}", 'magenta')
        print(colored_msg)
        self.logger.debug(message)
    
    def header(self, message: str):
        """Header message - use INFO level + bold style"""
        colored_msg = self._colorize(f"\n{message}", 'bold')
        print(colored_msg)
        self.logger.info(f"HEADER: {message}")
    
    def section(self, title: str, width: int = 80):
        """Section separator - use INFO level + cyan color"""
        separator = "=" * width
        colored_separator = self._colorize(separator, 'cyan')
        colored_title = self._colorize(f"{title.center(width)}", 'bold')
        
        print(f"\n{colored_separator}")
        print(colored_title)
        print(colored_separator)
        
        self.logger.info(f"SECTION: {title}")
    
    def set_level(self, level: str):
        """Dynamically set log level"""
        set_log_level(level)
        self.info(f"Log level changed to: {level}")
    
    def add_file_handler(self, file_path: str):
        """Add file output"""
        set_log_file(file_path)
        self.info(f"Log file added: {file_path}")


# Global instance - backward compatibility
_global_formatter = None

def get_global_formatter() -> CamelLoggerFormatter:
    """Get global formatter instance"""
    global _global_formatter
    if _global_formatter is None:
        _global_formatter = CamelLoggerFormatter()
    return _global_formatter


# Backward compatible static method interface
class OutputFormatter:
    """
    Backward compatible OutputFormatter interface
    Internally uses CAMEL native logging system
    """
    
    @classmethod
    def success(cls, message: str):
        get_global_formatter().success(message)
    
    @classmethod
    def error(cls, message: str):
        get_global_formatter().error(message)
    
    @classmethod
    def warning(cls, message: str):
        get_global_formatter().warning(message)
    
    @classmethod
    def info(cls, message: str):
        get_global_formatter().info(message)
    
    @classmethod
    def debug(cls, message: str):
        get_global_formatter().debug(message)
    
    @classmethod
    def header(cls, message: str):
        get_global_formatter().header(message)
    
    @classmethod
    def section(cls, title: str, width: int = 80):
        get_global_formatter().section(title, width)


# Testing and demonstration
if __name__ == "__main__":
    # Test CAMEL native logger formatter
    formatter = CamelLoggerFormatter(
        logger_name="test_formatter",
        log_level="DEBUG",
        log_file="test_camel_logger.log"
    )
    
    print("=== CAMEL Logger Formatter Test ===")
    
    formatter.section("Testing Various Log Levels")
    formatter.debug("This is debug information")
    formatter.info("This is general information")
    formatter.warning("This is warning information")
    formatter.error("This is error information")
    formatter.success("This is success information")
    
    formatter.header("Testing Header Format")
    
    formatter.section("Testing Backward Compatible Interface")
    OutputFormatter.info("Information using compatible interface")
    OutputFormatter.success("Success message using compatible interface")
    OutputFormatter.warning("Warning using compatible interface")
    
    formatter.info("Test completed - check test_camel_logger.log file")
