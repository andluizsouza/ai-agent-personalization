"""
RAG Manager for Web Knowledge Cache with FAISS and TTL (Time-to-Live)

This module manages a FAISS vector store for caching web content summaries
with metadata including creation dates for TTL validation (30 days).

Features:
- Google Embeddings (models/embedding-001)
- FAISS vector store for semantic search
- TTL validation (30 days)
- Persistence to disk
- Metadata management (brewery_name, url, summary, creation_date, brewery_type)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document

logger = logging.getLogger(__name__)


class RAGManager:
    """
    Manages FAISS-based RAG index with TTL for web content caching.
    
    The cache stores brewery website summaries with metadata to avoid
    repeated web searches within a 30-day window.
    """
    
    def __init__(
        self,
        index_path: str = "data/faiss_index",
        ttl_days: int = 30,
        embedding_model: str = "models/embedding-001"
    ):
        """
        Initialize RAG Manager.
        
        Args:
            index_path: Path to save/load FAISS index
            ttl_days: Time-to-live for cached entries (default: 30 days)
            embedding_model: Google embedding model name
        """
        self.index_path = Path(index_path)
        self.ttl_days = ttl_days
        self.embedding_model = embedding_model
        
        # Create directory if it doesn't exist
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=embedding_model
            )
            logger.info(f"Initialized Google Embeddings: {embedding_model}")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise
        
        # Load or create FAISS index
        self.vectorstore = self._load_or_create_index()
    
    def _load_or_create_index(self) -> FAISS:
        """
        Load existing FAISS index from disk or create a new one.
        
        Returns:
            FAISS vectorstore instance
        """
        index_file = self.index_path / "index.faiss"
        
        if index_file.exists():
            try:
                vectorstore = FAISS.load_local(
                    str(self.index_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info(f"Loaded existing FAISS index from {self.index_path}")
                return vectorstore
            except Exception as e:
                logger.warning(f"Failed to load index, creating new one: {e}")
        
        # Create empty index with a dummy document
        dummy_doc = Document(
            page_content="initialization",
            metadata={"type": "system", "creation_date": datetime.now().isoformat()}
        )
        vectorstore = FAISS.from_documents([dummy_doc], self.embeddings)
        logger.info("Created new FAISS index")
        
        return vectorstore
    
    def _is_cache_valid(self, creation_date_str: str) -> bool:
        """
        Check if cached entry is still valid based on TTL.
        
        Args:
            creation_date_str: ISO format date string
            
        Returns:
            True if cache is valid (< ttl_days old), False otherwise
        """
        try:
            creation_date = datetime.fromisoformat(creation_date_str)
            age_days = (datetime.now() - creation_date).days
            is_valid = age_days <= self.ttl_days
            
            logger.debug(
                f"Cache age: {age_days} days, TTL: {self.ttl_days} days, "
                f"Valid: {is_valid}"
            )
            
            return is_valid
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid creation_date format: {creation_date_str}, {e}")
            return False
    
    def search_cache(
        self,
        query: str,
        top_k: int = 1,
        brewery_name: Optional[str] = None
    ) -> Tuple[Optional[Dict], str]:
        """
        Search cache for existing brewery summary.
        
        Args:
            query: Search query (brewery name or URL)
            top_k: Number of results to retrieve
            brewery_name: Optional brewery name for filtering
            
        Returns:
            Tuple of (result_dict, status)
            - result_dict: None or dict with brewery info
            - status: "CACHE_HIT", "CACHE_STALE", or "CACHE_MISS"
        """
        try:
            # Perform similarity search
            docs = self.vectorstore.similarity_search(query, k=top_k)
            
            if not docs or docs[0].metadata.get("type") == "system":
                logger.info(f"Cache miss for query: {query}")
                return None, "CACHE_MISS"
            
            # Get the top result
            top_doc = docs[0]
            metadata = top_doc.metadata
            
            # Validate brewery name if provided
            if brewery_name:
                cached_name = metadata.get("brewery_name", "").lower()
                if brewery_name.lower() not in cached_name:
                    logger.info(f"Brewery name mismatch: {brewery_name} vs {cached_name}")
                    return None, "CACHE_MISS"
            
            # Check TTL
            creation_date = metadata.get("creation_date")
            if not creation_date:
                logger.warning("No creation_date in metadata, treating as stale")
                return None, "CACHE_STALE"
            
            if not self._is_cache_valid(creation_date):
                logger.info(f"Cache stale for: {metadata.get('brewery_name')}")
                result = {
                    "brewery_name": metadata.get("brewery_name"),
                    "url": metadata.get("url"),
                    "summary": top_doc.page_content,
                    "brewery_type": metadata.get("brewery_type"),
                    "creation_date": creation_date
                }
                return result, "CACHE_STALE"
            
            # Cache hit - return valid data
            logger.info(f"Cache hit for: {metadata.get('brewery_name')}")
            result = {
                "brewery_name": metadata.get("brewery_name"),
                "url": metadata.get("url"),
                "summary": top_doc.page_content,
                "brewery_type": metadata.get("brewery_type"),
                "creation_date": creation_date
            }
            return result, "CACHE_HIT"
            
        except Exception as e:
            logger.error(f"Cache search failed: {e}")
            return None, "CACHE_MISS"
    
    def add_to_cache(
        self,
        brewery_name: str,
        url: str,
        summary: str,
        brewery_type: str = "unknown"
    ) -> bool:
        """
        Add new entry to cache.
        
        Args:
            brewery_name: Name of the brewery
            url: Website URL
            summary: Content summary (3 sentences max)
            brewery_type: Type of brewery (micro, brewpub, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create document with metadata
            doc = Document(
                page_content=summary,
                metadata={
                    "brewery_name": brewery_name,
                    "url": url,
                    "brewery_type": brewery_type,
                    "creation_date": datetime.now().isoformat(),
                    "type": "brewery_summary"
                }
            )
            
            # Add to vectorstore
            self.vectorstore.add_documents([doc])
            logger.info(f"Added to cache: {brewery_name} ({url})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add to cache: {e}")
            return False
    
    def update_cache_entry(
        self,
        brewery_name: str,
        url: str,
        summary: str,
        brewery_type: str = "unknown"
    ) -> bool:
        """
        Update existing cache entry with new summary.
        
        Note: FAISS doesn't support in-place updates, so we add a new entry
        with updated timestamp. Old entry will naturally become less relevant
        due to lower similarity scores.
        
        Args:
            brewery_name: Name of the brewery
            url: Website URL
            summary: Updated content summary
            brewery_type: Type of brewery
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Updating cache entry for: {brewery_name}")
        return self.add_to_cache(brewery_name, url, summary, brewery_type)
    
    def save_index(self) -> bool:
        """
        Persist FAISS index to disk.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.vectorstore.save_local(str(self.index_path))
            logger.info(f"Saved FAISS index to {self.index_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """
        Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            # Get all documents (FAISS doesn't have a direct method for this)
            # So we'll use a broad search to estimate
            all_docs = self.vectorstore.similarity_search("brewery", k=100)
            
            total_entries = len([d for d in all_docs if d.metadata.get("type") == "brewery_summary"])
            
            valid_entries = 0
            stale_entries = 0
            
            for doc in all_docs:
                if doc.metadata.get("type") == "brewery_summary":
                    creation_date = doc.metadata.get("creation_date")
                    if creation_date and self._is_cache_valid(creation_date):
                        valid_entries += 1
                    else:
                        stale_entries += 1
            
            return {
                "total_entries": total_entries,
                "valid_entries": valid_entries,
                "stale_entries": stale_entries,
                "ttl_days": self.ttl_days,
                "index_path": str(self.index_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "total_entries": 0,
                "valid_entries": 0,
                "stale_entries": 0,
                "ttl_days": self.ttl_days,
                "index_path": str(self.index_path)
            }
