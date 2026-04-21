import json
import os

json_path = "Myexamples/data/final_data/final_custom_kg_papers.json"

print(f"Checking year distribution in {json_path}...")

try:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    total_papers = 0
    year_counts = {}
    missing_year = 0
    
    for entity in data.get("entities", []):
        if entity.get("entity_type") == "paper":
            total_papers += 1
            year = entity.get("year")
            
            if year:
                try:
                    year_int = int(year)
                    year_counts[year_int] = year_counts.get(year_int, 0) + 1
                except:
                    missing_year += 1
            else:
                missing_year += 1

    print(f"Total Papers Analyzed: {total_papers}")
    print(f"Papers with valid year: {total_papers - missing_year}")
    print(f"Papers with missing/invalid year: {missing_year}")
    
    print("\nYear Distribution:")
    sorted_years = sorted(year_counts.keys())
    for y in sorted_years:
        print(f"  {y}: {year_counts[y]}")
        
    # Check cutoff
    cutoff = 2022
    post_cutoff = sum(count for y, count in year_counts.items() if y >= cutoff)
    print(f"\nTotal papers >= {cutoff}: {post_cutoff}")

except Exception as e:
    print(f"Error: {e}")

