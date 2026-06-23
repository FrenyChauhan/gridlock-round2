# Why Recent Data Matters More

## The Decay Model

Violations from last week tell you more about next week
than violations from 5 months ago. Traffic patterns shift:

- New construction → new illegal parking zones emerge
- Metro station opens → surrounding violations spike
- Seasonal events → predictable annual patterns
- Enforcement history → zones with frequent patrolling 
  may show reduced violations (deterrence effect)

## Implementation

sample_weight = decay_rate ^ weeks_ago

decay_rate = 0.85 means:
  Last week:    weight 1.00
  2 weeks ago:  weight 0.85
  1 month ago:  weight 0.52
  3 months ago: weight 0.14

## When to Increase Decay Rate
- 0.90: stable enforcement area, slow-changing patterns
- 0.85: default Bengaluru urban (current)
- 0.75: rapidly developing areas (new construction, events)
- 0.65: highly volatile zones (festival seasons)

Per-cluster decay rates are a Phase 2 feature.
