#!/usr/bin/env python3
"""
FIG-MAC Basic Usage Example

This script demonstrates how to use the FIG-MAC system
to generate scientific hypotheses from a research topic.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Myexamples.test_mutiagent.hypothesis_society_demo import HypothesisGenerationSociety


async def generate_hypothesis(
    topic: str,
    max_iterations: int = 3,
    quality_threshold: float = 8.0,
    polish_iterations: int = 1
):
    """
    Generate a scientific hypothesis for the given topic.
    
    Args:
        topic: Research topic or question
        max_iterations: Maximum revision iterations (1-5)
        quality_threshold: Target quality score (7.0-9.5)
        polish_iterations: Final polishing rounds (0-2)
    
    Returns:
        HypothesisTaskResult with generated report
    """
    
    print("🚀 Initializing FIG-MAC Research Society...")
    print(f"📋 Topic: {topic[:100]}...")
    print("-" * 60)
    
    # Initialize the society
    society = HypothesisGenerationSociety()
    
    # Run the research workflow
    result = await society.run_research_async(
        research_topic=topic,
        max_iterations=max_iterations,
        quality_threshold=quality_threshold,
        polish_iterations=polish_iterations
    )
    
    return result


def display_results(result):
    """Display the research results in a formatted way."""
    
    if result.failed:
        print("\n❌ Research Failed")
        print(f"Error: {result.content}")
        return
    
    metadata = result.metadata
    
    print("\n" + "=" * 60)
    print("✅ RESEARCH COMPLETED SUCCESSFULLY")
    print("=" * 60)
    
    # Basic Information
    print("\n📄 Report Information:")
    print(f"   File: {metadata.get('file_path', 'N/A')}")
    print(f"   Topic: {metadata.get('topic', 'N/A')[:80]}...")
    
    # Quality Metrics
    print("\n⭐ Quality Metrics:")
    print(f"   Final Score: {metadata.get('final_quality_score', 'N/A')}/10")
    print(f"   Iterations: {metadata.get('iterations_performed', 'N/A')}/{metadata.get('max_iterations', 'N/A')}")
    
    # Evaluation Scores
    if 'evaluation_scores' in metadata:
        print("\n📊 8-Dimensional Evaluation:")
        for dim, score in metadata['evaluation_scores'].items():
            print(f"   {dim.replace('_', ' ').title()}: {score}/10")
    
    print("\n" + "=" * 60)


async def main():
    """Main entry point"""
    
    # Example research topics
    example_topics = [
        "How can graph neural networks improve drug discovery?",
        "What mechanisms enable transformers to capture long-range dependencies in protein sequences?",
        "How can pseudo-parallel data from knowledge graphs improve relation extraction?",
        "What is the role of attention mechanisms in multi-task learning for NLP?",
    ]
    
    # Select a topic (or use your own)
    topic = example_topics[0]  # Change index to try different topics
    
    # Optional: Use custom topic from command line
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    
    # Generate hypothesis
    result = await generate_hypothesis(
        topic=topic,
        max_iterations=2,      # Balanced speed/quality
        quality_threshold=8.0,  # High quality threshold
        polish_iterations=1     # Single polish round
    )
    
    # Display results
    display_results(result)


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("QWEN_API_KEY"):
        print("⚠️  Warning: QWEN_API_KEY not set!")
        print("Please set your API key:")
        print("  export QWEN_API_KEY='your-api-key'")
        print()
    
    # Run the example
    asyncio.run(main())
