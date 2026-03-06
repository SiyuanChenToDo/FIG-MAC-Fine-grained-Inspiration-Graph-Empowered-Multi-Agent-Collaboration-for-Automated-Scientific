"""Text processing utility functions."""

import re
from typing import List, Tuple, Optional


def extract_sections(text: str, 
                     section_markers: List[Tuple[str, Optional[str]]]) -> str:
    """
    Extract specific sections from text.
    
    Args:
        text: Source text
        section_markers: List of (start_marker, end_marker) tuples.
                        end_marker can be None to extract until end.
    
    Returns:
        Combined extracted sections
    """
    sections = []
    
    for start_marker, end_marker in section_markers:
        if start_marker in text:
            parts = text.split(start_marker)
            if len(parts) > 1:
                content = parts[1]
                
                if end_marker and end_marker in content:
                    content = content.split(end_marker)[0]
                elif end_marker is None:
                    # Extract until next major section
                    next_section = re.search(r'\n##?\s', content)
                    if next_section:
                        content = content[:next_section.start()]
                
                sections.append(content.strip())
    
    return "\n\n".join(sections) if sections else text


def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Raw text
        
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    return text.strip()


def truncate_text(text: str, 
                  max_length: int, 
                  smart: bool = True) -> str:
    """
    Truncate text to max length.
    
    Args:
        text: Source text
        max_length: Maximum length
        smart: If True, try to break at sentence/paragraph boundary
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    if not smart:
        return text[:max_length]
    
    truncated = text[:max_length]
    
    # Try to break at sentence end
    last_period = truncated.rfind('.')
    if last_period > max_length * 0.9:
        return truncated[:last_period + 1]
    
    # Try to break at paragraph
    last_newline = truncated.rfind('\n')
    if last_newline > max_length * 0.9:
        return truncated[:last_newline]
    
    # Try to break at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.9:
        return truncated[:last_space]
    
    return truncated


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extract JSON content from text (handles markdown code blocks).
    
    Args:
        text: Text containing JSON
        
    Returns:
        Extracted JSON string or None
    """
    # Try markdown code blocks
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'\{.*\}',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return None
