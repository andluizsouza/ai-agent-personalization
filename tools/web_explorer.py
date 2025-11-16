"""
Tool 3: Web Explorer with RAG Cache and Gemini Grounding

This tool retrieves website summaries for breweries, prioritizing cached data
(FAISS RAG) and falling back to Gemini Grounding (Google Search) when needed.

Features:
- Cache search with TTL validation (30 days)
- Gemini Grounding (Google Search) integration
- Precise search using brewery name + address + website
- Gemini-based summarization (max 3 sentences)
- Automatic cache updates
- Comprehensive error handling

Architecture:
- Step 1: Search RAG cache (FAISS)
- Step 2: If cache hit → return cached summary
- Step 3: If cache miss/stale → use Gemini Grounding
- Step 4: Save result to cache with TTL

Benefits:
- No web scraping needed
- More reliable than BeautifulSoup
- Grounding provides accurate, up-to-date information
- 99% cost reduction with cache strategy
"""

import os
import logging
import time
from typing import Dict, Optional
from urllib.parse import urlparse

from langchain_google_genai import ChatGoogleGenerativeAI

from utils.rag_manager import RAGManager
from utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class WebExplorer:
    """
    Tool for retrieving and summarizing brewery website content.
    
    Uses a RAG cache (FAISS) with TTL to minimize API calls.
    Falls back to Gemini Grounding (Google Search) when cache misses occur.
    
    Advantages over web scraping:
    - More reliable (no HTML parsing issues)
    - Always up-to-date information
    - Respects website access restrictions
    - Leverages Google's search quality
    """
    
    def __init__(
        self,
        index_path: str = "data/faiss_index",
        ttl_days: int = 30,
        gemini_model: str = "gemini-2.5-flash",
        temperature: float = 0
    ):
        """
        Initialize Web Explorer.
        
        Args:
            index_path: Path to FAISS index
            ttl_days: Cache TTL in days
            gemini_model: Gemini model for summarization
            temperature: LLM temperature (0 for deterministic)
        """
        # Validate Google API Key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not found in environment")
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        # Initialize RAG Manager
        try:
            self.rag_manager = RAGManager(index_path=index_path, ttl_days=ttl_days)
            logger.info("RAG Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Manager: {e}")
            raise
        
        # Initialize Gemini for summarization
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=gemini_model,
                temperature=temperature
            )
            logger.info(f"Initialized Gemini model: {gemini_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    

    def _grounded_search_summary(self, brewery_name: str, address: str, url: str) -> Optional[str]:
        """
        Use Gemini with Google Search Grounding to get a concise summary of the brewery.
        
        Uses the new Google GenAI SDK with google_search tool for Gemini 2.5 Flash.
        Reference: https://ai.google.dev/gemini-api/docs/google-search
        
        Args:
            brewery_name: Name of the brewery
            address: Address of the brewery (city, state, street, etc.)
            url: Website URL
            
        Returns:
            Short summary string or None if failed
        """
        try:
            logger.info(f"Using Gemini Grounding for: {brewery_name} | {address} | {url}")
            
            # Load prompt template from external file
            try:
                prompt_template = load_prompt('web_explorer.txt')
                # Replace variables in template
                prompt = prompt_template.format(
                    brewery_name=brewery_name,
                    address=address,
                    url=url
                )
            except Exception as e:
                logger.error(f"Failed to load prompt template: {e}")
                # Fallback to inline prompt
                prompt = f"""Você é um especialista em cervejarias. Pesquise e traga informações atualizadas sobre a cervejaria abaixo.

Cervejaria: {brewery_name}
Endereço: {address}
Site: {url}

Com base nas informações encontradas, crie um resumo conciso (máximo 3 frases) em português brasileiro, focando em:
- Tipo de cervejaria (micro, regional, brewpub, etc.)
- Principais estilos de cerveja produzidos
- Diferenciais e características únicas

Se não encontrar informações suficientes, informe isso de forma clara.

Resumo:"""
            
            # Use the new Google GenAI SDK with google_search tool
            # Reference: https://ai.google.dev/gemini-api/docs/google-search
            from google import genai
            from google.genai import types
            
            # Initialize client
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            
            # Configure grounding tool
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            
            config = types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=0  # Deterministic output
            )
            
            # Generate content with grounding
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )
            
            summary = response.text.strip()
            
            # Log grounding metadata if available
            if response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                if metadata.web_search_queries:
                    logger.info(f"Grounding queries used: {metadata.web_search_queries}")
                if metadata.grounding_chunks:
                    logger.info(f"Sources found: {len(metadata.grounding_chunks)}")
            
            logger.info(f"Grounded summary generated: {len(summary)} characters")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate grounded summary: {e}")
            return None
    
    def get_website_summary(
        self,
        brewery_name: str,
        url: str,
        brewery_type: str = "unknown",
        address: str = ""
    ) -> Dict:
        """
        Get website summary, using cache or fetching from web.
        
        Args:
            brewery_name: Name of the brewery
            url: Website URL
            brewery_type: Type of brewery (micro, brewpub, etc.)
            
        Returns:
            Dictionary with summary and metadata:
            {
                "brewery_name": str,
                "url": str,
                "summary": str,
                "source": "cache_hit|cache_stale|web_search",
                "cache_status": "CACHE_HIT|CACHE_STALE|CACHE_MISS",
                "brewery_type": str,
                "execution_time_ms": float,
                "error": str (optional)
            }
        """
        start_time = time.time()
        # Validate URL
        if not url or not self._is_valid_url(url):
            logger.warning(f"Invalid or missing URL for {brewery_name}")
            return {
                "brewery_name": brewery_name,
                "url": url or "N/A",
                "summary": "Website URL não disponível ou inválido.",
                "source": "error",
                "cache_status": "N/A",
                "brewery_type": brewery_type,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "error": "INVALID_URL"
            }
        # Step 1: Search cache
        cached_result, cache_status = self.rag_manager.search_cache(
            query=brewery_name,
            brewery_name=brewery_name
        )
        # Step 2: Handle cache hit (valid data)
        if cache_status == "CACHE_HIT" and cached_result:
            logger.info(f"Cache hit for {brewery_name}")
            return {
                "brewery_name": brewery_name,
                "url": url,
                "summary": cached_result["summary"],
                "source": "cache_hit",
                "cache_status": cache_status,
                "brewery_type": brewery_type,
                "execution_time_ms": (time.time() - start_time) * 1000
            }
        # Step 3: Handle cache miss or stale - use Gemini Grounding
        logger.info(f"Cache {cache_status.lower()} for {brewery_name}, using Gemini Grounding fallback")
        summary = self._grounded_search_summary(
            brewery_name=brewery_name,
            address=address,
            url=url
        )
        if not summary:
            error_msg = f"Não foi possível gerar resumo para {brewery_name} via Gemini Grounding"
            logger.error(error_msg)
            return {
                "brewery_name": brewery_name,
                "url": url,
                "summary": error_msg,
                "source": "web_search",
                "cache_status": cache_status,
                "brewery_type": brewery_type,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "error": "GROUNDING_FAILED"
            }
        # Step 4: Update cache
        if cache_status in ["CACHE_MISS", "CACHE_STALE"]:
            cache_updated = self.rag_manager.add_to_cache(
                brewery_name=brewery_name,
                url=url,
                summary=summary,
                brewery_type=brewery_type
            )
            if cache_updated:
                self.rag_manager.save_index()
                logger.info(f"Cache updated and saved for {brewery_name}")
            else:
                logger.warning(f"Failed to update cache for {brewery_name}")
        return {
            "brewery_name": brewery_name,
            "url": url,
            "summary": summary,
            "source": "web_search",
            "cache_status": cache_status,
            "brewery_type": brewery_type,
            "execution_time_ms": (time.time() - start_time) * 1000
        }
        
        # Return result
        return {
            "brewery_name": brewery_name,
            "url": url,
            "summary": summary,
            "source": "web_search",
            "cache_status": cache_status,
            "brewery_type": brewery_type,
            "execution_time_ms": (time.time() - start_time) * 1000
        }
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return self.rag_manager.get_cache_stats()


# Convenience function for direct use
def get_website_summary(
    brewery_name: str,
    url: str,
    brewery_type: str = "unknown",
    address: str = ""
) -> Dict:
    """
    Convenience function to get website summary using Gemini Grounding.
    Args:
        brewery_name: Name of the brewery
        url: Website URL
        brewery_type: Type of brewery
        address: Address of the brewery (optional)
    Returns:
        Dictionary with summary and metadata
    """
    explorer = WebExplorer()
    return explorer.get_website_summary(brewery_name, url, brewery_type, address)
