# fulfillment_qwen_3_7_max_predicted_statute_only

- model: `qwen/qwen3.7-max`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.6667**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | fulfilled | 79 |
| fulfilled | partially | 21 |
| partially | partially | 12 |
| partially | fulfilled | 12 |
| not_fulfilled | partially | 5 |
| fulfilled | not_fulfilled | 4 |
| partially | not_fulfilled | 3 |
| not_fulfilled | not_fulfilled | 3 |
| not_fulfilled | fulfilled | 2 |
