---
description: Erweitert Testset bei Bedarf. Paraphrasierung, Negative Sampling, Edge Cases. RAGAS EvolveComplexity, EvolveSimple.
globs: ["**/ground_truth_dataset.json"]
alwaysApply: false
---

# Synthetic Data Augmentation

**Zweck:** Erweitert das Ground-Truth Testset, falls 20-30 Fragen nicht ausreichen oder mehr Variation gewuenscht wird.

## Techniken

- **Paraphrasierung** – Existierende Fragen umformulieren (andere Formulierung, gleiche Intention)
- **Negative Sampling** – Schwer zu beantwortende Fragen oder solche, die gezielt nicht im Corpus beantwortbar sind (fuer Robustheit)
- **Edge Cases** – Randfaelle, Ambiguitaet, mehrdeutige Formulierungen

## RAGAS Integration

- **EvolveComplexity** – Transformation: einfache Fragen zu komplexeren
- **EvolveSimple** – Transformation: komplexe zu einfacheren
- Optional: Eigene Transformationen (Sprache, Formulierung)

## Skript

```bash
python evaluation/ragas_agents/scripts/augment_test_data.py --dataset <ground_truth_dataset.json> [--num-extra 10] [--strategies paraphrase,negative_sampling] [--output ground_truth_dataset_augmented.json]
```

## Eingaben

- `ground_truth_dataset.json`
- Optional: num_extra (Anzahl zusaetzlicher Beispiele), strategies (paraphrase, negative_sampling, edge_cases)
- Config: LLM fuer Paraphrasierung, Seed fuer Reproduzierbarkeit

## Ausgaben

- **ground_truth_dataset_augmented.json** – Original + augmentierte Eintraege; IDs eindeutig (z.B. suffix _aug_1)
- Optional: Nur neue Eintraege als separates File zum Mergen

## Hinweise

- Reproduzierbarkeit: Random Seed in Config setzen
- Nach Augmentation: Test Set Validation (Skill 8) erneut ausfuehren
