# fulfillment_qwen_3_7_max_oracle_web_enriched

- model: `qwen/qwen3.7-max`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.5319**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | fulfilled | 54 |
| fulfilled | partially | 46 |
| partially | partially | 15 |
| partially | not_fulfilled | 7 |
| not_fulfilled | not_fulfilled | 6 |
| partially | fulfilled | 5 |
| not_fulfilled | partially | 4 |
| fulfilled | not_fulfilled | 4 |
