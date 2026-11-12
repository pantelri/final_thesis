# fulfillment_claude_opus_4_8_predicted_statute_only

- model: `anthropic/claude-opus-4-8`
- pairs: 141  scored: 141  parse failures: 0
- **accuracy: 0.5816**

## confusion (gt -> pred)

| gt | pred | n |
|----|------|---|
| fulfilled | fulfilled | 63 |
| fulfilled | partially | 39 |
| partially | partially | 15 |
| partially | fulfilled | 9 |
| not_fulfilled | partially | 6 |
| not_fulfilled | not_fulfilled | 4 |
| partially | not_fulfilled | 3 |
| fulfilled | not_fulfilled | 2 |
