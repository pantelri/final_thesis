# fulfillment_qwen_3_7_max_oracle_statute_only

- model: `qwen/qwen3.7-max`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.6241**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | fulfilled | 69 |
| fulfilled | partially | 27 |
| partially | partially | 12 |
| partially | fulfilled | 8 |
| fulfilled | not_fulfilled | 8 |
| not_fulfilled | not_fulfilled | 7 |
| partially | not_fulfilled | 7 |
| not_fulfilled | fulfilled | 3 |
