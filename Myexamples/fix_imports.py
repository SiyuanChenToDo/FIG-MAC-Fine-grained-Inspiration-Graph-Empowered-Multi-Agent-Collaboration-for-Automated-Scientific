import os
import re
from pathlib import Path

def update_imports_in_file(file_path):
    # Define the patterns to search for and their replacements
    patterns = [
        (r'from\s+Myexamples\.(\w+\.)*camel_logger_formatter', r'from .camel_logger_formatter'),
        (r'from\s+Myexamples\.(\w+\.)*workflow_helper', r'from .workflow_helper'),
        (r'from\s+Myexamples\.(\w+\.)*simple_result_processor', r'from .simple_result_processor'),
        (r'from\s+Myexamples\.(\w+\.)*workflow_output_manager', r'from .workflow_output_manager'),
        (r'from\s+Myexamples\.(\w+\.)*camel_memory_output_manager', r'from .camel_memory_output_manager'),
        (r'from\s+Myexamples\.(\w+\.)*hypothesis_team', r'from .hypothesis_team'),
        (r'from\s+Myexamples\.agents\.', r'from agents.'),
        (r'from\s+Myexamples\.test_mutiagent\.', r'from test_mutiagent.'),
    ]
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    for pattern, repl in patterns:
        new_content, count = re.subn(pattern, repl, content)
        if count > 0:
            content = new_content
            modified = True
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated imports in {file_path}")

def main():
    # Get all Python files in the project
    project_root = Path('/root/autodl-tmp/Myexamples')
    python_files = list(project_root.rglob('*.py'))
    
    # Update imports in each file
    for file_path in python_files:
        try:
            update_imports_in_file(str(file_path))
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

if __name__ == "__main__":
    main()
