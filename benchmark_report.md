# Febrl Real-Data Benchmark Report (llm-crm-data-pipeline)

- Sampled true pairs: 30
- Candidate pairs after deterministic blocking: 27
- Blocking-stage recall ceiling: 19/30 (63%)
- Claude true positives: 16, false positives: 0, false negatives: 3
- Precision (of Claude's positive calls): 100.00%
- Recall (of blocking-reachable true pairs): 84.21%
- Recall (of all sampled true pairs, incl. blocking misses): 53.33%
- F1 (on reachable candidates): 91.43%

Blocking-stage misses are a real, expected limitation (a true pair whose blocking key field was itself corrupted by Febrl's noise generator won't become a candidate at all) - reported separately from Claude's classification accuracy on the candidates it was actually given, per standard record-linkage evaluation practice.
