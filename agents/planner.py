"""
Planner Agent - Orchestrator

This agent orchestrates the 5-step plan for brewery recommendations:
1. Get client profile (Tool 1)
2. Search new breweries (Tool 2)
3. Present initial suggestion
4. Ask conditional question (cost optimization)
5. Get detailed summary (Tool 3) - only if user says yes

Features:
- LangChain AgentExecutor with Gemini 2.5 Flash
- Function calling with 3 registered tools
- Conditional logic for cost optimization
- Chain-of-Thought logging
- Execution metrics tracking
"""

import os
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from tools.sql_runner import get_client_profile
from tools.brewery_finder import search_breweries_by_location_and_type
from tools.web_explorer import get_website_summary
from utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    Orchestrator agent that manages the complete workflow for brewery recommendations.
    
    Implements the Plan-and-Execute pattern with 5 mandatory steps:
    1. Retrieve client profile
    2. Search new breweries
    3. Present initial suggestion
    4. Ask conditional question (30s timeout)
    5. Get detailed summary (only if user confirms)
    
    This agent uses Gemini 2.5 Flash with function calling to coordinate
    the 3 tools and implements cost optimization through conditional execution.
    """
    
    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0,
        verbose: bool = False
    ):
        """
        Initialize the Planner Agent.
        
        Args:
            model_name: Gemini model to use
            temperature: LLM temperature (0 for deterministic)
            verbose: Enable verbose logging
        """
        self.model_name = model_name
        self.temperature = temperature
        self.verbose = verbose
        
        # Validate API Key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        # Load system prompt
        try:
            self.system_prompt = load_prompt('planner.txt')
            logger.info("Loaded planner system prompt")
        except Exception as e:
            logger.error(f"Failed to load planner prompt: {e}")
            raise
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            convert_system_message_to_human=True
        )
        logger.info(f"Initialized Gemini model: {model_name}")
        
        # Create tools
        self.tools = self._create_tools()
        logger.info(f"Registered {len(self.tools)} tools")
        
        # Create agent
        self.agent_executor = self._create_agent()
        logger.info("Planner Agent initialized successfully")
        
        # Execution metrics
        self.execution_log: List[Dict] = []
        self.total_execution_time: float = 0
        
    def _create_tools(self) -> List:
        """
        Create and register the 3 tools with LangChain.
        
        Returns:
            List of LangChain tools
        """
        
        @tool
        def get_client_profile_tool(client_id: str) -> str:
            """
            Retrieve client profile from database.
            
            Use this tool to get customer information including:
            - Client location (city, state, postal code)
            - Top 3 preferred brewery types
            - Top 5 recently ordered beers
            - Brewery purchase history
            
            Args:
                client_id: The unique client identifier (e.g., 'CLT-LNU555')
            
            Returns:
                JSON string with client profile or error message
            """
            logger.info(f"Tool 1 called: get_client_profile(client_id={client_id})")
            start_time = time.time()
            
            try:
                result = get_client_profile(client_id)
                execution_time = (time.time() - start_time) * 1000
                
                # Log execution
                self.execution_log.append({
                    "tool": "get_client_profile",
                    "timestamp": datetime.now().isoformat(),
                    "input": {"client_id": client_id},
                    "execution_time_ms": execution_time,
                    "status": "success" if not result.get("error") else "error"
                })
                
                return str(result)
            except Exception as e:
                logger.error(f"Tool 1 failed: {e}")
                return str({"error": "TOOL_ERROR", "message": str(e)})
        
        @tool
        def search_breweries_tool(
            city: Optional[str] = None,
            state: Optional[str] = None,
            brewery_type: Optional[str] = None,
            brewery_history: Optional[List[str]] = None,
            brewery_name: Optional[str] = None,
            filter_history: bool = True
        ) -> str:
            """
            Search for breweries by location, type, or specific name. Returns comprehensive information.
            
            This tool can search for NEW breweries (with filtering) or get information about 
            KNOWN breweries (without filtering).
            
            Args:
                city: City name (optional if brewery_name provided, e.g., 'San Diego', 'Bend')
                state: State name (optional, e.g., 'California', 'Oregon')
                brewery_type: Type of brewery (optional, e.g., 'micro', 'brewpub', 'regional')
                brewery_history: List of brewery names to filter out (only used if filter_history=True)
                brewery_name: Specific brewery name to search for (optional)
                filter_history: True to exclude known breweries (new recommendations), 
                               False to include all (for known brewery info lookup)
            
            Returns:
                JSON string with comprehensive brewery information including:
                - Name, type, ID
                - Complete address (address_1, address_2, address_3, street)
                - City, state, postal code, country
                - Phone number, website URL
                - Coordinates (latitude, longitude)
                - "Unavailable" for missing fields
            
            Examples:
                - New recommendations: city="San Diego", filter_history=True
                - Favorite brewery info: brewery_name="Odell Brewing", filter_history=False
                - Phone number: brewery_name="Stone Brewing", filter_history=False
            """
            logger.info(f"Tool 2 called: search_breweries(city={city}, state={state}, type={brewery_type}, name={brewery_name}, filter={filter_history})")
            start_time = time.time()
            
            try:
                # Set default for brewery_history
                if brewery_history is None:
                    brewery_history = []
                
                result = search_breweries_by_location_and_type(
                    city=city,
                    state=state,
                    brewery_type=brewery_type,
                    brewery_history=brewery_history,
                    brewery_name=brewery_name,
                    filter_history=filter_history
                )
                execution_time = (time.time() - start_time) * 1000
                
                # Log execution
                self.execution_log.append({
                    "tool": "search_breweries_by_location_and_type",
                    "timestamp": datetime.now().isoformat(),
                    "input": {
                        "city": city,
                        "state": state,
                        "brewery_type": brewery_type,
                        "brewery_name": brewery_name,
                        "filter_history": filter_history,
                        "history_count": len(brewery_history)
                    },
                    "execution_time_ms": execution_time,
                    "status": "success" if not result.get("error") else "error"
                })
                
                return str(result)
            except Exception as e:
                logger.error(f"Tool 2 failed: {e}")
                return str({"error": "TOOL_ERROR", "message": str(e)})
        
        @tool
        def get_website_summary_tool(brewery_name: str, url: str, brewery_type: str, address: str) -> str:
            """
            Get detailed summary of a brewery website.
            
            This tool uses RAG cache with TTL (30 days) to optimize costs.
            Falls back to Google Search + Gemini Grounding if cache misses.
            
            Args:
                brewery_name: Name of the brewery
                url: Website URL
                brewery_type: Type of brewery
                address: Full address for precise search
            
            Returns:
                JSON string with summary and metadata
            """
            logger.info(f"Tool 3 called: get_website_summary(brewery={brewery_name})")
            start_time = time.time()
            
            try:
                result = get_website_summary(
                    brewery_name=brewery_name,
                    url=url,
                    brewery_type=brewery_type,
                    address=address
                )
                execution_time = (time.time() - start_time) * 1000
                
                # Log execution
                self.execution_log.append({
                    "tool": "get_website_summary",
                    "timestamp": datetime.now().isoformat(),
                    "input": {
                        "brewery_name": brewery_name,
                        "url": url
                    },
                    "cache_status": result.get("cache_status", "unknown"),
                    "execution_time_ms": execution_time,
                    "status": "success" if not result.get("error") else "error"
                })
                
                return str(result)
            except Exception as e:
                logger.error(f"Tool 3 failed: {e}")
                return str({"error": "TOOL_ERROR", "message": str(e)})
        
        return [get_client_profile_tool, search_breweries_tool, get_website_summary_tool]
    
    def _create_agent(self) -> AgentExecutor:
        """
        Create the LangChain agent with tools and prompt.
        
        Returns:
            AgentExecutor instance
        """
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        
        # Create executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=self.verbose,
            handle_parsing_errors=True,
            max_iterations=10
        )
        
        return agent_executor
    
    def run(self, client_id: str, chat_history: Optional[List] = None) -> Dict:
        """
        Execute the complete 5-step plan for a client.
        
        Args:
            client_id: Client identifier
            chat_history: Optional conversation history
            
        Returns:
            Dictionary with response and execution metadata
        """
        start_time = time.time()
        self.execution_log = []  # Reset log
        
        try:
            logger.info(f"Starting planner execution for client: {client_id}")
            
            # Filter chat history to get only the last user message
            # This prevents the agent from being confused by previous responses
            if chat_history:
                # Get only the last user message
                user_messages = [msg for msg in chat_history if msg.get("role") == "user"]
                if user_messages:
                    last_user_message = user_messages[-1].get("content", "")
                    # Build input with client_id context
                    input_message = f"Client ID: {client_id}\n\nMensagem do usuário: {last_user_message}"
                else:
                    input_message = f"O client_id é: {client_id}. Execute o plano completo de 5 passos para fazer a recomendação."
            else:
                input_message = f"O client_id é: {client_id}. Execute o plano completo de 5 passos para fazer a recomendação."
            
            # Execute agent WITHOUT full history to avoid confusion
            # The agent should focus on the current request with the confirmed client_id
            result = self.agent_executor.invoke({
                "input": input_message,
                "chat_history": []  # Empty history to prevent confusion
            })
            
            execution_time = time.time() - start_time
            self.total_execution_time = execution_time
            
            logger.info(f"Planner execution completed in {execution_time:.2f}s")
            
            return {
                "response": result.get("output", ""),
                "client_id": client_id,
                "execution_time_s": execution_time,
                "tool_calls": len(self.execution_log),
                "chain_of_thought": self.execution_log,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Planner execution failed: {e}")
            return {
                "response": f"Erro ao executar o plano: {str(e)}",
                "client_id": client_id,
                "execution_time_s": time.time() - start_time,
                "tool_calls": len(self.execution_log),
                "chain_of_thought": self.execution_log,
                "status": "error",
                "error": str(e)
            }
    
    def get_metrics(self) -> Dict:
        """
        Get execution metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.execution_log:
            return {"message": "No executions yet"}
        
        # Calculate cache hit rate for Tool 3
        tool3_calls = [log for log in self.execution_log if log["tool"] == "get_website_summary"]
        cache_hits = sum(1 for log in tool3_calls if log.get("cache_status") == "CACHE_HIT")
        cache_hit_rate = cache_hits / len(tool3_calls) if tool3_calls else 0
        
        return {
            "total_execution_time_s": self.total_execution_time,
            "total_tool_calls": len(self.execution_log),
            "tools_breakdown": {
                "get_client_profile": len([l for l in self.execution_log if l["tool"] == "get_client_profile"]),
                "search_breweries": len([l for l in self.execution_log if l["tool"] == "search_breweries_by_location_and_type"]),
                "get_website_summary": len(tool3_calls)
            },
            "cache_hit_rate": cache_hit_rate,
            "avg_tool_execution_time_ms": sum(l.get("execution_time_ms", 0) for l in self.execution_log) / len(self.execution_log)
        }
    
    def get_chain_of_thought(self) -> List[Dict]:
        """
        Get the complete Chain-of-Thought trace.
        
        Returns:
            List of tool executions with inputs/outputs
        """
        return self.execution_log


# Convenience function
def create_planner_agent(verbose: bool = False) -> PlannerAgent:
    """
    Create a PlannerAgent instance.
    
    Args:
        verbose: Enable verbose logging
        
    Returns:
        PlannerAgent instance
    """
    return PlannerAgent(verbose=verbose)
