import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter
import re


def analyze_all_reviews(review_dir: Path) -> Dict[str, Any]:
    """
    Analyze all review files to understand score distribution
    """
    all_scores = []
    score_by_file = []
    
    review_files = sorted(review_dir.glob("review_Critic Crucible_*.json"))
    
    print(f"\n[INFO] Found {len(review_files)} review files")
    print("=" * 80)
    
    for file_path in review_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract score from structured_data
            structured_data = data.get("structured_data", {})
            score = None
            
            if structured_data:
                score = structured_data.get("overall_quality_score")
            
            # If no score in structured_data, try to extract from response
            if score is None:
                response_content = data.get("response_content", "")
                score = extract_score_from_text(response_content)
            
            if score is not None:
                # Ensure score is float
                try:
                    score = float(score)
                    all_scores.append(score)
                    score_by_file.append({
                        "file": file_path.name,
                        "timestamp": file_path.stem.split('_')[-1],
                        "score": score
                    })
                except (ValueError, TypeError):
                    print(f"[WARNING] Invalid score type in {file_path.name}: {score}")
        
        except Exception as e:
            print(f"[WARNING] Failed to process {file_path.name}: {e}")
    
    # Analyze score distribution
    score_counter = Counter(all_scores)
    
    return {
        "total_reviews": len(review_files),
        "scores_extracted": len(all_scores),
        "all_scores": all_scores,
        "score_distribution": dict(score_counter),
        "score_by_file": score_by_file
    }


def extract_score_from_text(text: str) -> float:
    """Extract quality score from review text"""
    patterns = [
        r'Quality Score[:\s*]+(\d+(?:\.\d+)?)\s*/\s*10',
        r'Quality Score[:\s*]+(\d+(?:\.\d+)?)',
        r'\*\*Quality Score\*\*[:\s]+(\d+(?:\.\d+)?)',
        r'"overall_quality_score"[:\s]+(\d+(?:\.\d+)?)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = float(match.group(1))
            if 0 <= score <= 10:
                return score
    
    return None


def analyze_memory_priority(review_dir: Path, num_recent: int = 5) -> Dict[str, Any]:
    """
    Analyze whether memory system correctly prioritizes recent messages
    
    Check if:
    1. Recent reviews are stored
    2. Content is preserved
    3. No evidence of truncation issues
    """
    review_files = sorted(review_dir.glob("review_Critic Crucible_*.json"))[-num_recent:]
    
    analysis = []
    
    for file_path in review_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            message_content = data.get("message_content", "")
            response_content = data.get("response_content", "")
            
            # Extract synthesis length from message
            synthesis_marker = "Hypothesis to Review:"
            synthesis_length = 0
            if synthesis_marker in message_content:
                start_idx = message_content.find(synthesis_marker) + len(synthesis_marker)
                synthesis_section = message_content[start_idx:].strip()
                # Find where task instructions start again
                task_markers = ["\n\nPlease provide:", "\n\n**IMPORTANT**:", "\n\n**CRITICAL**:"]
                for marker in task_markers:
                    if marker in synthesis_section:
                        synthesis_section = synthesis_section[:synthesis_section.find(marker)]
                        break
                synthesis_length = len(synthesis_section)
            
            analysis.append({
                "file": file_path.name,
                "timestamp": file_path.stem.split('_')[-1],
                "message_length": len(message_content),
                "response_length": len(response_content),
                "synthesis_length_in_review": synthesis_length,
                "has_structured_data": data.get("structured_data") is not None
            })
        
        except Exception as e:
            print(f"[WARNING] Failed to analyze {file_path.name}: {e}")
    
    return {
        "num_analyzed": len(analysis),
        "memory_records": analysis
    }


def find_iteration_sequences(review_dir: Path) -> List[Dict[str, Any]]:
    """
    Find sequences of reviews that appear to be from the same iteration cycle
    
    Look for:
    - Reviews close in time (within 30 minutes)
    - Same or very similar synthesis content
    - Score progression (or lack thereof)
    """
    review_files = sorted(review_dir.glob("review_Critic Crucible_*.json"))
    
    # Group by time windows (30 minutes = 1800 seconds)
    time_window = 3000  # 50 minutes for safety
    
    sequences = []
    current_sequence = []
    
    for i, file_path in enumerate(review_files):
        try:
            timestamp = int(file_path.stem.split('_')[-1])
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            score = None
            structured_data = data.get("structured_data", {})
            if structured_data:
                score = structured_data.get("overall_quality_score")
            
            if score is None:
                response_content = data.get("response_content", "")
                score = extract_score_from_text(response_content)
            
            # Ensure score is float
            if score is not None:
                try:
                    score = float(score)
                except (ValueError, TypeError):
                    score = None
            
            record = {
                "file": file_path.name,
                "timestamp": timestamp,
                "score": score
            }
            
            # Check if this belongs to current sequence
            if not current_sequence:
                current_sequence.append(record)
            else:
                last_timestamp = current_sequence[-1]["timestamp"]
                time_diff = timestamp - last_timestamp
                
                if time_diff < time_window:
                    current_sequence.append(record)
                else:
                    # Start new sequence
                    if len(current_sequence) >= 2:
                        sequences.append(current_sequence)
                    current_sequence = [record]
        
        except Exception as e:
            print(f"[WARNING] Failed to process {file_path.name}: {e}")
    
    # Add last sequence
    if len(current_sequence) >= 2:
        sequences.append(current_sequence)
    
    return sequences


def analyze_iteration_effectiveness(sequences: List[List[Dict]]) -> Dict[str, Any]:
    """
    Analyze whether iterations are effective in improving scores
    """
    analysis = {
        "total_sequences": len(sequences),
        "sequences_with_improvement": 0,
        "sequences_with_no_change": 0,
        "sequences_with_decline": 0,
        "score_unchanged_count": 0,
        "detailed_sequences": []
    }
    
    for i, sequence in enumerate(sequences, 1):
        scores = [rec["score"] for rec in sequence if rec["score"] is not None]
        
        if len(scores) < 2:
            continue
        
        # Check score progression
        improved = False
        unchanged = False
        declined = False
        
        for j in range(len(scores) - 1):
            if scores[j+1] > scores[j]:
                improved = True
            elif scores[j+1] == scores[j]:
                unchanged = True
            elif scores[j+1] < scores[j]:
                declined = True
        
        # Count sequences with all identical scores
        if len(set(scores)) == 1:
            analysis["score_unchanged_count"] += 1
        
        if improved and not declined:
            analysis["sequences_with_improvement"] += 1
            status = "IMPROVED"
        elif unchanged and not improved and not declined:
            analysis["sequences_with_no_change"] += 1
            status = "NO_CHANGE"
        elif declined:
            analysis["sequences_with_decline"] += 1
            status = "DECLINED"
        else:
            status = "MIXED"
        
        analysis["detailed_sequences"].append({
            "sequence_id": i,
            "num_reviews": len(sequence),
            "scores": scores,
            "status": status,
            "score_range": f"{min(scores):.1f} - {max(scores):.1f}" if scores else "N/A"
        })
    
    return analysis


def main():
    """Main investigation function"""
    print("=" * 80)
    print("DEEP INVESTIGATION: 8.7 Score Issue and Memory System")
    print("=" * 80)
    
    review_dir = Path(os.environ.get("WORKFLOW_OUTPUT_DIR", "workflow_outputs")) / "memory_records" / "review"
    
    if not review_dir.exists():
        print(f"\n[ERROR] Review directory not found: {review_dir}")
        return
    
    # Investigation 1: Score Distribution
    print("\n" + "=" * 80)
    print("INVESTIGATION 1: Score Distribution Analysis")
    print("=" * 80)
    
    score_analysis = analyze_all_reviews(review_dir)
    
    print(f"\n[RESULT] Total reviews analyzed: {score_analysis['total_reviews']}")
    print(f"[RESULT] Scores successfully extracted: {score_analysis['scores_extracted']}")
    
    if score_analysis['all_scores']:
        avg_score = sum(score_analysis['all_scores']) / len(score_analysis['all_scores'])
        print(f"[RESULT] Average score: {avg_score:.2f}")
        
        print(f"\n[SCORE DISTRIBUTION]:")
        sorted_scores = sorted(score_analysis['score_distribution'].items(), key=lambda x: x[1], reverse=True)
        
        for score, count in sorted_scores:
            percentage = (count / score_analysis['scores_extracted']) * 100
            bar = "█" * int(percentage / 2)
            print(f"  Score {score:.1f}: {count:3d} times ({percentage:5.1f}%) {bar}")
        
        # Check if 8.7 is hardcoded or just common
        if 8.7 in score_analysis['score_distribution']:
            count_87 = score_analysis['score_distribution'][8.7]
            percentage_87 = (count_87 / score_analysis['scores_extracted']) * 100
            print(f"\n⚠️  [FINDING] Score 8.7 appears {count_87} times ({percentage_87:.1f}%)")
            
            if percentage_87 > 30:
                print(f"   This is VERY HIGH! Investigating why...")
            else:
                print(f"   This is within normal range for a common score.")
    
    # Investigation 2: Memory System Priority
    print("\n" + "=" * 80)
    print("INVESTIGATION 2: Memory System Priority Check")
    print("=" * 80)
    
    memory_analysis = analyze_memory_priority(review_dir, num_recent=10)
    
    print(f"\n[RESULT] Analyzed {memory_analysis['num_analyzed']} recent reviews")
    print(f"\n[MEMORY RECORDS] (Most recent last):")
    
    for record in memory_analysis['memory_records']:
        print(f"\n  File: {record['file']}")
        print(f"    Timestamp: {record['timestamp']}")
        print(f"    Message length: {record['message_length']} chars")
        print(f"    Response length: {record['response_length']} chars")
        print(f"    Synthesis length in review: {record['synthesis_length_in_review']} chars")
        print(f"    Has structured data: {record['has_structured_data']}")
    
    # Check if synthesis lengths are reasonable
    synthesis_lengths = [r['synthesis_length_in_review'] for r in memory_analysis['memory_records']]
    if synthesis_lengths:
        avg_synth_len = sum(synthesis_lengths) / len(synthesis_lengths)
        print(f"\n[FINDING] Average synthesis length in reviews: {avg_synth_len:.0f} chars")
        
        if avg_synth_len < 5000:
            print(f"   ⚠️  WARNING: Synthesis lengths are LOW! This suggests truncation.")
        elif avg_synth_len > 10000:
            print(f"   ✅ OK: Synthesis lengths are reasonable (>10k chars)")
    
    # Investigation 3: Iteration Sequences
    print("\n" + "=" * 80)
    print("INVESTIGATION 3: Iteration Sequence Analysis")
    print("=" * 80)
    
    sequences = find_iteration_sequences(review_dir)
    print(f"\n[RESULT] Found {len(sequences)} iteration sequences")
    
    iteration_analysis = analyze_iteration_effectiveness(sequences)
    
    print(f"\n[ITERATION EFFECTIVENESS]:")
    print(f"  Total sequences: {iteration_analysis['total_sequences']}")
    print(f"  Sequences with improvement: {iteration_analysis['sequences_with_improvement']}")
    print(f"  Sequences with no change: {iteration_analysis['sequences_with_no_change']}")
    print(f"  Sequences with decline: {iteration_analysis['sequences_with_decline']}")
    print(f"  Sequences with ALL identical scores: {iteration_analysis['score_unchanged_count']}")
    
    # Show problematic sequences
    print(f"\n[DETAILED SEQUENCES] (Last 5):")
    for seq in iteration_analysis['detailed_sequences'][-5:]:
        status_emoji = {
            "IMPROVED": "✅",
            "NO_CHANGE": "❌",
            "DECLINED": "⚠️",
            "MIXED": "🔄"
        }
        emoji = status_emoji.get(seq['status'], "❓")
        
        print(f"\n  {emoji} Sequence {seq['sequence_id']}: {seq['status']}")
        print(f"     Reviews: {seq['num_reviews']}")
        print(f"     Scores: {' → '.join([f'{s:.1f}' for s in seq['scores']])}")
        print(f"     Range: {seq['score_range']}")
    
    # Final Assessment
    print("\n" + "=" * 80)
    print("FINAL ASSESSMENT")
    print("=" * 80)
    
    issues_found = []
    
    # Check 1: Is 8.7 suspiciously common?
    if 8.7 in score_analysis['score_distribution']:
        count_87 = score_analysis['score_distribution'][8.7]
        percentage_87 = (count_87 / score_analysis['scores_extracted']) * 100
        if percentage_87 > 30:
            issues_found.append(f"Score 8.7 appears {percentage_87:.1f}% of the time (suspiciously high)")
    
    # Check 2: Are iterations ineffective?
    if iteration_analysis['score_unchanged_count'] > iteration_analysis['sequences_with_improvement']:
        issues_found.append(f"Most iteration sequences show NO score improvement ({iteration_analysis['score_unchanged_count']} unchanged vs {iteration_analysis['sequences_with_improvement']} improved)")
    
    # Check 3: Are synthesis lengths too short?
    if synthesis_lengths and sum(synthesis_lengths) / len(synthesis_lengths) < 5000:
        issues_found.append(f"Average synthesis length is only {sum(synthesis_lengths) / len(synthesis_lengths):.0f} chars (suggests truncation)")
    
    if issues_found:
        print("\n🔴 [CRITICAL ISSUES FOUND]:")
        for i, issue in enumerate(issues_found, 1):
            print(f"  {i}. {issue}")
    else:
        print("\n✅ [NO CRITICAL ISSUES FOUND]")
        print("   Score distribution appears normal")
        print("   Memory system appears to be working correctly")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
