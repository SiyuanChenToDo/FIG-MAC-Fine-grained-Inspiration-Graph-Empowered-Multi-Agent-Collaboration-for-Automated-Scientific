"""File utility functions."""

import os
import json
import glob
from pathlib import Path
from typing import List, Optional, Dict, Any


def find_files(directory: str, pattern: str = "*", recursive: bool = True) -> List[str]:
    """
    Find files matching pattern in directory.
    
    Args:
        directory: Root directory to search
        pattern: File pattern (e.g., "*.md", "*.txt")
        recursive: Whether to search recursively
        
    Returns:
        List of file paths
    """
    if recursive:
        search_path = os.path.join(directory, "**", pattern)
        return glob.glob(search_path, recursive=True)
    else:
        search_path = os.path.join(directory, pattern)
        return glob.glob(search_path)


def load_text_file(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """
    Load text from file.
    
    Args:
        file_path: Path to file
        encoding: File encoding
        
    Returns:
        File content or None if error
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ Error loading {file_path}: {e}")
        return None


def save_json(data: Dict[str, Any], file_path: str, indent: int = 2) -> bool:
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        file_path: Output file path
        indent: JSON indentation
        
    Returns:
        True if successful
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ Error saving {file_path}: {e}")
        return False


def load_json(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON from file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading JSON {file_path}: {e}")
        return None
