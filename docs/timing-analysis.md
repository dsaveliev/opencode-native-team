# Timing Analysis: Why v4 Took 81 Minutes

## The 38-Minute Gap

v1 (barebone): 43 min. v4 (combined): 81 min. Delta: 38 min.

Decomposition of the delta:

| Cause | Time | % of delta |
|---|---:|---:|
| Shutdown test block (single subagent, 28.2 min) | **28.2** | **74%** |
| 5-axis review (9.6 min vs 5.6 in v1) | +4.0 | 10% |
| Tester dispatch rejection + retry | +3.3 | 9% |
| Control verdict after fixes (v1 didn't need) | +3.5 | 9% |
| TDD overhead on 4 coding tasks (~2 min each) | +8.0 | 21%* |
| Openspec artifacts upfront (4 min) | +4.0 | 10%* |
| Orchestrator coordination (11.9 vs 7.1 min) | +4.8 | 13%* |

*Percentages overlap — some items partially cover the baseline 43 min.

## The Dominant Cost: One Subagent

The shutdown test block (28.2 min) accounts for **74% of the total overrun**.
Without it, v4 would have taken ~53 min — only +23% over v1.

**Root cause chain:**
1. v4's evidence-based `[x]` requirement ("only mark complete with proof") is correct
2. But the coder interpreted "proof" as "exhaustive test matrices"
3. Combined with slow `-race` compilation, this created a perfectionism spiral
4. The orchestrator's parent transcript was silent for 15+ minutes (subagent running),
   making it appear hung from the outside

**v5 fix:** "Test tasks: 5-minute timeout; 'sufficient' = typical case + boundaries +
races" — explicitly caps what "proof" means for test tasks.

## Subagent Time Comparison

| Arm | Total | Subagent work | Coordination |
|---|---:|---:|---:|
| v1 (barebone) | 43.0 min | 35.8 min (7 sessions) | 7.1 min |
| v2 (+skills) | 39.3 min | 31.2 min (7 sessions) | 8.1 min |
| v4 (combined) | 80.8 min | 68.8 min (12 sessions) | 11.9 min |

v4 coordination overhead (+4.8 min over v1) is modest — the dual-layer contract
adds ~2 min to planning and ~3 min to inter-delegation decisions.

## v5 Time Projections

| Fix | Expected saving |
|---|---:|
| Test timeout (5.1) | −20 min (shutdown block capped) |
| Parallel read-only delegation (4.1) | −8 min (reviewer ∥ tester) |
| No external_directory retry (4.3) | −3 min |
| Wave batching (4.4) | −2 min (fewer coordination hops) |
| Per-task light review replaces long final review | ±0 min (distributed, same total) |
| **Net projection** | **≤ 55 min** |

## Key Insight

The native pattern's coordination overhead is nearly flat (~7-12 min regardless
of configuration). Time scales with **subagent work**, which is driven by the
scope of what they're asked to do. Contract directives that limit scope
(timeouts, "sufficient" definitions) are the primary time lever — not
architectural changes to the team.
