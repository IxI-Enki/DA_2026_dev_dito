"""
Query Generator - LLM-basierte Test-Query-Generierung

Generiert:
- Synthetische Faktenfragen
- How-to / Prozess-Fragen
- RAGAS-kompatible Test-Sets
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import sys

# Relative import für config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_config, EvaluationConfig

# Optional OpenAI-compatible client
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


@dataclass
class GeneratedQuery:
    """Eine generierte Test-Query."""
    question: str
    source_page: str
    source_chunk: str
    query_type: str  # factual, procedural
    namespace: str
    context: Optional[str] = None
    expected_answer: Optional[str] = None


@dataclass
class QueryGenerationResult:
    """Gesamtergebnis der Query-Generierung."""
    total_queries: int = 0
    queries_by_type: Dict[str, int] = field(default_factory=dict)
    queries_by_namespace: Dict[str, int] = field(default_factory=dict)
    queries: List[GeneratedQuery] = field(default_factory=list)
    failed_generations: int = 0
    pages_sampled: int = 0


class QueryGenerator:
    """Generiert synthetische Test-Queries mit LLM."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        """
        Initialisiert den QueryGenerator.

        Args:
            config: EvaluationConfig Instanz
        """
        self.config = config or get_config()
        self.raw_config = self.config.raw_config

        # Query generation settings
        self.query_cfg = self.config.query_generation
        self.enabled = self.query_cfg.enabled

        # LLM settings
        self.llm_cfg = self.query_cfg.llm

        # Sampling settings
        self.pages_per_namespace = self.query_cfg.pages_per_namespace
        self.chunks_per_page = self.query_cfg.chunks_per_page
        self.min_chunk_length = self.query_cfg.min_chunk_length

        # Query type templates from config
        query_types_cfg = self.raw_config.get('QUERY_GENERATION', {}).get('query_types', {})
        self.factual_template = query_types_cfg.get('factual', {}).get('prompt_template', self._default_factual_template())
        self.procedural_template = query_types_cfg.get('procedural', {}).get('prompt_template', self._default_procedural_template())

        # Initialize LLM client
        self.client = None
        if HAS_OPENAI and self.enabled:
            try:
                self.client = OpenAI(
                    base_url=self.llm_cfg.base_url,
                    api_key=self.llm_cfg.api_key
                )
            except Exception as e:
                print(f"  WARNUNG: LLM-Client konnte nicht initialisiert werden: {e}")

        # Results
        self.result = QueryGenerationResult()

    def _default_factual_template(self) -> str:
        return """Basierend auf folgendem Text, erstelle eine präzise Faktenfrage:

TEXT:
{chunk}

Erstelle eine Frage, die mit den Informationen im Text beantwortet werden kann.
Die Frage soll auf Deutsch sein.
Antworte NUR mit der Frage, ohne weitere Erklärung."""

    def _default_procedural_template(self) -> str:
        return """Basierend auf folgendem Text, erstelle eine Wie-macht-man-Frage:

TEXT:
{chunk}

Erstelle eine Frage im Stil "Wie...", "Was muss ich tun um...", etc.
Die Frage soll auf Deutsch sein.
Antworte NUR mit der Frage, ohne weitere Erklärung."""

    def generate(self, sample_size: Optional[int] = None) -> QueryGenerationResult:
        """
        Generiert Test-Queries aus den Wiki-Inhalten.

        Args:
            sample_size: Optionale Begrenzung der generierten Queries

        Returns:
            QueryGenerationResult mit allen Queries
        """
        print("\n[QueryGenerator] Starte Generierung...")

        if not self.enabled:
            print("  Query-Generierung ist deaktiviert")
            return self.result

        if not self.client:
            print("  WARNUNG: Kein LLM-Client verfügbar - Generierung übersprungen")
            return self.result

        # Load pages grouped by namespace
        pages_by_ns = self._load_pages_by_namespace()
        print(f"  Gefunden: {len(pages_by_ns)} Namespaces")

        # Sample pages from each namespace
        for namespace, pages in pages_by_ns.items():
            sampled = self._sample_pages(pages, self.pages_per_namespace)
            self.result.pages_sampled += len(sampled)

            for page_data in sampled:
                self._generate_queries_for_page(page_data, namespace)

                # Check sample size limit
                if sample_size and self.result.total_queries >= sample_size:
                    print(f"  Sample-Limit erreicht: {sample_size}")
                    break

            if sample_size and self.result.total_queries >= sample_size:
                break

        print(f"  Generiert: {self.result.total_queries} Queries")
        print(f"  Fehlgeschlagen: {self.result.failed_generations}")

        return self.result

    def _load_pages_by_namespace(self) -> Dict[str, List[Dict]]:
        """Lädt alle Seiten gruppiert nach Namespace."""
        pages_by_ns = {}
        content_dir = self.config.page_content_dir

        if not content_dir or not content_dir.exists():
            return pages_by_ns

        for content_file in content_dir.glob("*.txt"):
            page_id = content_file.stem

            # Extract namespace
            namespace = page_id.split(':')[0] if ':' in page_id else 'root'

            # Skip archived content
            if namespace == 'archive':
                continue

            try:
                content = content_file.read_text(encoding='utf-8')

                # Skip short content
                if len(content) < self.min_chunk_length * 2:
                    continue

                if namespace not in pages_by_ns:
                    pages_by_ns[namespace] = []

                pages_by_ns[namespace].append({
                    'page_id': page_id,
                    'content': content
                })

            except Exception:
                continue

        return pages_by_ns

    def _sample_pages(self, pages: List[Dict], n: int) -> List[Dict]:
        """Wählt zufällig n Seiten aus."""
        if len(pages) <= n:
            return pages
        return random.sample(pages, n)

    def _generate_queries_for_page(self, page_data: Dict, namespace: str):
        """
        Generiert Queries für eine Seite.
        
        Gemäß Microsoft RAG Guide:
        - Query: Die Frage
        - Context: Collection der tatsächlichen Textstellen (hier: der Chunk)
        - Answer: Gültige Antwort (optional, kann später generiert werden)
        """
        page_id = page_data['page_id']
        content = page_data['content']

        # Split into chunks (one-off chunking für Query-Generierung, nicht für finale Lösung)
        chunks = self._chunk_content(content)

        # Sample chunks
        sampled_chunks = chunks[:self.chunks_per_page]

        for chunk in sampled_chunks:
            # Generate factual query
            factual_q = self._generate_query(chunk, 'factual')
            if factual_q:
                # Context: Der tatsächliche Text der die Query beantwortet (Microsoft Guide)
                query = GeneratedQuery(
                    question=factual_q,
                    source_page=page_id,
                    source_chunk=chunk[:500],
                    query_type='factual',
                    namespace=namespace,
                    context=chunk,  # Context gemäß Microsoft Guide
                    expected_answer=None  # Kann später mit LLM generiert werden
                )
                self._add_query(query)

            # Generate procedural query for suitable pages
            if self._is_procedural_candidate(page_id, chunk):
                proc_q = self._generate_query(chunk, 'procedural')
                if proc_q:
                    query = GeneratedQuery(
                        question=proc_q,
                        source_page=page_id,
                        source_chunk=chunk[:500],
                        query_type='procedural',
                        namespace=namespace,
                        context=chunk,  # Context gemäß Microsoft Guide
                        expected_answer=None  # Kann später mit LLM generiert werden
                    )
                    self._add_query(query)

    def _chunk_content(self, content: str) -> List[str]:
        """Teilt Inhalt in Chunks auf."""
        # Simple paragraph-based chunking
        paragraphs = content.split('\n\n')

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) > 1000:
                if len(current_chunk) >= self.min_chunk_length:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if len(current_chunk) >= self.min_chunk_length:
            chunks.append(current_chunk.strip())

        return chunks

    def _is_procedural_candidate(self, page_id: str, chunk: str) -> bool:
        """Prüft ob ein Chunk für Prozess-Fragen geeignet ist."""
        indicators = ['schritt', 'anleitung', 'wie', 'ablauf', 'prozess',
                     'vorgehen', 'formular', 'antrag', 'muss', 'sollte']

        page_lower = page_id.lower()
        chunk_lower = chunk.lower()

        for indicator in indicators:
            if indicator in page_lower or indicator in chunk_lower:
                return True
        return False

    def _generate_query(self, chunk: str, query_type: str) -> Optional[str]:
        """Generiert eine Query mit LLM."""
        if not self.client:
            return None

        template = self.factual_template if query_type == 'factual' else self.procedural_template
        prompt = template.replace('{chunk}', chunk[:800])

        try:
            response = self.client.chat.completions.create(
                model=self.llm_cfg.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.llm_cfg.temperature,
                max_tokens=self.llm_cfg.max_tokens,
                top_p=self.llm_cfg.top_p
            )

            content = response.choices[0].message.content
            if content is None:
                self.result.failed_generations += 1
                return None

            question = content.strip()

            # Basic validation
            if len(question) < 10 or len(question) > 500:
                self.result.failed_generations += 1
                return None

            if not question.endswith('?'):
                question += '?'

            return question

        except Exception as e:
            self.result.failed_generations += 1
            return None

    def _add_query(self, query: GeneratedQuery):
        """Fügt eine Query zu den Ergebnissen hinzu."""
        self.result.queries.append(query)
        self.result.total_queries += 1

        # Update stats
        self.result.queries_by_type[query.query_type] = \
            self.result.queries_by_type.get(query.query_type, 0) + 1

        self.result.queries_by_namespace[query.namespace] = \
            self.result.queries_by_namespace.get(query.namespace, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Ergebnisse zu Dictionary für JSON-Export."""
        return {
            'summary': {
                'total_queries': self.result.total_queries,
                'pages_sampled': self.result.pages_sampled,
                'failed_generations': self.result.failed_generations
            },
            'by_type': self.result.queries_by_type,
            'by_namespace': self.result.queries_by_namespace,
            'queries': [
                {
                    'question': q.question,
                    'source_page': q.source_page,
                    'query_type': q.query_type,
                    'namespace': q.namespace,
                    'context': q.context[:500] if q.context else None
                }
                for q in self.result.queries
            ]
        }

    def to_ragas_format(self) -> List[Dict[str, Any]]:
        """
        Exportiert Queries im RAGAS-kompatiblen Format.
        
        Format entspricht Microsoft RAG Guide:
        - Query: Die Frage
        - Context: Collection der tatsächlichen Textstellen (hier: contexts array)
        - Answer: Gültige Antwort (hier: ground_truth, optional)

        Returns:
            Liste von Dicts mit question, contexts, ground_truth
        """
        ragas_data = []

        for query in self.result.queries:
            # Microsoft Guide Format: Query + Context + Answer
            ragas_data.append({
                'question': query.question,  # Query
                'contexts': [query.context] if query.context else [],  # Context (Collection)
                'ground_truth': query.expected_answer or "",  # Answer (optional)
                'metadata': {
                    'source_page': query.source_page,
                    'query_type': query.query_type,
                    'namespace': query.namespace,
                    'source_chunk': query.source_chunk[:200] if query.source_chunk else None
                }
            })

        return ragas_data


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    generator = QueryGenerator()

    if not generator.enabled:
        print("Query-Generierung ist deaktiviert in der Konfiguration")
    elif not generator.client:
        print("LLM-Client nicht verfügbar - bitte LM-Studio starten")
    else:
        result = generator.generate(sample_size=10)

        print("\n" + "=" * 60)
        print("  QUERY GENERATION RESULTS")
        print("=" * 60)
        print(f"\n  Total Queries: {result.total_queries}")
        print(f"  Pages Sampled: {result.pages_sampled}")
        print(f"  Failed: {result.failed_generations}")

        print(f"\n  By Type:")
        for qt, count in result.queries_by_type.items():
            print(f"    {qt}: {count}")

        print(f"\n  Sample Queries:")
        for q in result.queries[:5]:
            print(f"    - [{q.query_type}] {q.question[:80]}...")
