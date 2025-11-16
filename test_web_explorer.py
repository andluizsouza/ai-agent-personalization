"""
Unit tests for Tool 3: Web Explorer

Tests cover:
- RAG Manager initialization and FAISS operations
- Cache hit/miss/stale scenarios
- Gemini Grounding (Google Search) integration
- Gemini summarization
- Cache persistence
- Error handling
"""

import os
import time
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import shutil

from tools.web_explorer import WebExplorer, get_website_summary
from utils.rag_manager import RAGManager


class TestRAGManager:
    """Test suite for RAG Manager"""
    
    @pytest.fixture
    def temp_index_path(self, tmp_path):
        """Create temporary index path for testing"""
        index_path = tmp_path / "test_faiss_index"
        yield str(index_path)
        # Cleanup
        if index_path.exists():
            shutil.rmtree(index_path)
    
    def test_initialization(self, temp_index_path):
        """Test RAG Manager initialization"""
        # Verify GOOGLE_API_KEY exists
        assert os.getenv("GOOGLE_API_KEY"), "GOOGLE_API_KEY not set"
        
        # Initialize
        rag = RAGManager(index_path=temp_index_path)
        
        # Verify attributes
        assert rag.ttl_days == 30
        assert rag.embedding_model == "models/embedding-001"
        assert rag.vectorstore is not None
        
        print("PASSED: RAG Manager initialized successfully")
    
    def test_cache_miss(self, temp_index_path):
        """Test cache miss scenario"""
        rag = RAGManager(index_path=temp_index_path)
        
        result, status = rag.search_cache("Nonexistent Brewery")
        
        assert status == "CACHE_MISS"
        assert result is None
        
        print("PASSED: Cache miss detected correctly")
    
    def test_add_to_cache(self, temp_index_path):
        """Test adding entry to cache"""
        rag = RAGManager(index_path=temp_index_path)
        
        success = rag.add_to_cache(
            brewery_name="Test Brewery",
            url="https://testbrewery.com",
            summary="This is a test brewery with great beers.",
            brewery_type="micro"
        )
        
        assert success is True
        
        # Verify it can be found
        result, status = rag.search_cache("Test Brewery")
        assert status == "CACHE_HIT"
        assert result is not None
        assert result["brewery_name"] == "Test Brewery"
        
        print("PASSED: Entry added to cache successfully")
    
    def test_cache_hit(self, temp_index_path):
        """Test cache hit with valid data"""
        rag = RAGManager(index_path=temp_index_path)
        
        # Add entry
        rag.add_to_cache(
            brewery_name="Modern Times Beer",
            url="https://moderntimesbeer.com",
            summary="Modern Times Beer is a craft brewery known for IPAs.",
            brewery_type="micro"
        )
        
        # Search
        result, status = rag.search_cache("Modern Times Beer")
        
        assert status == "CACHE_HIT"
        assert result is not None
        assert "Modern Times" in result["brewery_name"]
        assert result["url"] == "https://moderntimesbeer.com"
        assert len(result["summary"]) > 0
        
        print(f"PASSED: Cache hit with summary: {result['summary'][:50]}...")
    
    def test_cache_persistence(self, temp_index_path):
        """Test saving and loading FAISS index"""
        # Create and populate index
        rag1 = RAGManager(index_path=temp_index_path)
        rag1.add_to_cache(
            brewery_name="Persistent Brewery",
            url="https://persistent.com",
            summary="This brewery persists across sessions.",
            brewery_type="brewpub"
        )
        rag1.save_index()
        
        # Load in new instance
        rag2 = RAGManager(index_path=temp_index_path)
        result, status = rag2.search_cache("Persistent Brewery")
        
        assert status == "CACHE_HIT"
        assert result["brewery_name"] == "Persistent Brewery"
        
        print("PASSED: Index persisted and loaded successfully")
    
    def test_cache_stats(self, temp_index_path):
        """Test cache statistics"""
        rag = RAGManager(index_path=temp_index_path)
        
        # Add some entries
        for i in range(3):
            rag.add_to_cache(
                brewery_name=f"Brewery {i}",
                url=f"https://brewery{i}.com",
                summary=f"Summary for brewery {i}",
                brewery_type="micro"
            )
        
        stats = rag.get_cache_stats()
        
        assert stats["total_entries"] >= 3
        assert stats["ttl_days"] == 30
        assert "index_path" in stats
        
        print(f"PASSED: Cache stats: {stats}")


class TestWebExplorer:
    """Test suite for Web Explorer"""
    
    @pytest.fixture
    def temp_index_path(self, tmp_path):
        """Create temporary index path for testing"""
        index_path = tmp_path / "test_web_index"
        yield str(index_path)
        # Cleanup
        if index_path.exists():
            shutil.rmtree(index_path)
    
    def test_initialization(self, temp_index_path):
        """Test Web Explorer initialization"""
        explorer = WebExplorer(index_path=temp_index_path)
        
        assert explorer.rag_manager is not None
        assert explorer.llm is not None
        
        print("PASSED: Web Explorer initialized successfully")
    
    def test_invalid_url(self, temp_index_path):
        """Test handling of invalid URL"""
        explorer = WebExplorer(index_path=temp_index_path)
        
        result = explorer.get_website_summary(
            brewery_name="Test Brewery",
            url="not-a-valid-url",
            brewery_type="micro"
        )
        
        assert "error" in result
        assert result["error"] == "INVALID_URL"
        assert result["source"] == "error"
        
        print("PASSED: Invalid URL handled correctly")
    
    def test_missing_url(self, temp_index_path):
        """Test handling of missing URL"""
        explorer = WebExplorer(index_path=temp_index_path)
        
        result = explorer.get_website_summary(
            brewery_name="Test Brewery",
            url="",
            brewery_type="micro"
        )
        
        assert "error" in result
        assert result["source"] == "error"
        
        print("PASSED: Missing URL handled correctly")
    
    @pytest.mark.skip(reason="Requires real Gemini Grounding API - run manually")
    def test_real_grounding_search(self, temp_index_path):
        """Test real Gemini Grounding search (manual test)"""
        explorer = WebExplorer(index_path=temp_index_path)
        
        # Test with a real brewery using Grounding
        result = explorer.get_website_summary(
            brewery_name="Stone Brewing",
            url="https://www.stonebrewing.com",
            brewery_type="regional",
            address="Escondido, California"
        )
        
        assert "error" not in result
        assert result["source"] == "web_search"
        assert result["cache_status"] == "CACHE_MISS"
        assert len(result["summary"]) > 0
        assert result["execution_time_ms"] > 0
        
        print(f"PASSED: Real Grounding search successful")
        print(f"Summary: {result['summary']}")
        
        # Test cache hit on second call
        result2 = explorer.get_website_summary(
            brewery_name="Stone Brewing",
            url="https://www.stonebrewing.com",
            brewery_type="regional",
            address="Escondido, California"
        )
        
        assert result2["source"] == "cache_hit"
        assert result2["cache_status"] == "CACHE_HIT"
        
        print("PASSED: Cache hit on second call")
    
    def test_cache_workflow(self, temp_index_path):
        """Test complete cache workflow"""
        # Create explorer and pre-populate cache
        explorer = WebExplorer(index_path=temp_index_path)
        
        # Manually add to cache
        explorer.rag_manager.add_to_cache(
            brewery_name="Cached Brewery",
            url="https://cached.com",
            summary="This brewery is already in cache.",
            brewery_type="micro"
        )
        
        # Get summary (should hit cache)
        result = explorer.get_website_summary(
            brewery_name="Cached Brewery",
            url="https://cached.com",
            brewery_type="micro"
        )
        
        assert result["source"] == "cache_hit"
        assert result["cache_status"] == "CACHE_HIT"
        assert "This brewery is already in cache" in result["summary"]
        
        print("PASSED: Cache workflow working correctly")
    
    def test_convenience_function(self, temp_index_path):
        """Test convenience function"""
        # Pre-populate cache via direct RAG Manager
        rag = RAGManager(index_path=temp_index_path)
        rag.add_to_cache(
            brewery_name="Convenience Test",
            url="https://convenience.com",
            summary="Testing convenience function.",
            brewery_type="brewpub"
        )
        
        # Use convenience function (it creates its own WebExplorer instance)
        # Note: This will use default index path, not our temp path
        # So we test the function exists and handles invalid URLs
        result = get_website_summary(
            brewery_name="Test",
            url="invalid-url",
            brewery_type="micro",
            address="Test City"
        )
        
        assert "error" in result
        
        print("PASSED: Convenience function works")
    
    def test_get_cache_stats(self, temp_index_path):
        """Test cache statistics retrieval"""
        explorer = WebExplorer(index_path=temp_index_path)
        
        # Add some entries
        explorer.rag_manager.add_to_cache(
            brewery_name="Stats Test 1",
            url="https://stats1.com",
            summary="First stats test.",
            brewery_type="micro"
        )
        
        stats = explorer.get_cache_stats()
        
        assert "total_entries" in stats
        assert "valid_entries" in stats
        assert stats["ttl_days"] == 30
        
        print(f"PASSED: Cache stats retrieved: {stats}")


if __name__ == "__main__":
    print("\nRunning Web Explorer Tests...\n")
    
    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY not found in environment")
        exit(1)
    
    print("Testing RAG Manager...")
    pytest.main([__file__, "-v", "-k", "TestRAGManager"])
    
    print("\nTesting Web Explorer...")
    pytest.main([__file__, "-v", "-k", "TestWebExplorer", "-m", "not skip"])
    
    print("\n All tests completed!")
