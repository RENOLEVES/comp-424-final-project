"""Throw-away symmetry sanity check for an experiments/<variant>.py evaluate_position.

Usage: python experiments/sanity_check.py experiments/v1a_cell1.py
Builds a position via helpers.new_game + a few random_move/execute_move calls, then checks
evaluate_position(board, reserves, 1, 2) == -evaluate_position(board, reserves, 2, 1).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

import helpers
from runners import load_agent_class


def main():
    path = sys.argv[1]
    cls = load_agent_class(path)
    evaluate_position = sys.modules[cls.__module__].evaluate_position
    rng = np.random.default_rng(7)
    board, reserves, obstacle, removed = helpers.new_game(42)
    player = 1
    for _ in range(6):
        move = helpers.random_move(board, reserves, player, rng=rng)
        if move is None:
            player = 3 - player
            continue
        helpers.execute_move(board, reserves, player, move)
        player = 3 - player
    v12 = evaluate_position(board, reserves, 1, 2)
    v21 = evaluate_position(board, reserves, 2, 1)
    print(f"evaluate_position(., ., 1, 2) = {v12}")
    print(f"evaluate_position(., ., 2, 1) = {v21}")
    if v12 == -v21:
        print("SYMMETRIC: OK")
    else:
        print("SYMMETRIC: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
