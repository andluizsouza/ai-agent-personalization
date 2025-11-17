"""
Tests for Planner Agent

Unit and integration tests for the orchestrator agent.
"""

import pytest
import os
from agents import create_planner_agent


class TestPlannerAgent:
    """Test suite for Planner Agent"""
    
    @pytest.fixture
    def agent(self):
        """Create a planner agent instance for testing."""
        return create_planner_agent(verbose=False)
    
    def test_initialization(self, agent):
        """Test that agent initializes correctly."""
        assert agent is not None
        assert agent.model_name == "gemini-2.5-flash"
        assert agent.temperature == 0
        assert len(agent.tools) == 3
        assert agent.llm is not None
        assert agent.agent_executor is not None
    
    def test_system_prompt_loaded(self, agent):
        """Test that system prompt is loaded from file."""
        assert agent.system_prompt is not None
        assert "PLANO DE EXECUÇÃO OBRIGATÓRIO" in agent.system_prompt
        assert "SAUDAÇÃO INICIAL" in agent.system_prompt
        assert "get_client_profile" in agent.system_prompt
        assert "search_breweries_by_location_and_type" in agent.system_prompt
        assert "get_website_summary" in agent.system_prompt
        assert "Assistente de Reabastecimento Inteligente da BEES" in agent.system_prompt
    
    def test_tools_registered(self, agent):
        """Test that all 3 tools are registered."""
        tool_names = [tool.name for tool in agent.tools]
        assert "get_client_profile_tool" in tool_names
        assert "search_breweries_tool" in tool_names
        assert "get_website_summary_tool" in tool_names
    
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="Requires GOOGLE_API_KEY environment variable"
    )
    def test_run_with_valid_client(self):
        """Test execution with valid client ID."""
        # Create fresh agent for this test
        agent = create_planner_agent(verbose=False)
        result = agent.run(client_id="CLT-LNU555")
        
        assert result is not None
        assert result["status"] == "success"
        assert "response" in result
        assert result["client_id"] == "CLT-LNU555"
        assert result["execution_time_s"] > 0
        assert result["tool_calls"] >= 2  # At least Tool 1 and Tool 2
        assert len(result["chain_of_thought"]) >= 2
    
    def test_get_metrics_no_execution(self, agent):
        """Test metrics before any execution."""
        metrics = agent.get_metrics()
        assert "message" in metrics
        assert metrics["message"] == "No executions yet"
    
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="Requires GOOGLE_API_KEY environment variable"
    )
    def test_get_metrics_after_execution(self):
        """Test metrics after execution."""
        # Create fresh agent
        agent = create_planner_agent(verbose=False)
        
        # Run agent
        agent.run(client_id="CLT-LNU555")
        
        # Get metrics
        metrics = agent.get_metrics()
        
        assert "total_execution_time_s" in metrics
        assert "total_tool_calls" in metrics
        assert "tools_breakdown" in metrics
        assert "cache_hit_rate" in metrics
        assert "avg_tool_execution_time_ms" in metrics
        
        # Validate breakdown
        breakdown = metrics["tools_breakdown"]
        assert breakdown["get_client_profile"] >= 1
        assert breakdown["search_breweries"] >= 1
    
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="Requires GOOGLE_API_KEY environment variable"
    )
    def test_chain_of_thought(self):
        """Test Chain-of-Thought trace generation."""
        # Create fresh agent
        agent = create_planner_agent(verbose=False)
        
        # Run agent
        agent.run(client_id="CLT-LNU555")
        
        # Get trace
        trace = agent.get_chain_of_thought()
        
        assert len(trace) >= 2
        
        # Validate first step (Tool 1)
        step1 = trace[0]
        assert step1["tool"] == "get_client_profile"
        assert "timestamp" in step1
        assert "execution_time_ms" in step1
        assert "status" in step1
        assert step1["input"]["client_id"] == "CLT-LNU555"
        
        # Validate second step (Tool 2)
        step2 = trace[1]
        assert step2["tool"] == "search_breweries_by_location_and_type"
        assert "city" in step2["input"]
        assert "state" in step2["input"]
        assert "brewery_type" in step2["input"]
    
    def test_invalid_client_id(self, agent):
        """Test execution with invalid client ID."""
        result = agent.run(client_id="INVALID-ID")
        
        # Agent should handle gracefully
        assert result is not None
        assert "response" in result


class TestPlannerSteps:
    """Test individual steps of the 5-step plan"""
    
    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        return create_planner_agent(verbose=False)
    
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="Requires GOOGLE_API_KEY environment variable"
    )
    def test_step1_client_profile(self):
        """Test Step 1: Get Client Profile"""
        # Create fresh agent for this test
        agent = create_planner_agent(verbose=False)
        result = agent.run(client_id="CLT-LNU555")
        
        # Check that Tool 1 was called
        tool1_calls = [
            log for log in result["chain_of_thought"] 
            if log["tool"] == "get_client_profile"
        ]
        assert len(tool1_calls) == 1
        assert tool1_calls[0]["status"] == "success"
    
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="Requires GOOGLE_API_KEY environment variable"
    )
    def test_step2_brewery_search(self):
        """Test Step 2: Search Breweries"""
        # Create fresh agent
        agent = create_planner_agent(verbose=False)
        result = agent.run(client_id="CLT-LNU555")
        
        # Check that Tool 2 was called
        tool2_calls = [
            log for log in result["chain_of_thought"] 
            if log["tool"] == "search_breweries_by_location_and_type"
        ]
        assert len(tool2_calls) == 1
        assert tool2_calls[0]["status"] == "success"
    
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="Requires GOOGLE_API_KEY environment variable"
    )
    def test_step3_initial_suggestion(self):
        """Test Step 3: Present Initial Suggestion"""
        # Create fresh agent
        agent = create_planner_agent(verbose=False)
        result = agent.run(client_id="CLT-LNU555")
        
        response = result["response"].lower()
        
        # Should mention beers
        assert any(word in response for word in ["cerveja", "beer"])
        
        # Should mention brewery name
        assert "barrel" in response or "brewing" in response
        
        # Should have conditional question
        assert "sim" in response and "não" in response
    
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="Requires GOOGLE_API_KEY environment variable - Manual test only"
    )
    def test_step4_conditional_question(self, agent):
        """Test Step 4: Conditional Question (Manual)"""
        # This test requires manual interaction
        # Run: python demo_planner.py --client_id CLT-LNU555
        pytest.skip("Manual test - requires user interaction")
    
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="Requires GOOGLE_API_KEY environment variable - Manual test only"
    )
    def test_step5_website_summary(self, agent):
        """Test Step 5: Website Summary (Manual)"""
        # This test requires confirming "yes" to conditional question
        pytest.skip("Manual test - requires user confirmation")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
