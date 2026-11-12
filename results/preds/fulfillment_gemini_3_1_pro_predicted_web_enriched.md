# fulfillment_gemini_3_1_pro_predicted_web_enriched

- model: `google/gemini-3.1-pro-preview`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.5248**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | fulfilled | 57 |
| fulfilled | partially | 46 |
| partially | partially | 14 |
| partially | fulfilled | 8 |
| partially | not_fulfilled | 5 |
| not_fulfilled | partially | 4 |
| not_fulfilled | fulfilled | 3 |
| not_fulfilled | not_fulfilled | 3 |
| fulfilled | not_fulfilled | 1 |
