# Evaluation Without RAGAS

**Stand:** 2026-02-17  
**Zweck:** Experiments (FF1, FF3, J1–J6) und Metriken ohne die RAGAS.io-Bibliothek durchfuehren.

---

## Kurzfassung

- **Retrieval-Metriken** (MRR, NDCG@10, Precision@5, Recall@10, MAP, Hit Rate) sind in `evaluation/metrics/` implementiert und benoetigen **kein RAGAS**. Sie brauchen nur: pro Query eine Rangliste (retrieved doc IDs) und eine Menge relevanter Doc-IDs (Ground Truth).
- **Ground Truth** kann manuell oder aus eurem verifizierten Testset kommen. Die Pipeline akzeptiert `ground_truth/leowiki_qa_50_verified.json` (mit `source_file` pro Q&A); `sources` werden daraus abgeleitet.
- **RAGAS** wurde nur genutzt fuer: (1) synthetische Fragen-Generierung (ist fehlgeschlagen / nicht nutzbar) und (2) optionale LLM-as-Judge-Metriken. Beides ist verzichtbar; die Forschungsfragen lassen sich mit Retrieval-Metriken + manuell verifiziertem Testset nachweisen.

---

## 1. Was ohne RAGAS funktioniert

| Komponente                                                | Abhaengigkeit                                                                      | Status                                                |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **Experiments** (`evaluation/experiments/*.yaml`)         | Config + Ground-Truth-Datei                                                        | Nutzbar                                               |
| **Metriken** (`evaluation/metrics/`)                      | Ranked Results + Relevanz-Set                                                      | Nutzbar (MRR, NDCG@10, P@5, Recall@10, MAP, Hit Rate) |
| **Eval-Pipeline** (`evaluation/scripts/eval_pipeline.py`) | Qdrant + Ground Truth; RAGAS optional                                              | Nutzbar mit `--skip ragas`                            |
| **Ground Truth**                                          | JSON mit `qa_pairs` (question, source_file oder sources, ggf. ground_truth/answer) | Nutzbar: `leowiki_qa_50_verified.json`                |

---

## 2. Ground-Truth-Format

Die Pipeline erwartet eine JSON-Datei mit:

- **metadata** (optional): created_at, version, description, etc.
- **qa_pairs**: Liste von Objekten mit:
  - **question** (string): Suchanfrage
  - **source_file** (string) **oder** **sources** (list of strings):
    - `source_file`: z.B. `exams_matura-tagesschule-if-it.txt` → wird intern zu Page-ID konvertiert (z.B. `exams:matura-tagesschule-if-it`)
    - `sources`: Liste von Page-IDs, die als relevant gelten (z.B. fuer mehrere relevante Seiten pro Frage)
  - **ground_truth** oder **answer** (optional): fuer RAGAS-Schritt oder Berichte
  - **difficulty** (optional): z.B. easy, medium, hard

Beispiel (aus `leowiki_qa_50_verified.json`):

```json
{
  "metadata": { "version": "2.0", ... },
  "qa_pairs": [
    {
      "id": "matura-01",
      "question": "Aus welchen Saeulen bestehen die Reife- und Diplompruefungen?",
      "ground_truth": "Die Reife- und Diplompruefungen bestehen aus 3 Saeulen: ...",
      "source_file": "exams_matura-tagesschule-if-it.txt",
      "difficulty": "easy"
    }
  ]
}
```

Die Pipeline leitet aus `source_file` die erwartete Page-ID ab (`source_file_to_page_id`), wenn `sources` fehlt. Damit ist euer verifiziertes 50-Q&A-Set direkt nutzbar.

---

## 3. Experimente und Metriken ausfuehren

### Pipeline (alle Schritte ausser RAGAS)

```powershell
python -m evaluation.scripts.eval_pipeline --config evaluation/experiments/full_eval.yaml --skip ragas
```

In `full_eval.yaml` ist standardmaessig bereits eingetragen:

- **ground_truth.file:** `ground_truth/leowiki_qa_50_verified.json`
- **metrics:** mrr, precision_at_5, ndcg_at_10, recall_at_k, mean_average_precision, hit_rate

RAGAS (LLM-as-Judge) wird mit `--skip ragas` uebersprungen. Retrieval-Schritt, Custom-Metriken, Statistik, Visualisierung und Report laufen ohne RAGAS.

### Einzelne Experiment-Typen

- **Modellvergleich (FF3, J2):** z.B. `model_octen_4b.yaml`, `model_pixie_rune.yaml`, … – gleicher Testkorpus, verschiedene Embedding-Modelle.
- **Chunk-Groesse (J4):** `chunk_256.yaml`, `chunk_512.yaml`, `chunk_1024.yaml`.
- **Hybrid vs. Dense (J6):** `hybrid_vs_dense.yaml`.
- **Keyword-Baseline (FF1):** `keyword_baseline.yaml` – DokuWiki-Stichwortsuche vs. semantische Suche.

Die genannten YAMLs referenzieren dieselbe Ground-Truth-Datei; die Metriken in `evaluation/metrics/` werden ohne RAGAS berechnet.

---

## 4. Ground-Truth erstellen ohne RAGAS

Falls ihr zusaetzliche oder andere Testfragen braucht, ohne RAGAS TestsetGenerator:

1. **Manuell (empfohlen in _froschungsfragen_de.md)**  
   Gemeinsam Fragen formulieren und pro Frage die relevanten Wiki-Seiten (Page-IDs) festlegen. JSON mit `qa_pairs` wie oben anlegen; pro Eintrag `question` und `sources` (Liste von Page-IDs) oder `source_file` (eine Datei → eine Page-ID).

2. **Aus test_corpus (empfohlen fuer Modellvergleich)**  
   Ein Q&A pro Dokument aus `evaluation/test_corpus`, mit `page_id` aus YAML-Frontmatter und Template-Frage aus Titel/Dateiname. Direkt nutzbar fuer alle Metriken und Experimente (FF3, J2, J4, J6).  
   `python -m evaluation.scripts.generate_ground_truth_from_test_corpus`  
   Schreibt `evaluation/ground_truth/test_corpus_qa.json`. In den Experiment-YAMLs `ground_truth.file` auf `ground_truth/test_corpus_qa.json` setzen. Optional: `--max-questions 50` um auf 50 Fragen zu begrenzen.

3. **Einfacher LLM-Generator (ohne RAGAS)**  
   Eigenes kleines Skript: z.B. pro Korpus-Dokument einen Aufruf an OpenAI/ollama: "Erzeuge eine kurze deutschsprachige Frage, die dieses Dokument beantwortet." Fragen sammeln, manuell pruefen und mit `source_file` oder `sources` in die Ground-Truth-JSON eintragen. Kein RAGAS noetig.

---

## 5. Bezug zu Forschungsfragen

- **J1 (Testkorpus):** "Ca. 30 Testfragen (RAGAS-generiert + manuell verifiziert)" – ihr duerft pragmatisch bleiben: "Jan und Imre beurteilen gemeinsam, welche Wiki-Seiten fuer eine Testfrage relevant sind." Das ist ohne RAGAS erfuellbar (manuell oder mit obigen Alternativen).
- **FF1, FF3, J2, J4, J6:** Nachweis ueber Retrieval-Metriken (MRR, NDCG@10, P@5, Recall@10, MAP, Hit Rate) auf einem definierten Testset – alles ohne RAGAS-Bibliothek.
- **RAGAS-Metriken** (answer_correctness, faithfulness, context_precision): Optional; wenn ihr sie weglasst, reicht die Dokumentation im Thesis-Text, dass ihr Retrieval-Metriken und manuell verifiziertes Ground Truth verwendet habt.

---

## 6. Dateien und Stellen im Code

- **Ground Truth (bereits nutzbar):** `evaluation/ground_truth/leowiki_qa_50_verified.json`
- **Ground Truth aus test_corpus:** `evaluation/scripts/generate_ground_truth_from_test_corpus.py` erzeugt `ground_truth/test_corpus_qa.json` aus `evaluation/test_corpus` (ein Q&A pro Dokument, page_id aus Frontmatter). Ideal fuer Modellvergleich auf dem gleichen Korpus wie die Indexierung.
- **Pipeline (source_file-Support):** `evaluation/scripts/eval_pipeline.py` – nutzt `_expected_sources_for_qa()` (sources aus `sources` oder aus `source_file`).
- **Metriken:** `evaluation/metrics/` (mrr, ndcg, precision_at_k, recall_at_k, mean_average_precision, hit_rate).
- **Experiment-Configs:** `evaluation/experiments/*.yaml` – `ground_truth.file` auf eure JSON setzen (z.B. `ground_truth/test_corpus_qa.json` fuer test_corpus-basierte Evaluation).

Die Pipeline unterstuetzt optional LLM-as-Judge-Metriken (RAGAS-style) ueber `evaluation.metrics.llm_judge`; mit `--skip ragas` werden nur Retrieval-Metriken berechnet. Ground Truth: z.B. `leowiki_qa_78_Opus_46.json`, `test_corpus_qa.json` oder `leowiki_qa_50_verified.json`.
