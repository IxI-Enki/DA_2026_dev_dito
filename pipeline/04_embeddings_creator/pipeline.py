"""
Embedding Pipeline
==================
Orchestrates the complete embedding process.
"""

import json
import time
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from tqdm import tqdm

from config import get_config
from document_loader import DocumentLoader, Document
from content_aware_chunker import ContentAwareChunker, Chunk
from embedder import Embedder

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """Main pipeline: Orchestrates the entire embedding process."""
    
    def __init__(self):
        self.config = get_config()
        self._setup_logging()
        self._setup_directories()
        
        # Initialize components
        self.loader = DocumentLoader()
        self.chunker = ContentAwareChunker()
        self.embedder = Embedder()
        
        # Statistics
        self.statistics = {
            'documents': {'pages': 0, 'media': 0, 'total': 0},
            'chunks': {'pages': 0, 'media': 0, 'total': 0},
            'skipped': 0,
            'failed': 0,
        }
    
    def _setup_logging(self):
        """Configure logging."""
        log_config = self.config.logging
        log_level = log_config.get('level', 'INFO')
        log_format = log_config.get('format', '%(asctime)s [%(levelname)s] %(message)s')
        log_file = log_config.get('file')
        
        handlers = []
        
        if log_config.get('console', True):
            handlers.append(logging.StreamHandler(sys.stdout))
        
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=handlers,
        )
        
        # Set specific logger levels
        for logger_name, level in log_config.get('levels', {}).items():
            logging.getLogger(logger_name).setLevel(getattr(logging, level))
    
    def _setup_directories(self):
        """Create required directories."""
        Path(self.config.paths.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.paths.log_dir).mkdir(parents=True, exist_ok=True)
    
    def _build_metadata(self, chunk: Chunk) -> Dict[str, Any]:
        """Build metadata dictionary for a chunk."""
        include = self.config.output.include_metadata
        metadata = {}
        
        if include.get('source', True):
            metadata['source'] = chunk.source
        if include.get('collection', True):
            metadata['collection'] = chunk.collection
        if include.get('title', True):
            metadata['title'] = chunk.title
        if include.get('namespace', True):
            metadata['namespace'] = chunk.namespace
        if include.get('page_id', True) and chunk.page_id:
            metadata['page_id'] = chunk.page_id
        if include.get('media_id', True) and chunk.media_id:
            metadata['media_id'] = chunk.media_id
        if include.get('access_level', True):
            metadata['access_level'] = chunk.access_level
        if include.get('content_type', True):
            metadata['content_type'] = chunk.content_type
        
        # Frontmatter fields
        fm = chunk.document.frontmatter
        if include.get('freshness_score', True) and 'freshness_score' in fm:
            metadata['freshness_score'] = fm['freshness_score']
        if include.get('freshness_category', True) and 'freshness_category' in fm:
            metadata['freshness_category'] = fm['freshness_category']
        
        # Chunk info
        if include.get('chunk_index', True):
            metadata['chunk_index'] = chunk.chunk_index
        if include.get('total_chunks', True):
            metadata['total_chunks'] = chunk.total_chunks
        if include.get('original_length', True):
            metadata['original_length'] = len(chunk.document.content)
        
        # Embedding info
        if include.get('embedding_model', True):
            metadata['embedding_model'] = self.embedder.model
        if include.get('embedding_dimensions', True):
            metadata['embedding_dimensions'] = self.embedder.dimensions
        if include.get('created_at', True):
            metadata['created_at'] = datetime.now().isoformat()
        
        # Relationship data
        if include.get('links_to', True) and 'links_to' in fm:
            metadata['links_to'] = fm['links_to']
        if include.get('linked_from', True) and 'linked_from' in fm:
            metadata['linked_from'] = fm['linked_from']
        if include.get('media_refs', True) and 'media_refs' in fm:
            metadata['media_refs'] = fm['media_refs']
        if include.get('referenced_by', True) and 'referenced_by' in fm:
            metadata['referenced_by'] = fm['referenced_by']
        
        return metadata
    
    def _write_jsonl(self, output_path: Path, records: List[Dict[str, Any]]):
        """Write records to JSONL file."""
        encoding = self.config.output.encoding
        
        with open(output_path, 'w', encoding=encoding) as f:
            for record in records:
                json.dump(record, f, ensure_ascii=False)
                f.write('\n')
    
    def run(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the complete embedding pipeline.
        
        Args:
            limit: Maximum documents to process (None = all)
            
        Returns:
            Pipeline statistics
        """
        logger.info("=" * 60)
        logger.info("QDRANT EMBEDDING PIPELINE")
        logger.info("=" * 60)
        logger.info(f"Model: {self.embedder.model}")
        logger.info(f"Dimensions: {self.embedder.dimensions}")
        
        start_time = time.time()
        
        try:
            # 1. Load documents
            logger.info("\n" + "=" * 60)
            logger.info("Loading documents...")
            logger.info("=" * 60)
            
            documents = self.loader.load_all(limit=limit)
            doc_stats = self.loader.get_stats(documents)
            
            self.statistics['documents']['pages'] = doc_stats['pages']
            self.statistics['documents']['media'] = doc_stats['media']
            self.statistics['documents']['total'] = doc_stats['total']
            
            logger.info(f"Loaded {doc_stats['total']} documents ({doc_stats['pages']} pages, {doc_stats['media']} media)")
            
            # 2. Chunk documents
            logger.info("\n" + "=" * 60)
            logger.info("Chunking documents...")
            logger.info("=" * 60)
            
            chunks = self.chunker.chunk_all(documents)
            chunk_stats = self.chunker.get_stats(chunks)
            
            self.statistics['chunks'] = chunk_stats.get('by_collection', {})
            self.statistics['chunks']['total'] = chunk_stats['total']
            
            logger.info(f"Created {chunk_stats['total']} chunks")
            logger.info(f"Avg chunk size: {chunk_stats['avg_chunk_size']:.0f} chars")
            
            # 3. Create embeddings
            logger.info("\n" + "=" * 60)
            logger.info("Creating embeddings...")
            logger.info("=" * 60)
            
            # Extract texts for embedding
            texts = [chunk.text for chunk in chunks]
            
            # Progress bar
            progress_config = self.config.logging.get('progress', {})
            progress_enabled = progress_config.get('enabled', True)
            
            # Create embeddings in batches with progress
            all_embeddings = []
            batch_size = self.embedder.batch_size
            
            pbar = tqdm(
                range(0, len(texts), batch_size),
                desc="Embedding",
                disable=not progress_enabled,
                colour=progress_config.get('colour', 'green'),
            )
            
            for i in pbar:
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.embedder.create_embeddings(batch_texts)
                all_embeddings.extend(batch_embeddings)
                pbar.set_postfix({'chunks': len(all_embeddings)})
            
            # 4. Build output records
            logger.info("\n" + "=" * 60)
            logger.info("Building output records...")
            logger.info("=" * 60)
            
            schema = self.config.output.schema
            records = []
            
            for chunk, embedding in zip(chunks, all_embeddings):
                record = {
                    schema['id_field']: chunk.chunk_id,
                    schema['text_field']: chunk.text,
                    schema['embedding_field']: embedding,
                    schema['metadata_field']: self._build_metadata(chunk),
                }
                records.append(record)
            
            # 5. Write output (timestamped subdir: embedded_at_YYYYMMDD_HHMMSS)
            logger.info("\n" + "=" * 60)
            logger.info("Writing output...")
            logger.info("=" * 60)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_output_dir = Path(self.config.paths.output_dir) / f"embedded_at_{timestamp}"
            run_output_dir.mkdir(parents=True, exist_ok=True)
            output_file = run_output_dir / self.config.output.filename
            self._write_jsonl(output_file, records)
            
            logger.info(f"Wrote {len(records)} records to {output_file}")
            
            # 6. Write statistics (same timestamped dir)
            elapsed = time.time() - start_time
            emb_stats = self.embedder.get_statistics()
            
            final_stats = {
                'pipeline': {
                    'documents': self.statistics['documents'],
                    'chunks': self.statistics['chunks'],
                    'elapsed_seconds': round(elapsed, 2),
                },
                'embedding': emb_stats,
                'output': {
                    'file': str(output_file),
                    'records': len(records),
                    'format': self.config.output.format,
                },
                'timestamp': datetime.now().isoformat(),
            }
            
            stats_file = run_output_dir / "embedding_statistics.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(final_stats, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\nStatistics saved to: {stats_file}")
            
            # Print summary
            if self.config.statistics.get('print_summary', True):
                self._print_summary(final_stats)
            
            return final_stats
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def _print_summary(self, stats: Dict[str, Any]):
        """Print pipeline summary."""
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 60)
        
        pipe = stats['pipeline']
        emb = stats['embedding']
        
        logger.info(f"\nDocuments:")
        logger.info(f"  Pages: {pipe['documents'].get('pages', 0)}")
        logger.info(f"  Media: {pipe['documents'].get('media', 0)}")
        logger.info(f"  Total: {pipe['documents'].get('total', 0)}")
        
        logger.info(f"\nChunks:")
        logger.info(f"  Total: {pipe['chunks'].get('total', 0)}")
        
        logger.info(f"\nEmbedding API:")
        logger.info(f"  Model: {emb['model']}")
        logger.info(f"  Dimensions: {emb['dimensions']}")
        logger.info(f"  Total tokens: {emb['total_tokens']:,}")
        logger.info(f"  Estimated cost: ${emb['total_cost']:.4f}")
        
        logger.info(f"\nOutput:")
        logger.info(f"  File: {stats['output']['file']}")
        logger.info(f"  Records: {stats['output']['records']}")
        
        logger.info(f"\nTime: {pipe['elapsed_seconds']:.2f}s")
        logger.info("=" * 60)


# Entry point for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Qdrant Embedding Pipeline')
    parser.add_argument('--limit', '-l', type=int, help='Limit documents to process')
    args = parser.parse_args()
    
    pipeline = EmbeddingPipeline()
    pipeline.run(limit=args.limit)
