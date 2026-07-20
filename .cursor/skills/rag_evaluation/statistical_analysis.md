---
description: Statistische Auswertung der Evaluation-Ergebnisse. Deskriptive Statistik, Ergebnistabellen, 95% CI. Keine Signifikanztests (gemaess Forschungsfragen). Matplotlib/Seaborn.
globs: ["**/evaluation_results_*.json"]
alwaysApply: false
---

# Statistical Analysis

**Zweck:** Statistische Auswertung der RAGAS- und Retrieval-Evaluation-Ergebnisse fuer die Diplomarbeit (Kap. 6).

## Analysen

- **Deskriptive Statistik** – Mittelwert, Median, Standardabweichung pro Metrik
- **Ergebnistabellen** – Wie in FF1, FF3, J2, J4, J6 gefordert (tabellarische Gegenueberstellung)
- **Konfidenzintervalle** – 95% CI wo sinnvoll (z.B. bei Stichproben)
- **Keine Signifikanztests** – Gemaess vereinfachter Forschungsfragen; ehrlicher Vergleich mit Diskussion reicht

## Visualisierungen

- Matplotlib/Seaborn: Balkendiagramme (Metriken pro Modell/Strategie), Boxplots (Score-Verteilung)
- Optional: Heatmaps (Modell x Metrik)

## Skript

```bash
python evaluation/ragas_agents/scripts/analyze_statistics.py --results-dir <evaluation_results_dir> [--output statistical_analysis_YYYYMMDD.json] [--plots-dir evaluation/ragas_agents/output/plots]
```

## Eingaben

- Verzeichnis mit `evaluation_results_*.json` (Embedding, Retrieval, LLM-Judge)
- Optional: Einzelne JSON-Dateien
- Config: Metriken-Liste, CI-Level (0.95)

## Ausgaben

- **statistical_analysis_*.json** – Aggregierte Tabellen, Mittelwerte, Std, CI pro Metrik und Konfiguration
- **Plots** – PNG/PDF fuer Kap. 6 und Anhang
- Optional: CSV-Export fuer Anhang

## Hinweise

- Forschungsfragen verlangen Ergebnistabellen + begruendete Empfehlung, keine p-Werte
- Output fliesst in Report Generation (Skill 14) ein
