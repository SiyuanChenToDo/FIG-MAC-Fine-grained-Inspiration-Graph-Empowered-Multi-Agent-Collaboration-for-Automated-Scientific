#!/usr/bin/env python3
"""
Workflow Helper Class
Provides simple state management assistance for existing HypothesisTeam, does not replace core logic

This is an auxiliary class for simplifying state transition logic while maintaining all existing functionality
"""

from enum import Enum
from typing import Dict, Optional, List, Any
from dataclasses import dataclass


class TeamState(Enum):
    """Team state enumeration - consistent with original HypothesisTeam"""
    INIT = "init"
    LITERATURE = "literature"
    IDEATION = "ideation"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    REVIEW = "review"
    REVISION = "revision"  # Revision phase (iterative improvement)
    POLISH = "polish"
    EVALUATION = "evaluation"  # Final evaluation phase (FIG-MAC standards)
    FINISH = "finish"


@dataclass
class StateTransition:
    """State transition rules"""
    from_state: TeamState
    to_state: TeamState
    condition: str = "success"


class WorkflowHelper:
    """
    Workflow Helper Class
    Provides simple state transition assistance without changing existing core logic
    """
    
    def __init__(self):
        """Initialize workflow helper"""
        # Define standard state transition sequence
        self.standard_transitions = [
            StateTransition(TeamState.INIT, TeamState.LITERATURE),
            StateTransition(TeamState.LITERATURE, TeamState.IDEATION),
            StateTransition(TeamState.IDEATION, TeamState.ANALYSIS),
            StateTransition(TeamState.ANALYSIS, TeamState.SYNTHESIS),
            StateTransition(TeamState.SYNTHESIS, TeamState.REVIEW),
            StateTransition(TeamState.REVIEW, TeamState.POLISH),
            StateTransition(TeamState.POLISH, TeamState.EVALUATION),
            StateTransition(TeamState.EVALUATION, TeamState.FINISH),
        ]
        
        # Create transition mapping table
        self.transition_map = {
            transition.from_state: transition.to_state
            for transition in self.standard_transitions
        }
    
    def get_next_state(self, current_state: TeamState) -> TeamState:
        """
        Get next state
        
        Args:
            current_state: Current state
            
        Returns:
            TeamState: Next state
        """
        return self.transition_map.get(current_state, TeamState.FINISH)
    
    def is_valid_transition(self, from_state: TeamState, to_state: TeamState) -> bool:
        """
        Check if state transition is valid
        
        Args:
            from_state: Source state
            to_state: Target state
            
        Returns:
            bool: Whether transition is valid
        """
        expected_next = self.get_next_state(from_state)
        return to_state == expected_next
    
    def get_state_sequence(self) -> List[TeamState]:
        """
        Returns:
            List[TeamState]: Complete state sequence including iterative revision
        """
        # Return all states in correct order, including REVISION for completeness
        return [
            TeamState.INIT,
            TeamState.LITERATURE,
            TeamState.IDEATION,
            TeamState.ANALYSIS,
            TeamState.SYNTHESIS,
            TeamState.REVIEW,
            TeamState.REVISION,  # Iterative improvement phase
            TeamState.POLISH,
            TeamState.EVALUATION,
            TeamState.FINISH
        ]
    
    def get_state_progress(self, current_state: TeamState) -> Dict[str, any]:
        """
        Get progress information for current state
        
        Args:
            current_state: Current state
            
        Returns:
            Dict: Progress information
        """
        sequence = self.get_state_sequence()
        
        # Special handling for REVISION state (iterative, not in standard sequence)
        if current_state == TeamState.REVISION:
            # REVISION is between REVIEW and POLISH, treat as REVIEW progress
            review_index = sequence.index(TeamState.REVIEW)
            total_states = len(sequence)
            return {
                "current_state": current_state.value,
                "current_index": review_index,
                "total_states": total_states,
                "progress_percentage": (review_index / (total_states - 1)) * 100,
                "is_complete": False
            }
        
        try:
            current_index = sequence.index(current_state)
            total_states = len(sequence)
            
            return {
                "current_state": current_state.value,
                "current_index": current_index,
                "total_states": total_states,
                "progress_percentage": (current_index / (total_states - 1)) * 100,
                "is_complete": current_state == TeamState.FINISH
            }
        except ValueError:
            return {
                "current_state": current_state.value,
                "current_index": -1,
                "total_states": len(sequence),
                "progress_percentage": 0,
                "is_complete": False
            }


# Test helper class
if __name__ == "__main__":
    print("=== Workflow Helper Class Test ===")
    
    helper = WorkflowHelper()
    
    # Test state transitions
    print("Test state transition sequence:")
    current = TeamState.INIT
    while current != TeamState.FINISH:
        next_state = helper.get_next_state(current)
        print(f"  {current.value} -> {next_state.value}")
        current = next_state
    
    # Test progress calculation
    print("\nTest progress calculation:")
    for state in TeamState:
        progress = helper.get_state_progress(state)
        print(f"  {state.value}: {progress['progress_percentage']:.1f}%")
    
    print("\n✅ Workflow Helper Class test completed!")
