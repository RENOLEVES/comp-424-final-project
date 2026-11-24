"""Student agent: edit ONLY this file.

Search implementation produced with assistance from OpenAI Codex. The team
remains responsible for the submitted code and its explanation.
"""
from agents.agent import Agent
from store import register_agent
from helpers import Move, get_valid_moves, check_move_validity, LINES
from constants import *
import time


TIME_MARGIN = 0.4               # stop searching at STEP_TIME_LIMIT - 0.4 s

# Evaluation weights.
CELL_WEIGHT = 0.5
THREAT_WEIGHT = 150
FORK_WEIGHT = 400

N_CELLS = BOARD_SIZE * BOARD_SIZE
SIZES = (SMALL, MEDIUM, LARGE)
WIN = 1_000_000                 # score of a win, from root_player's point of view
MATE_T = WIN - 1_000            # |score| above this means a forced win/loss
INF = float("inf")
LINE_WEIGHTS = (0, 2, 12, 80, 500)


class _SearchTimeout(Exception):
    """Raised internally when the safe search deadline has been reached."""


# Top piece of every possible cell code, worked out once up front.
TOP_OWNER = [0] * 64
TOP_SIZE = [-1] * 64
for _code in range(64):
    for _s in (LARGE, MEDIUM, SMALL):
        _o = (_code >> (2 * _s)) & 3
        if _o == PLAYER_1 or _o == PLAYER_2:
            TOP_OWNER[_code] = _o
            TOP_SIZE[_code] = _s
            break


def _encode(board, reserves):
    """Return a compact representation of the board and reserves, and the set of obstacle cells."""
    cells = []
    obstacle = set()
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            code = 0
            for s in SIZES:
                v = int(board[r, c, s])
                if v == OBSTACLE:
                    obstacle.add(r * BOARD_SIZE + c)
                    v = 0
                code |= v << (2 * s)
            cells.append(code)
    res = [[0, 0, 0],
           [int(reserves[PLAYER_1, s]) for s in SIZES],
           [int(reserves[PLAYER_2, s]) for s in SIZES]]
    return cells, res, obstacle


def _live_lines(obstacle):
    """Return the living lines, the live lines through
    each cell, and the number of live lines through each cell (its value).
    Cell value is used to order moves in the search."""
    lines = []
    for line in LINES[WIN_LENGTH]:
        idx = tuple(r * BOARD_SIZE + c for r, c in line)
        if not any(i in obstacle for i in idx):
            lines.append(idx)
    lines_at = [[ln for ln in lines if i in ln] for i in range(N_CELLS)]
    cell_value = [len(lines_at[i]) for i in range(N_CELLS)]
    return lines, lines_at, cell_value


def _gen_moves(cells, res, free, p):
    """Return the list of legal moves of player p as (src, dest, size); src -1 means a placement."""
    tops = [TOP_SIZE[code] for code in cells]
    moves = []
    rp = res[p]
    for s in SIZES:
        if rp[s] > 0:
            for d in free:
                if tops[d] < s:
                    moves.append((-1, d, s))
    if ALLOW_MOVES:
        for src in free:
            code = cells[src]
            if TOP_OWNER[code] == p:
                s = TOP_SIZE[code]
                for d in free:
                    if d != src and tops[d] < s:
                        moves.append((src, d, s))
    return moves


def _winner_after(cells, lines_at, m, src, d):
    """Winner right after some move played.

    Only the tops of src and d can have changed, so only lines through them
    need rechecking. The opponent is checked first (the uncovering rule).
    """
    q = 3 - m
    if src >= 0:
        for line in lines_at[src]:
            if all(TOP_OWNER[cells[i]] == q for i in line):
                return q
    for line in lines_at[d]:
        if all(TOP_OWNER[cells[i]] == m for i in line):
            return m
    if src >= 0:
        for line in lines_at[src]:
            if all(TOP_OWNER[cells[i]] == m for i in line):
                return m
    return 0


def _threat_cells(own, sz, res, lines, free, attacker, defender):
    """Return the set of cells that attacker can play to complete a line next turn.

    A cell is a threat if it is the only empty cell in a line that has at least one 
    of attacker's pieces and no pieces of defender. This will reward the player for creating a fork.
    """
    ra = res[attacker]
    reserve_max = -1
    for s in SIZES:
        if ra[s] > 0:
            reserve_max = s
    board_pieces = []
    if ALLOW_MOVES:
        for i in free:
            if own[i] == attacker:
                board_pieces.append((sz[i], i))

    cells = set()
    for line in lines:
        count = 0
        open_cell = -1
        for i in line:
            if own[i] == attacker:
                count += 1
            else:
                open_cell = i
        if open_cell < 0 or count != len(line) - 1:
            continue
        if own[open_cell] == defender:
            needed = sz[open_cell] + 1
        else:
            needed = SMALL
        if reserve_max >= needed:
            cells.add(open_cell)
            continue
        for size, i in board_pieces:
            if size >= needed and i not in line:
                cells.add(open_cell)
                break
    return cells


def evaluate_position(cells, res, lines, free, cell_value, me):
    """Return a position score from ``me``'s point of view.
    Goal: To win the game, a player must complete a line with their pieces. 

    The evaluation function is designed by following concepts:
    Preprocessing.
    1. Remove the the lines that are blocked by the obstacle.
    2. Compute each cell's value with # of live lines through it.

    Scored as (my value - opponent's value):
    Reward.
    1. Reward my living lines that are uncontested by the opponent, with increasing weights by piece count.
    2. Reward the cells that has more control + size of the piece on top + # of piece in reserve. (# of living lines through it)
    3. Reward bonus points to fork (FORK_WEIGHT) for holding two or more threat cells at once.

    Penalize. 
    2. Penalize the opponent's living lines that are uncontested by me, with increasing weights by piece count.
    """
    op = 3 - me
    own = [TOP_OWNER[c] for c in cells]
    sz = [TOP_SIZE[c] for c in cells]
    score = 0.0

    for line in lines:
        mine = 0
        theirs = 0
        for i in line:
            o = own[i]
            if o == me:
                mine += 1
            elif o == op:
                theirs += 1
        if theirs == 0:
            score += LINE_WEIGHTS[mine]
        if mine == 0:
            score -= LINE_WEIGHTS[theirs]

    for i in free:
        o = own[i]
        if o == me:
            score += CELL_WEIGHT * cell_value[i] + sz[i] + 1
        elif o == op:
            score -= CELL_WEIGHT * cell_value[i] + sz[i] + 1
    rm, ro = res[me], res[op]
    for s in SIZES:
        score += (s + 1) * (rm[s] - ro[s])

    my_threats = len(_threat_cells(own, sz, res, lines, free, me, op))
    op_threats = len(_threat_cells(own, sz, res, lines, free, op, me))
    score += THREAT_WEIGHT * (my_threats - op_threats)
    if my_threats >= 2:
        score += FORK_WEIGHT
    if op_threats >= 2:
        score -= FORK_WEIGHT
    return score


def _to_move(mv):
    """Convert a compact move to a Move object."""
    src, d, s = mv
    dest = (d // BOARD_SIZE, d % BOARD_SIZE)
    if src < 0:
        return Move(None, dest, s)
    return Move((src // BOARD_SIZE, src % BOARD_SIZE), dest, s)


@register_agent("student_agent")          # do not change this string
class StudentAgent(Agent):
    """Iterative-deepening minimax agent with alpha-beta pruning, running on the
    compact board above. Leaves are scored by evaluate_position."""

    def __init__(self):
        """Set up per-game state before the first move."""
        super().__init__()
        self.name = "StudentAgent"
        self.turn_number = 0
        self.root_player = PLAYER_1
        self.root_opponent = PLAYER_2
        self.last_depth = 0
        # Compact position used by the search (filled in by step()).
        self._cells = []
        self._res = []
        self._free = []
        self._lines = []
        self._lines_at = []
        self._cell_value = []
        self._deadline = 0.0
        self._nodes = 0

    def _check_time(self):
        """Stop the current iteration before the referee's time limit.

        The clock is only read every 512 nodes to keep the check cheap."""
        self._nodes += 1
        if not (self._nodes & 511) and time.perf_counter() >= self._deadline:
            raise _SearchTimeout

    def _terminal_score(self, winner, depth):
        """Score a known winner, preferring faster wins and slower losses."""
        if winner == self.root_player:
            return WIN + depth
        if winner == self.root_opponent:
            return -WIN - depth
        return 0

    def _make(self, mv, p):
        """Play mv for p on the compact board."""
        src, d, s = mv
        shift = 2 * s
        cells = self._cells
        if src < 0:
            self._res[p][s] -= 1
        else:
            cells[src] &= ~(3 << shift)
        cells[d] |= p << shift

    def _unmake(self, mv, p):
        """Exactly undo _make(mv, p)."""
        src, d, s = mv
        shift = 2 * s
        cells = self._cells
        cells[d] &= ~(3 << shift)
        if src < 0:
            self._res[p][s] += 1
        else:
            cells[src] |= p << shift

    def _order(self, moves, p):
        """Order moves for pruning: gobbling captures first, then central
        cells, placements and bigger pieces. Correctness never depends on it."""
        cells = self._cells
        cell_value = self._cell_value
        q = 3 - p

        def key(mv):
            src, d, s = mv
            capture = 1 if TOP_OWNER[cells[d]] == q else 0   # covers an opponent
            return (capture, s, cell_value[d], 1 if src < 0 else 0)

        moves.sort(key=key, reverse=True)
        return moves

    def _minimax(self, player_to_move, depth, alpha, beta, ply):
        """Return the alpha-beta minimax value of one node, from root_player's
        point of view. The parent has already checked whether its move won."""
        if ply >= MAX_PLIES:
            return 0
        self._check_time()
        if depth <= 0:
            return evaluate_position(self._cells, self._res, self._lines,
                                     self._free, self._cell_value,
                                     self.root_player)

        next_player = 3 - player_to_move
        moves = _gen_moves(self._cells, self._res, self._free, player_to_move)
        if not moves:
            if ALLOW_MOVES:
                # No legal move: the side to move loses.
                return self._terminal_score(next_player, depth)
            if not _gen_moves(self._cells, self._res, self._free, next_player):
                return 0                        # placements-only rules: draw
            return self._minimax(next_player, depth - 1, alpha, beta, ply + 1)

        self._order(moves, player_to_move)

        if player_to_move == self.root_player:
            # Maximizing node.
            value = -INF
            for mv in moves:
                self._make(mv, player_to_move)
                winner = _winner_after(self._cells, self._lines_at,
                                       player_to_move, mv[0], mv[1])
                if winner:
                    child = self._terminal_score(winner, depth - 1)
                else:
                    child = self._minimax(next_player, depth - 1,
                                          alpha, beta, ply + 1)
                self._unmake(mv, player_to_move)
                if child > value:
                    value = child
                if value > alpha:
                    alpha = value
                if alpha >= beta:
                    break                       # beta cutoff
            return value

        # Minimizing node.
        value = INF
        for mv in moves:
            self._make(mv, player_to_move)
            winner = _winner_after(self._cells, self._lines_at,
                                   player_to_move, mv[0], mv[1])
            if winner:
                child = self._terminal_score(winner, depth - 1)
            else:
                child = self._minimax(next_player, depth - 1,
                                      alpha, beta, ply + 1)
            self._unmake(mv, player_to_move)
            if child < value:
                value = child
            if value < beta:
                beta = value
            if alpha >= beta:
                break                           # alpha cutoff
        return value

    def _search_depth(self, p, moves, depth, ply):
        """Complete one root iteration and return (best_score, best_move).

        `moves` is reordered in place so the best move comes first next time,
        which is where iterative deepening pays off."""
        next_player = 3 - p
        alpha = -INF
        beta = INF
        best = -INF
        best_move = moves[0]
        scored = []
        for mv in moves:
            self._make(mv, p)
            winner = _winner_after(self._cells, self._lines_at, p, mv[0], mv[1])
            if winner:
                v = self._terminal_score(winner, depth - 1)
            else:
                v = self._minimax(next_player, depth - 1, alpha, beta, ply + 1)
            self._unmake(mv, p)
            scored.append((v, mv))
            if v > best:
                best = v
                best_move = mv
            if best > alpha:
                alpha = best
            if best >= WIN:
                break                           # immediate win: look no further
        # stable sort: best first, the rest keep the previous order among ties
        order = {mv: i for i, mv in enumerate(moves)}
        scored.sort(key=lambda t: (-t[0], order[t[1]]))
        searched = {mv for _, mv in scored}
        moves[:] = [mv for _, mv in scored] + [mv for mv in moves if mv not in searched]
        return best, best_move

    def step(self, board, reserves, player, opponent):
        """Return a legal move found by the last fully completed search depth."""
        start = time.perf_counter()
        self._deadline = start + max(0.01, STEP_TIME_LIMIT - TIME_MARGIN)
        self._nodes = 0
        self.root_player = player
        self.root_opponent = opponent
        ply = 2 * self.turn_number + player - 1
        self.turn_number += 1

        legal = get_valid_moves(board, reserves, player)
        # The referee calls step only when a legal move exists. Keeping the
        # first generated move guarantees a legal fallback if anything fails.
        fallback = legal[0]
        if len(legal) == 1:
            return fallback
        try:
            self._cells, self._res, obstacle = _encode(board, reserves)
            self._free = [i for i in range(N_CELLS) if i not in obstacle]
            self._lines, self._lines_at, self._cell_value = _live_lines(obstacle)

            moves = _gen_moves(self._cells, self._res, self._free, player)
            if not moves:
                return fallback
            self._order(moves, player)

            best_move = moves[0]
            depth = 1
            self.last_depth = 0
            while True:
                try:
                    score, best_move = self._search_depth(player, moves, depth, ply)
                except _SearchTimeout:
                    break
                self.last_depth = depth
                # stop when there is a forced win/loss or the maximum depth is reached
                if abs(score) > MATE_T or ply + depth >= MAX_PLIES:
                    break
                depth += 1

            move = _to_move(best_move)
            if check_move_validity(board, reserves, player, move):
                return move
        except Exception:
            pass
        return fallback
