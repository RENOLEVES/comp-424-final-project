## Summary

**Final current best: `experiments/v4_fork.py`**, containing baseline (unchanged old_agent.py line
scoring + material/reserve scoring) plus:
- rule 2: threat penalty — `score -= 150 *` (number of opponent live-line threats)
- rule 3: threat reward — `score += 150 *` (number of my live-line threats) — makes rule 2 symmetric
- rule 4: fork bonus — `+-400` when a side has 2+ simultaneous threats

Rule 1 (cell value, both weights 1 and 0.5) and rule 5 (pin penalty, weight 10) were tested and not
kept. Copy `experiments/v4_fork.py` to `agents/student_agent.py` if you agree with these verdicts —
I did not copy it myself, per the instructions.

| rule | tested as | verdict | why |
|---|---|---|---|
| 1. cell value (weight 1) | v1a_cell1 | DROP | 11.1% decisive win rate vs old_agent (9 decisive/20 games) |
| 1. cell value (weight 0.5) | v1b_cell05 | not kept | 38.9% decisive win rate vs old_agent (18 decisive/20 games, net negative) |
| 2. threat penalty | v2_threat_pen | KEEP | 40.0% (ambiguous, small sample), but logically sound & no slower |
| 3. threat reward | v3_threat_reward | KEEP | 50.0% (ambiguous, small sample), completes rule 2 into a symmetric feature |
| 4. fork bonus | v4_fork | KEEP | 0 decisive games (all draws), kept on soundness + no speed cost |
| 5. pin penalty | v5_pin | not kept | 33.3% decisive win rate vs v4_fork, matches CLAUDE.md's own "may hurt" expectation |

**Things to check / caveats:**
- **Testing rigor dropped off after rule 1.** Rules 2-5 were each decided from a single 10-game
  seed (132214) instead of the full two-seed Round A (and possible Round B) protocol, per a live
  instruction mid-session ("you only need to test 1 seed per rule"). Rules 2, 3 and 5 all landed in
  the ambiguous "no significant difference" band on tiny decisive-game counts (3, 4, and 6 decisive
  games respectively), and rule 4's single seed produced **zero** decisive games at all. These KEEP
  verdicts leaned on "not slower + logically sound" rather than a clear statistical edge — they are
  defensible judgment calls, not confident wins. If you want higher confidence before trusting rules
  2-4, it would be worth re-running each one (or the final v4_fork vs. old_agent.py directly) with
  the full Round A + Round B protocol from CLAUDE.md.
- **Wall-clock budget was exceeded.** The "stop starting new matches after 7 hours" rule in this
  file was written assuming compute-bound execution, but the actual bottleneck in this session was
  multi-hour gaps between my turns (each 10-game match itself only took ~10-20 minutes of real
  compute). By the time rule 1's first variant finished, the nominal 7-hour wall-clock mark had
  already passed. You (awake, mid-session) explicitly told me to keep going regardless, so I did;
  flagging it here since the original note assumed I'd be working unsupervised all night.
- **Rule 2 alone is intentionally asymmetric.** `evaluate_position(.,.,1,2) != -evaluate_position(.,.,2,1)`
  for `v2_threat_pen.py` on its own (confirmed via a 50-position stress test, every mismatch exactly
  150 = THREAT_WEIGHT) because it only penalizes the opponent's threats, never rewards mine. This
  matches CLAUDE.md's own note ("Rule 2 + 3 together = symmetric threat feature") and is not a bug —
  just flagging it since the generic "the evaluation must be symmetric, if not fix it" instruction
  doesn't literally hold for that one intermediate variant.
- **`.gitignore` was edited.** This repo's `.gitignore` is a whitelist (everything ignored by
  default, specific files let back in). `experiments/` and `results.md` didn't exist yet and were
  being silently ignored, so I added `!/results.md` and `!/experiments/` (plus an ignore for
  `experiments/**/__pycache__/`) following the exact pattern the file's own header comment
  documents. `agents/student_agent.py` itself was never touched.
- All variants passed `validate_submission.py` (PASS, only the expected "wrong filename" warning)
  and every match ran with 0 strikes/forfeits and identical mean step times (1.60s) across the
  board — no engineering/timeout issues anywhere, only heuristic-quality differences.

---

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
| v3_threat_reward | 3. threat reward (symmetric with rule 2) | THREAT_WEIGHT=150 | experiments/v2_threat_pen.py | 132214 only | 2 | 6 | 2 | 50.0% | 1.60s / 1.60s | 0 / 0 | KEEP (no significant difference; logically sound, not slower) |
| v4_fork | 4. fork bonus | FORK_WEIGHT=400 | experiments/v3_threat_reward.py | 132214 only | 0 | 10 | 0 | n/a (0 decisive) | 1.60s / 1.60s | 0 / 0 | KEEP (no significant difference; logically sound, not slower) |
| v5_pin | 5. pin penalty | PIN_WEIGHT=10 | experiments/v4_fork.py | 132214 only | 2 | 4 | 4 | 33.3% | 1.60s / 1.60s | 0 / 0 | NOT KEPT (trends negative, matches CLAUDE.md's prior "may hurt" note) |

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

**v3_threat_reward** (rule 3, threat reward, on top of v2_threat_pen): adds the mirror-image reward
for my own threats, `score += THREAT_WEIGHT * my_threats`, using the exact same completion check as
rule 2 but with attacker/defender swapped. Refactored the shared check into a nested
`_count_threats(attacker, defender)` helper inside `evaluate_position` (still "only
evaluate_position changed" — the helper is local to it) so rule 2's existing opponent-threat count
and the new my-threat count can't drift apart through copy-paste; confirmed this refactor preserves
rule 2's behavior via validation + the stress test below. Stress-tested symmetry over 50 random
positions: `evaluate_position(.,.,1,2) == -evaluate_position(.,.,2,1)` held in all 50 (as expected,
since this is rule 2 + 3 together, which CLAUDE.md calls out as the symmetric pairing). Validated
(PASS). Tested with the new single-seed protocol (seed 132214 only) against the current best,
`experiments/v2_threat_pen.py`: 2W-6D-2L (50.0% of 4 decisive games) — no significant difference,
tiny sample. Mean step time identical (1.60s) and the rule is logically sound (same justification
as rule 2, now applied symmetrically), so **verdict: KEEP.** `experiments/v3_threat_reward.py`
becomes the current best going into rule 4 (a threat rule was kept, so rule 4 is tested).

**v4_fork** (rule 4, fork bonus, on top of v3_threat_reward): reuses the `my_threats` /
`opponent_threats` counts already computed for rules 2+3 and adds `FORK_WEIGHT=400` for my side
when `my_threats >= 2`, subtracts it when `opponent_threats >= 2`. Stress-tested symmetric over 50
random positions (0/50 mismatches) and validated (PASS). Single-seed test (132214) against the
current best, `experiments/v3_threat_reward.py`: all 10 games were draws (0 decisive games) — the
most extreme case of "no significant difference" possible; both agents are apparently strong/even
enough at this point that this seed's configurations never resolve to a win either way. Step time
unchanged (1.60s) and the fork concept (an unstoppable double threat) is a standard, logically
sound tactical idea, so **verdict: KEEP.** `experiments/v4_fork.py` becomes the current best going
into rule 5. (Given the 0-decisive result here, this is a weaker basis for "KEEP" than the earlier
rules' — flagging that if the user wants a second seed for confidence, it's worth re-checking, but
proceeding per the "1 seed per rule" instruction.)

**v5_pin** (rule 5, pin penalty, on top of v4_fork): for each cell where my top piece buries an
opponent piece in a smaller slot underneath, `score -= PIN_WEIGHT`; mirrored, for each cell where
the opponent's top piece buries one of mine, `score += PIN_WEIGHT` — implemented exactly as
CLAUDE.md specifies (the penalty direction is intentionally from the burying side's perspective,
not the buried side's). Stress-tested over 100 random positions with 14 random moves each (enough
plies that ~50/100 positions actually had at least one buried piece, so the pin logic was genuinely
exercised, not vacuously symmetric): 0 asymmetries. Validated (PASS). Single-seed test (132214)
against the current best, `experiments/v4_fork.py`: 2W-4D-4L (33.3% of 6 decisive games) — below
even odds, in the "no significant difference" band but trending clearly negative, consistent with
CLAUDE.md's own note that "earlier tests suggest this may hurt." **Verdict: NOT KEPT.** Pinning a
piece (or being pinned) does not seem to reliably translate into a better position for the side on
top within this search depth/horizon, matching the documented prior expectation.
`experiments/v4_fork.py` (rules 2+3+4) remains the final current best.

**Timing note:** wall-clock gaps between my turns in this session have been multi-hour (the
background match itself only takes roughly 10-20 minutes of CPU time), so the "7 hours from start"
wall-clock budget in claude.md was exceeded by the time rule 1's first variant finished, even though
very little actual compute had been used. The user (awake, mid-session) explicitly said to keep
going regardless, so testing continues past that wall-clock mark; flagging this discrepancy here as
something to check, per the "record what you chose and why" instruction.
