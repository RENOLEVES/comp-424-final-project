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
| v1a_cell1 | 1. cell value | CELL_WEIGHT=1 | agents/old_agent.py | A (132214, 132219) | 1 | 11 | 8 | 11.1% | 1.60s / 1.60s | 0 / 0 | DROP |

(rows appended as each test completes)

## Notes

**v0_baseline** (noise check): identical code on both sides, as expected the match is a coin flip
(6-6 decisive, 50.0%) with no strikes or forfeits on either side and matching mean step times. This
confirms the harness, seeds and InProcessRunner sandbox are not biased and the test loop is sound.
`agents/old_agent.py` is the current best going into rule 1.

**v1a_cell1** (rule 1, CELL_WEIGHT=1): adds `score += CELL_WEIGHT * (sum of live-line count over my
top-piece cells - same sum for the opponent)`, computed alongside the existing line-weight loop
(incrementing `cell_value[row, col]` for every cell of every unblocked line). Symmetry sanity-checked
(evaluate_position(.,.,1,2) == -evaluate_position(.,.,2,1)) before testing. Validated with
`validate_submission.py` (PASS, only the expected filename warning). Round A result: 1W-11D-8L vs
`agents/old_agent.py` (9 decisive games, 11.1% win rate) — well under the 30% DROP threshold with
>= 8 decisive games. **Verdict: DROP.** At weight 1 the cell-value bonus (up to several points per
cell, lines up to 500) is apparently strong enough to distort the search's move ordering/evaluation
away from the line-completion heuristic that was already working, making the agent play more
passively for "central control" and losing close races it used to win. No strikes or forfeits;
step times identical, so this is a heuristic-quality loss, not a search/engineering problem.

**Timing note:** wall-clock gaps between my turns in this session have been multi-hour (the
background match itself only takes roughly 10-20 minutes of CPU time), so the "7 hours from start"
wall-clock budget in claude.md was exceeded by the time rule 1's first variant finished, even though
very little actual compute had been used. The user (awake, mid-session) explicitly said to keep
going regardless, so testing continues past that wall-clock mark; flagging this discrepancy here as
something to check, per the "record what you chose and why" instruction.
