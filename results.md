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
| v1b_cell05 | 1. cell value | CELL_WEIGHT=0.5 | agents/old_agent.py | A (132214, 132219) + B (900000, 900005) | 7 | 22 | 11 | 38.9% | 1.60s / 1.60s | 0 / 0 | not kept (no significant difference, trends negative) |
| v2_threat_pen | 2. threat penalty (opponent only) | THREAT_WEIGHT=150 | agents/old_agent.py | A (132214, 132219) | 2 | 15 | 3 | 40.0% | 1.60s / 1.60s | 0 / 0 | KEEP (no significant difference; logically sound, not slower) |

(rows appended as each test completes)

## Notes

**Protocol change (mid-session, user instruction):** given how long each 10-game match takes in
this environment, the user told me to test only 1 seed (10 games) per rule from here on, instead of
the full two-seed Round A / two-seed Round B protocol described above. Rule 1 (both weights) and
the start of rule 2 already followed the original multi-seed protocol; rule 2's decision uses both
of its already-started seeds (132214, 132219) since the second was in flight when the instruction
arrived, but rules 3 onward use a single 10-game seed (132214) per variant and decide from that
alone.

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

**v1b_cell05** (rule 1, CELL_WEIGHT=0.5): same rule as v1a, weight 0.5. Symmetry-checked and
validated (PASS) the same way. Round A alone was inconclusive (4W-12D-4L, exactly 50% of 8 decisive
games). Round B's first seed (900000) swung hard the other way (0W-4D-6L); at that point, with the
second Round B seed (900005) still running in the background, the running total stood at
4W-16D-10L (28.6% of 14 decisive games), which already cleared the <=30% DROP bar, so testing moved
on to rule 2 per the user's live instruction rather than waiting. Seed 900005 then finished
3W-6D-1L in v1b_cell05's favor, pulling the **final, complete** total to 7W-22D-11L across all 20
Round A + Round B games: 38.9% of 18 decisive games. That lands in the "no significant difference"
band (neither >=75% KEEP nor <=30% DROP), not a clean DROP as first estimated from the partial data
— correcting that here. Per the decision rule, an inconclusive result is kept only if it is not
slower and the rule is logically sound; 38.9% is still net-negative (losing more than it wins), so
the judgment call is **not kept**, matching the direction of the original call even though the
precise bucket (ambiguous vs. clear-drop) was off with incomplete data. Combined with v1a's clear
drop at weight 1, rule 1 (cell value) is dropped entirely; `agents/old_agent.py` remains the current
best going into rule 2.

**v2_threat_pen** (rule 2, threat penalty only, THREAT_WEIGHT=150): penalizes, per live line, the
case where the opponent has WIN_LENGTH-1 top pieces on that line and can complete it next turn
(the remaining cell is empty with any opponent reserve piece, or holds my piece and the opponent
has a strictly larger reserve piece). Implemented as a second pass over `LINES[WIN_LENGTH]` so the
original line-scoring loop is untouched. By design this is NOT symmetric on its own — confirmed via
a 50-random-position stress test (`evaluate_position(.,.,1,2) != -evaluate_position(.,.,2,1)` in
11/50 cases, every mismatch exactly 150 = THREAT_WEIGHT) — because it only penalizes opponent
threats, never rewards my own; CLAUDE.md explicitly notes "Rule 2 + 3 together = symmetric threat
feature," so this one-sided check is correct, not a bug. Validated (PASS). Tested with the original
two-seed protocol (started before the "1 seed per rule" instruction landed): 2W-15D-3L combined
(40.0% of only 5 decisive games out of 20 — a very high draw rate, both agents converging to very
similar lines of play). That is squarely in the "no significant difference" band. Mean step time is
identical to `agents/old_agent.py` (1.60s) and the rule is logically sound (never walking into an
opponent's one-move win is an unambiguous improvement in principle), so per the decision rule's
"otherwise" branch, **verdict: KEEP.** `experiments/v2_threat_pen.py` becomes the current best
going into rule 3.

**Timing note:** wall-clock gaps between my turns in this session have been multi-hour (the
background match itself only takes roughly 10-20 minutes of CPU time), so the "7 hours from start"
wall-clock budget in claude.md was exceeded by the time rule 1's first variant finished, even though
very little actual compute had been used. The user (awake, mid-session) explicitly said to keep
going regardless, so testing continues past that wall-clock mark; flagging this discrepancy here as
something to check, per the "record what you chose and why" instruction.
