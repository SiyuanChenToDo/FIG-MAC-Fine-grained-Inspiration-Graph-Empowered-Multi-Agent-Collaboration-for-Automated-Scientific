#!/usr/bin/env python3
"""
Unified Tool Adapter
Based on CAMEL FunctionTool framework, provides standardized tool integration for existing HypothesisTeam

This is an auxiliary adapter for unifying different tool interfaces while maintaining all existing functionality
"""

import os
import sys
from typing import List, Any, Dict, Optional, Union
from pathlib import Path

from camel.toolkits import FunctionTool, SearchToolkit
from Myexamples.test_mutiagent.camel_logger_formatter import OutputFormatter

# Add project root directory to path for importing RAG system
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from Myexamples.agents.graph_agents import run_local_rag
except ImportError:
    OutputFormatter.warning("Cannot import run_local_rag, local RAG functionality will be unavailable")
    run_local_rag = None


class UnifiedToolAdapter:
    """
    Unified Tool Adapter - based on CAMEL FunctionTool framework
    
    Provides standardized tool acquisition interface, supports:
    1. CAMEL native SearchToolkit
    2. Local RAG system adaptation
    3. Other custom tool adaptation
    """
    
    @staticmethod
    def adapt_search_toolkit() -> List[FunctionTool]:
        """
        Adapt search toolkit to CAMEL standard format
        
        Returns:
            List[FunctionTool]: Standardized search tool list
        """
        try:
            search_toolkit = SearchToolkit()
            # SearchToolkit already returns FunctionTool list
            tools = search_toolkit.get_tools()
            OutputFormatter.info(f"SearchToolkit adaptation successful, obtained {len(tools)} tools")
            return tools
        except Exception as e:
            OutputFormatter.error(f"SearchToolkit adaptation failed: {e}")
            return []
    
    @staticmethod
    def adapt_local_rag(rag_function: Optional[callable] = None) -> List[FunctionTool]:
        """
        Adapt local RAG system to CAMEL standard format
        
        Args:
            rag_function: RAG function, defaults to run_local_rag
            
        Returns:
            List[FunctionTool]: Standardized RAG tool list
        """
        if rag_function is None:
            rag_function = run_local_rag
        
        if rag_function is None:
            OutputFormatter.warning("Local RAG functionality unavailable, skipping adaptation")
            return []
        
        try:
            # Wrap RAG function to match FunctionTool expected signature
            def run_local_rag_tool(query: str) -> str:
                """
                Run local RAG system, retrieve relevant information based on knowledge base
                
                Args:
                    query (str): Retrieval query content
                    
                Returns:
                    str: Retrieved relevant information
                """
                try:
                    result = rag_function(query)
                    return str(result) if result else "No relevant information found"
                except Exception as e:
                    OutputFormatter.error(f"RAG query failed: {e}")
                    return f"RAG query error: {str(e)}"
            
            # Create FunctionTool, let CAMEL automatically generate schema
            rag_tool = FunctionTool(run_local_rag_tool)
            
            OutputFormatter.info("Local RAG system adaptation successful")
            return [rag_tool]
            
        except Exception as e:
            OutputFormatter.error(f"Local RAG adaptation failed: {e}")
            return []
    
    @staticmethod
    def get_tools_for_agent(agent_type: str, custom_tools: Optional[List[Any]] = None) -> List[FunctionTool]:
        """
        Get standardized tool list for specified agent
        
        Args:
            agent_type: Agent type (scholar, ideator, analyst, synthesizer, reviewer, polisher)
            custom_tools: Custom tool list
            
        Returns:
            List[FunctionTool]: Standardized tool list
        """
        tools = []
        
        # Assign tools based on agent type
        agent_tool_mapping = {
            "scholar": ["search", "rag"],  # Scholar needs search and RAG
            "ideator": ["search"],         # Ideator needs search
            "analyst": ["search", "rag"],  # Analyst needs search and RAG
            "synthesizer": ["rag"],        # Synthesizer mainly needs RAG
            "reviewer": ["search"],        # Reviewer needs search
            "polisher": []                 # Polisher doesn't need external tools
        }
        
        required_tools = agent_tool_mapping.get(agent_type.lower(), [])
        
        # Add search tools
        if "search" in required_tools:
            search_tools = UnifiedToolAdapter.adapt_search_toolkit()
            tools.extend(search_tools)
        
        # Add RAG tools
        if "rag" in required_tools:
            rag_tools = UnifiedToolAdapter.adapt_local_rag()
            tools.extend(rag_tools)
        
        # Handle custom tools
        if custom_tools:
            for tool in custom_tools:
                if isinstance(tool, FunctionTool):
                    tools.append(tool)
                elif hasattr(tool, 'get_tools'):  # Like SearchToolkit
                    tools.extend(tool.get_tools())
                else:
                    OutputFormatter.warning(f"Unknown tool type, skipping: {type(tool)}")
        
        OutputFormatter.info(f"Adapted {len(tools)} tools for {agent_type} agent")
        return tools
    
    @staticmethod
    def adapt_legacy_tools(legacy_tools: List[Any]) -> List[FunctionTool]:
        """
        Adapt legacy tools to CAMEL standard format
        
        Args:
            legacy_tools: Legacy tool list
            
        Returns:
            List[FunctionTool]: Standardized tool list
        """
        adapted_tools = []
        
        for tool in legacy_tools:
            try:
                if isinstance(tool, FunctionTool):
                    # Already in standard format
                    adapted_tools.append(tool)
                elif isinstance(tool, SearchToolkit):
                    # SearchToolkit needs to call get_tools()
                    adapted_tools.extend(tool.get_tools())
                elif hasattr(tool, 'get_tools'):
                    # Other tools with get_tools method
                    adapted_tools.extend(tool.get_tools())
                elif callable(tool):
                    # Callable object, try to wrap as FunctionTool
                    OutputFormatter.warning(f"Attempting to adapt callable tool: {tool.__name__ if hasattr(tool, '__name__') else str(tool)}")
                    # More complex adaptation logic can be added here
                else:
                    OutputFormatter.warning(f"Cannot adapt tool type: {type(tool)}")
                    
            except Exception as e:
                OutputFormatter.error(f"Tool adaptation failed: {e}")
                continue
        
        OutputFormatter.info(f"Adapted {len(adapted_tools)}/{len(legacy_tools)} legacy tools")
        return adapted_tools
    
    @staticmethod
    def get_tool_summary(tools: List[FunctionTool]) -> Dict[str, Any]:
        """
        Get tool list summary
        
        Args:
            tools: Tool list
            
        Returns:
            Dict: Tool summary information
        """
        summary = {
            "total_count": len(tools),
            "tool_names": [],
            "tool_descriptions": {}
        }
        
        for tool in tools:
            if hasattr(tool, 'get_openai_function_schema'):
                schema = tool.get_openai_function_schema()
                name = schema.get('name', 'unknown')
                description = schema.get('description', 'No description')
                
                summary["tool_names"].append(name)
                summary["tool_descriptions"][name] = description
        
        return summary


# Compatibility function, maintain compatibility with existing code
def get_standard_tools_for_agent(agent_name: str) -> List[FunctionTool]:
    """
    Compatibility function: Get standard tools for agent
    
    Args:
        agent_name: Agent name
        
    Returns:
        List[FunctionTool]: Standardized tool list
    """
    # Map agent names to types
    name_to_type_mapping = {
        "Scholar Scour": "scholar",
        "Idea Igniter": "ideator", 
        "Analysis Ace": "analyst",
        "Synthesis Sage": "synthesizer",
        "Review Ranger": "reviewer",
        "Polish Pro": "polisher"
    }
    
    agent_type = name_to_type_mapping.get(agent_name, "scholar")  # Default to scholar
    return UnifiedToolAdapter.get_tools_for_agent(agent_type)


# Test functionality
if __name__ == "__main__":
    print("=== Unified Tool Adapter Test ===")
    
    # Test SearchToolkit adaptation
    print("\n1. Test SearchToolkit adaptation:")
    search_tools = UnifiedToolAdapter.adapt_search_toolkit()
    print(f"Obtained {len(search_tools)} search tools")
    
    # Test RAG adaptation
    print("\n2. Test local RAG adaptation:")
    rag_tools = UnifiedToolAdapter.adapt_local_rag()
    print(f"Obtained {len(rag_tools)} RAG tools")
    
    # Test agent tool acquisition
    print("\n3. Test agent tool acquisition:")
    for agent_type in ["scholar", "ideator", "analyst"]:
        tools = UnifiedToolAdapter.get_tools_for_agent(agent_type)
        summary = UnifiedToolAdapter.get_tool_summary(tools)
        print(f"{agent_type}: {summary['total_count']} tools - {summary['tool_names']}")
    
    # Test compatibility function
    print("\n4. Test compatibility function:")
    compat_tools = get_standard_tools_for_agent("Scholar Scour")
    print(f"Scholar Scour compatibility tools: {len(compat_tools)} tools")
    
    OutputFormatter.success("Unified Tool Adapter test completed")
