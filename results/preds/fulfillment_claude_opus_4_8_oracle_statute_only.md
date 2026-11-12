# fulfillment_claude_opus_4_8_oracle_statute_only

- model: `anthropic/claude-opus-4-8`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.4681**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | partially | 55 |
| fulfilled | fulfilled | 44 |
| partially | partially | 16 |
| partially | not_fulfilled | 7 |
| not_fulfilled | not_fulfilled | 6 |
| fulfilled | not_fulfilled | 5 |
| not_fulfilled | partially | 4 |
| partially | fulfilled | 4 |
