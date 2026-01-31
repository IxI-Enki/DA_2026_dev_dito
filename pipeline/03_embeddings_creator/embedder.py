"""
Embedder
========
Creates embeddings using OpenAI API.
"""

import time
import logging
from typing import List, Dict, Any

from openai import OpenAI

from config import get_config

logger = logging.getLogger(__name__)


class Embedder:
    """Creates embeddings via OpenAI API."""
    
    def __init__(self):
        self.config = get_config()
        self.client = self._init_client()
        
        # Model settings
        self.model = self.config.openai.embedding_model
        self.dimensions = self.config.openai.embedding_dimensions
        self.encoding_format = self.config.openai.encoding_format
        self.batch_size = self.config.openai.batch_size
        self.delay = self.config.openai.delay_between_batches
        
        # Statistics
        self.stats = {
            'total_tokens': 0,
            'total_requests': 0,
            'total_cost': 0.0,
            'total_embeddings': 0,
        }
        
        # Cost per 1k tokens
        cost_config = self.config.statistics.get('cost', {})
        self.cost_per_1k = cost_config.get(self.model, 0.00013)
    
    def _init_client(self) -> OpenAI:
        """Initialize OpenAI client."""
        api_key = self.config.get_api_key()
        
        return OpenAI(
            api_key=api_key,
            base_url=self.config.openai.base_url,
            timeout=self.config.openai.timeout,
            max_retries=self.config.openai.max_retries,
        )
    
    def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embeddings = self.create_embeddings([text])
        return embeddings[0] if embeddings else []
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimensions,
                encoding_format=self.encoding_format,
            )
            
            # Update statistics
            tokens_used = response.usage.total_tokens
            self.stats['total_tokens'] += tokens_used
            self.stats['total_requests'] += 1
            self.stats['total_embeddings'] += len(texts)
            self.stats['total_cost'] += (tokens_used / 1000) * self.cost_per_1k
            
            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            
            # Rate limiting delay
            if self.delay > 0:
                time.sleep(self.delay)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding creation failed: {e}")
            raise
    
    def create_embeddings_batched(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings in batches.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            embeddings = self.create_embeddings(batch)
            all_embeddings.extend(embeddings)
            
            if i > 0 and i % (self.batch_size * 10) == 0:
                logger.info(f"Embedded {i}/{len(texts)} texts...")
        
        return all_embeddings
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get embedding statistics."""
        return {
            **self.stats,
            'model': self.model,
            'dimensions': self.dimensions,
            'batch_size': self.batch_size,
        }


# Test embedding
if __name__ == "__main__":
    import os
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    
    # Check if API key is set
    if not os.environ.get('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Set it with: $env:OPENAI_API_KEY = 'your-key'")
        exit(1)
    
    embedder = Embedder()
    
    test_texts = [
        "Dies ist ein Test für das Embedding-System.",
        "Die HTL Leonding ist eine technische Schule in Oberösterreich.",
    ]
    
    print(f"Model: {embedder.model}")
    print(f"Dimensions: {embedder.dimensions}")
    print(f"\nCreating embeddings for {len(test_texts)} texts...")
    
    embeddings = embedder.create_embeddings(test_texts)
    
    print(f"\nResults:")
    for i, emb in enumerate(embeddings):
        print(f"  Text {i+1}: {len(emb)} dimensions, first 5: {emb[:5]}")
    
    stats = embedder.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Total cost: ${stats['total_cost']:.6f}")
