# fulfillment_claude_opus_4_8_predicted_web_enriched

- model: `anthropic/claude-opus-4-8`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.5319**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | fulfilled | 53 |
| fulfilled | partially | 49 |
| partially | partially | 19 |
| not_fulfilled | partially | 7 |
| partially | not_fulfilled | 5 |
| partially | fulfilled | 3 |
| not_fulfilled | not_fulfilled | 3 |
| fulfilled | not_fulfilled | 2 |
