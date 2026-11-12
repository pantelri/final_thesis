# fulfillment_claude_opus_4_8_oracle_web_enriched

- model: `anthropic/claude-opus-4-8`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.4610**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | partially | 56 |
| fulfilled | fulfilled | 42 |
| partially | partially | 18 |
| partially | not_fulfilled | 8 |
| fulfilled | not_fulfilled | 6 |
| not_fulfilled | partially | 5 |
| not_fulfilled | not_fulfilled | 5 |
| partially | fulfilled | 1 |
