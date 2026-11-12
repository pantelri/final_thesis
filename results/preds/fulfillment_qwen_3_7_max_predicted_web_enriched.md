# fulfillment_qwen_3_7_max_predicted_web_enriched

- model: `qwen/qwen3.7-max`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.6099**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | fulfilled | 69 |
| fulfilled | partially | 34 |
| partially | partially | 14 |
| partially | fulfilled | 8 |
| partially | not_fulfilled | 5 |
| not_fulfilled | partially | 4 |
| not_fulfilled | fulfilled | 3 |
| not_fulfilled | not_fulfilled | 3 |
| fulfilled | not_fulfilled | 1 |
