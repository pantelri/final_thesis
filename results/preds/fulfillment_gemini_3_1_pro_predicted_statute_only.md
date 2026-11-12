# fulfillment_gemini_3_1_pro_predicted_statute_only

- model: `google/gemini-3.1-pro-preview`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.6454**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | fulfilled | 77 |
| fulfilled | partially | 15 |
| fulfilled | not_fulfilled | 12 |
| partially | fulfilled | 12 |
| partially | partially | 9 |
| partially | not_fulfilled | 6 |
| not_fulfilled | not_fulfilled | 5 |
| not_fulfilled | fulfilled | 4 |
| not_fulfilled | partially | 1 |
