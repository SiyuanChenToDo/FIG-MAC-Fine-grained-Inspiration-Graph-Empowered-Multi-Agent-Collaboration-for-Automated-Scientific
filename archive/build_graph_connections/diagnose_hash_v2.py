import hashlib
from camel.storages import Neo4jGraph

n4j = Neo4jGraph(
    url="bolt://localhost:17687",
    username="neo4j",
    password="ai4sci123456",
)

# Target from previous example: 
# CSV ID: 10.18653/v1/2020.acl-main.173_82f6b390
# We suspect this hash '82f6b390' comes from one of the solution nodes for this DOI.
target_doi = "10.18653/v1/2020.acl-main.173"
target_hash = "82f6b390"

print(f"Diagnosis Round 2: Checking variants for DOI {target_doi}")
print(f"Target Hash: {target_hash}\n")

def get_variants(text):
    if not text: return []
    variants = []
    # 1. Raw
    variants.append(("raw", text.encode('utf-8')))
    # 2. Strip whitespace
    variants.append(("strip", text.strip().encode('utf-8')))
    # 3. Lowercase
    variants.append(("lower", text.lower().encode('utf-8')))
    # 4. Normalized space (replace multiple spaces/newlines with single space)
    norm_text = " ".join(text.split())
    variants.append(("normalized_space", norm_text.encode('utf-8')))
    return variants

def check_hashes(label, content, property_name):
    for name, encoded in get_variants(content):
        md5 = hashlib.md5(encoded).hexdigest()[:8]
        if md5 == target_hash:
            return f"MATCH FOUND! Node: {label}, Prop: {property_name}, Method: {name} -> MD5: {md5}"
        
        # Try SHA256 just in case (8 chars)
        sha256 = hashlib.sha256(encoded).hexdigest()[:8]
        if sha256 == target_hash:
            return f"MATCH FOUND! Node: {label}, Prop: {property_name}, Method: {name} -> SHA256: {sha256}"
            
    return None

# Get all properties for the solution nodes of this DOI
query = f"""
MATCH (s:Solution)
WHERE s.sol_id STARTS WITH '{target_doi}'
RETURN s.sol_id, properties(s) as props
"""

results = n4j.query(query)

match_found = False
for record in results:
    sol_id = record['s.sol_id']
    props = record['props']
    print(f"Checking Node: {sol_id}")
    
    # Check 'text' property
    if 'text' in props:
        res = check_hashes(sol_id, props['text'], 'text')
        if res:
            print(f"  🎉 {res}")
            match_found = True
            
    # Check 'simplified' property
    if 'simplified' in props:
        res = check_hashes(sol_id, props['simplified'], 'simplified')
        if res:
            print(f"  🎉 {res}")
            match_found = True
            
    print("-" * 20)

if not match_found:
    print("❌ Still no match found with text variants.")


