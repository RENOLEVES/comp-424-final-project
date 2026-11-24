# Overnight heuristic testing — results log

Environment: Windows, Python 3.11.14, numpy 1.26.4 (matches tournament versions). All matches run
with `TIME_MARGIN = 0.4` on both sides, no `--strict` (InProcessRunner; confirmed the sandbox also
works fine on this Windows machine via `validate_submission.py`, so validation uses the default
sandboxed dynamic phase).

Decision rule (from CLAUDE.md): decisive games = W + L (draws excluded).
KEEP if win% >= 75% of decisive games with >= 8 decisive games.
DROP if win% <= 30% of decisive games with >= 8 decisive games.
Otherwise "no significant difference": keep only if not slower and logically sound.

## Table

| variant | rule added | weight(s) | opponent (current best) | seeds | W | D | L | decisive win % | mean step time | strikes/forfeits | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v0_baseline | none (copy of old_agent.py) | - | agents/old_agent.py | A (132214, 132219) | 6 | 8 | 6 | 50.0% | 1.60s / 1.60s | 0 / 0 | NOISE CHECK OK |

(rows appended as each test completes)

## Notes

**v0_baseline** (noise check): identical code on both sides, as expected the match is a coin flip
(6-6 decisive, 50.0%) with no strikes or forfeits on either side and matching mean step times. This
confirms the harness, seeds and InProcessRunner sandbox are not biased and the test loop is sound.
`agents/old_agent.py` is the current best going into rule 1.
