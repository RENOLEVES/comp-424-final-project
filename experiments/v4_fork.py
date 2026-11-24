"""Student agent: edit ONLY this file.

Search implementation produced with assistance from OpenAI Codex. The team
remains responsible for the submitted code and its explanation.
"""
from agents.agent import Agent
from store import register_agent
from helpers import (Move, get_valid_moves, execute_move, check_winner,
                     check_endgame, copy_state, top_view, LINES)
from constants import *
import numpy as np
import time


WIN_SCORE = 1_000_000
TIME_MARGIN = 0.4


class _SearchTimeout(Exception):
    """Raised internally when the safe search deadline has been reached."""


THREAT_WEIGHT = 150


FORK_WEIGHT = 400


def evaluate_position(board, reserves, player, opponent):
    """Rule 4 (fork bonus, on top of rules 2+3's threat penalty/reward):
    baseline line/material heuristic, the symmetric threat penalty/reward,
    and a bonus for a side that holds 2 or more simultaneous threats (a
    fork the opponent cannot block in one move).
    """
    owners, sizes = top_view(board)
    score = 0

    # Reward uncontested lines increasingly as they approach completion.
    line_weights = (0, 2, 12, 80, 500)
    for line in LINES[WIN_LENGTH]:
        mine = 0
        theirs = 0
        blocked = False
        for row, col in line:
            owner = int(owners[row, col])
            if owner == OBSTACLE:
                blocked = True
                break
            mine += owner == player
            theirs += owner == opponent
        if blocked:
            continue
        if theirs == 0:
            score += line_weights[mine]
        if mine == 0:
            score -= line_weights[theirs]

    def _count_threats(attacker, defender):
        """Count live lines where `attacker` has WIN_LENGTH-1 top pieces and can complete it
        next turn: the remaining cell is empty with any attacker reserve piece, or holds a
        `defender` piece the attacker has a strictly larger reserve piece to cover."""
        count = 0
        for line in LINES[WIN_LENGTH]:
            attacker_count = 0
            blocked = False
            open_cell = None
            for row, col in line:
                owner = int(owners[row, col])
                if owner == OBSTACLE:
                    blocked = True
                    break
                if owner == attacker:
                    attacker_count += 1
                else:
                    open_cell = (row, col)
            if blocked or open_cell is None or attacker_count != len(line) - 1:
                continue
            orow, ocol = open_cell
            open_owner = int(owners[orow, ocol])
            if open_owner == EMPTY:
                if bool(np.any(reserves[attacker] >= 1)):
                    count += 1
            elif open_owner == defender:
                open_size = int(sizes[orow, ocol])
                if open_size < LARGE and bool(np.any(reserves[attacker, open_size + 1:] >= 1)):
                    count += 1
        return count

    # Rule 2: penalize lines where the opponent threatens to complete on their next turn.
    opponent_threats = _count_threats(opponent, player)
    score -= THREAT_WEIGHT * opponent_threats
    # Rule 3: reward lines where I hold the same kind of threat against the opponent.
    my_threats = _count_threats(player, opponent)
    score += THREAT_WEIGHT * my_threats

    # Rule 4: a side with 2 or more simultaneous threats has an unblockable fork.
    if my_threats >= 2:
        score += FORK_WEIGHT
    if opponent_threats >= 2:
        score -= FORK_WEIGHT

    # Prefer visible control by larger pieces and retain useful reserve pieces.
    for size in (SMALL, MEDIUM, LARGE):
        weight = size + 1
        score += weight * int(np.count_nonzero((owners == player) & (sizes == size)))
        score -= weight * int(np.count_nonzero((owners == opponent) & (sizes == size)))
        score += weight * int(reserves[player, size] - reserves[opponent, size])
    return score


@register_agent("student_agent")          # do not change this string
class StudentAgent(Agent):
    """Iterative-deepening minimax agent with alpha-beta pruning."""

    def __init__(self):
        """Set up per-game state before the first move."""
        super().__init__()
        self.name = "StudentAgent"
        self.turn_number = 0
        self.deadline = 0.0
        self.root_player = PLAYER_1
        self.root_opponent = PLAYER_2

    def _check_time(self):
        """Stop the current iteration before the referee's two-second limit."""
        if time.perf_counter() >= self.deadline:
            raise _SearchTimeout

    @staticmethod
    def _move_order_value(move, preferred):
        """Return a cheap ordering key; correctness never depends on this key."""
        if move == preferred:
            return 10_000
        # Try placements before relocations and larger pieces before smaller ones.
        row, col = move.dest
        centrality = 3 - abs(3 - 2 * row) - abs(3 - 2 * col)
        return (100 if move.src is None else 0) + 10 * move.size + centrality

    def _ordered_moves(self, moves, preferred=None):
        """Return moves in a pruning-friendly but still fully legal order."""
        return sorted(moves,
                      key=lambda move: self._move_order_value(move, preferred),
                      reverse=True)

    def _terminal_score(self, winner, depth):
        """Score a known winner, preferring faster wins and slower losses."""
        if winner == self.root_player:
            return WIN_SCORE + depth
        if winner == self.root_opponent:
            return -WIN_SCORE - depth
        return 0

    def _minimax(self, board, reserves, player_to_move, depth, alpha, beta, ply):
        """Return the alpha-beta minimax value of one search node."""
        self._check_time()

        over, winner, _ = check_endgame(board, reserves, player_to_move, ply)
        if over:
            return self._terminal_score(winner, depth)
        if depth == 0:
            return evaluate_position(board, reserves,
                                     self.root_player, self.root_opponent)

        moves = get_valid_moves(board, reserves, player_to_move)
        next_player = 3 - player_to_move

        # With placements-only experimental rules, a player can have to pass.
        if not moves:
            return self._minimax(board, reserves, next_player, depth - 1,
                                 alpha, beta, ply + 1)

        if player_to_move == self.root_player:
            value = -float("inf")
            for move in self._ordered_moves(moves):
                self._check_time()
                child_board, child_reserves = copy_state(board, reserves)
                execute_move(child_board, child_reserves, player_to_move, move)
                move_winner = check_winner(child_board, player_to_move)
                if move_winner:
                    child_value = self._terminal_score(move_winner, depth - 1)
                else:
                    child_value = self._minimax(
                        child_board, child_reserves, next_player, depth - 1,
                        alpha, beta, ply + 1)
                value = max(value, child_value)
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value

        value = float("inf")
        for move in self._ordered_moves(moves):
            self._check_time()
            child_board, child_reserves = copy_state(board, reserves)
            execute_move(child_board, child_reserves, player_to_move, move)
            move_winner = check_winner(child_board, player_to_move)
            if move_winner:
                child_value = self._terminal_score(move_winner, depth - 1)
            else:
                child_value = self._minimax(
                    child_board, child_reserves, next_player, depth - 1,
                    alpha, beta, ply + 1)
            value = min(value, child_value)
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value

    def _search_depth(self, board, reserves, moves, depth, ply, preferred):
        """Complete one root search and return its best score and move."""
        best_score = -float("inf")
        best_move = moves[0]
        alpha = -float("inf")
        beta = float("inf")

        for move in self._ordered_moves(moves, preferred):
            self._check_time()
            child_board, child_reserves = copy_state(board, reserves)
            execute_move(child_board, child_reserves, self.root_player, move)

            # check_winner implements the uncovering rule: the opponent is
            # checked before the player who just moved.
            winner = check_winner(child_board, self.root_player)
            if winner:
                score = self._terminal_score(winner, depth - 1)
            else:
                score = self._minimax(
                    child_board, child_reserves, self.root_opponent,
                    depth - 1, alpha, beta, ply + 1)
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
        return best_score, best_move

    def step(self, board, reserves, player, opponent):
        """Return a legal move found by the last fully completed search depth."""
        start = time.perf_counter()
        self.deadline = start + max(0.01, STEP_TIME_LIMIT - TIME_MARGIN)
        self.root_player = player
        self.root_opponent = opponent

        moves = get_valid_moves(board, reserves, player)
        # The referee calls step only when a legal move exists. Keeping the
        # first generated move guarantees a legal fallback if time expires.
        best_move = moves[0]
        ply = 2 * self.turn_number + player - 1
        self.turn_number += 1

        depth = 1
        while True:
            try:
                _, completed_move = self._search_depth(
                    board, reserves, moves, depth, ply, best_move)
                best_move = completed_move
                depth += 1
            except _SearchTimeout:
                break
        return best_move