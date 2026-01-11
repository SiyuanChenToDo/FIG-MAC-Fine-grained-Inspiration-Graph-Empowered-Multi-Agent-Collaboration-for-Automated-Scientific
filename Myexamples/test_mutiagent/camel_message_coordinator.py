#!/usr/bin/env python3
"""
CAMEL Native Message Coordinator
Replaces custom HypothesisChannel, uses CAMEL framework's native message passing mechanism

Based on CAMEL BaseMessage and TaskChannel design, provides more standardized message passing
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole
from camel.logger import get_logger


class MessageType(Enum):
    """Message type enumeration"""
    COORDINATION = "coordination"  # Coordination messages
    TASK_ASSIGNMENT = "task_assignment"  # Task assignment
    RESULT_SHARING = "result_sharing"  # Result sharing
    STATUS_UPDATE = "status_update"  # Status updates


class CamelMessageCoordinator:
    """
    Message coordinator based on CAMEL native mechanisms
    Simplified message passing, focused on team coordination and status synchronization
    """
    
    def __init__(self, team_name: str = "hypothesis_team"):
        """
        Initialize CAMEL message coordinator
        
        Args:
            team_name: Team name, used for log identification
        """
        self.team_name = team_name
        self.logger = get_logger(f"message_coordinator.{team_name}")
        
        # Message history record - using CAMEL native BaseMessage
        self.message_history: List[BaseMessage] = []
        
        # Team status tracking
        self.team_status: Dict[str, Any] = {
            "current_phase": "init",
            "active_agents": [],
            "completed_tasks": [],
            "start_time": datetime.now()
        }
        
        self.logger.info(f"CAMEL Message Coordinator initialized for team: {team_name}")
    
    def create_coordination_message(
        self, 
        sender: str, 
        content: str, 
        message_type: MessageType = MessageType.COORDINATION,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BaseMessage:
        """
        Create standardized coordination message
        
        Args:
            sender: Sender identifier
            content: Message content
            message_type: Message type
            metadata: Additional metadata
            
        Returns:
            BaseMessage: CAMEL native message object
        """
        # Build metadata
        meta_dict = {
            "message_type": message_type.value,
            "sender": sender,
            "timestamp": datetime.now().isoformat(),
            "team": self.team_name
        }
        
        if metadata:
            meta_dict.update(metadata)
        
        # Create CAMEL native message
        message = BaseMessage(
            role_name=sender,
            role_type=OpenAIBackendRole.ASSISTANT,
            meta_dict=meta_dict,
            content=content
        )
        
        # Record to history
        self.message_history.append(message)
        
        self.logger.debug(f"Created {message_type.value} message from {sender}")
        return message
    
    def broadcast_phase_transition(
        self, 
        new_phase: str, 
        active_agents: List[str],
        phase_description: str = ""
    ) -> BaseMessage:
        """
        Broadcast phase transition message
        
        Args:
            new_phase: New phase name
            active_agents: Active agent list
            phase_description: Phase description
            
        Returns:
            BaseMessage: Phase transition message
        """
        # Update team status
        self.team_status.update({
            "current_phase": new_phase,
            "active_agents": active_agents,
            "phase_start_time": datetime.now()
        })
        
        content = f"Phase transition: {new_phase}"
        if phase_description:
            content += f" - {phase_description}"
        
        message = self.create_coordination_message(
            sender="Team Coordinator",
            content=content,
            message_type=MessageType.STATUS_UPDATE,
            metadata={
                "phase": new_phase,
                "active_agents": active_agents,
                "phase_description": phase_description
            }
        )
        
        self.logger.info(f"Phase transition broadcasted: {new_phase}")
        return message
    
    def share_task_result(
        self, 
        agent_name: str, 
        task_type: str, 
        result_summary: str,
        success: bool = True
    ) -> BaseMessage:
        """
        Share task result
        
        Args:
            agent_name: Agent name
            task_type: Task type
            result_summary: Result summary
            success: Whether successful
            
        Returns:
            BaseMessage: Result sharing message
        """
        content = f"Task completed: {task_type}"
        if not success:
            content = f"Task failed: {task_type}"
        
        message = self.create_coordination_message(
            sender=agent_name,
            content=content,
            message_type=MessageType.RESULT_SHARING,
            metadata={
                "task_type": task_type,
                "result_summary": result_summary,
                "success": success,
                "agent": agent_name
            }
        )
        
        # Update completed task list
        if success:
            self.team_status["completed_tasks"].append({
                "agent": agent_name,
                "task": task_type,
                "timestamp": datetime.now().isoformat()
            })
        
        self.logger.info(f"Task result shared: {agent_name} - {task_type} ({'success' if success else 'failed'})")
        return message
    
    def get_team_status(self) -> Dict[str, Any]:
        """Get team status"""
        return self.team_status.copy()
    
    def get_message_history(
        self, 
        message_type: Optional[MessageType] = None,
        sender: Optional[str] = None
    ) -> List[BaseMessage]:
        """
        Get message history
        
        Args:
            message_type: Filter message type
            sender: Filter sender
            
        Returns:
            List[BaseMessage]: Filtered message list
        """
        messages = self.message_history.copy()
        
        if message_type:
            messages = [
                msg for msg in messages 
                if msg.meta_dict.get("message_type") == message_type.value
            ]
        
        if sender:
            messages = [
                msg for msg in messages 
                if msg.meta_dict.get("sender") == sender
            ]
        
        return messages
    
    def get_coordination_summary(self) -> str:
        """
        Get coordination summary
        
        Returns:
            str: Team coordination summary
        """
        status = self.team_status
        total_messages = len(self.message_history)
        completed_tasks = len(status["completed_tasks"])
        
        duration = datetime.now() - status["start_time"]
        
        summary = f"""
CAMEL Message Coordinator Summary - Team: {self.team_name}
================================================================
Current Phase: {status['current_phase']}
Active Agents: {', '.join(status.get('active_agents', []))}
Completed Tasks: {completed_tasks}
Total Messages: {total_messages}
Duration: {duration}
================================================================
        """.strip()
        
        return summary


# 测试和演示
if __name__ == "__main__":
    # 测试CAMEL消息协调器
    coordinator = CamelMessageCoordinator("test_team")
    
    print("=== CAMEL Message Coordinator 测试 ===")
    
    # 测试阶段转换
    msg1 = coordinator.broadcast_phase_transition(
        "literature_review", 
        ["Scholar Scour"], 
        "开始文献综述阶段"
    )
    print(f"Phase message: {msg1.content}")
    
    # 测试结果共享
    msg2 = coordinator.share_task_result(
        "Scholar Scour", 
        "literature_review", 
        "完成了全面的文献综述",
        success=True
    )
    print(f"Result message: {msg2.content}")
    
    # 测试状态获取
    status = coordinator.get_team_status()
    print(f"Team status: {status['current_phase']}")
    
    # 测试摘要
    print("\n" + coordinator.get_coordination_summary())
