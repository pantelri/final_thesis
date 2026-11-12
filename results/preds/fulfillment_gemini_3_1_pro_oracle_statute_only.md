# fulfillment_gemini_3_1_pro_oracle_statute_only

- model: `google/gemini-3.1-pro-preview`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.5957**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | fulfilled | 68 |
| fulfilled | partially | 26 |
| partially | not_fulfilled | 11 |
| partially | partially | 10 |
| fulfilled | not_fulfilled | 10 |
| not_fulfilled | not_fulfilled | 6 |
| partially | fulfilled | 6 |
| not_fulfilled | partially | 3 |
| not_fulfilled | fulfilled | 1 |
