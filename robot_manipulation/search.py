"""Bounded bidirectional RRT-Connect with caller-owned collision checks.

Reference: Kuffner and LaValle, ICRA 2000, DOI 10.1109/ROBOT.2000.844730.
"""
import numpy as np


def rrt_connect(start, goal, limits, edge_free, rng, max_iterations=180, step=.25):
    start, goal = np.asarray(start), np.asarray(goal)
    stats = {'iterations': 0, 'edge_checks': 0, 'nodes': 2}

    def free(a, b):
        stats['edge_checks'] += 1
        return edge_free(a, b)

    if not free(start, start) or not free(goal, goal):
        return None, stats
    if free(start, goal):
        return [start.copy(), goal.copy()], stats
    trees = [([start.copy()], [-1]), ([goal.copy()], [-1])]
    swapped = False

    def extend(tree, target):
        nodes, parents = tree
        index = int(np.argmin(np.linalg.norm(np.asarray(nodes) - target, axis=1)))
        delta = target - nodes[index]
        length = np.linalg.norm(delta)
        if length < 1e-9:
            return index, True
        point = nodes[index] + delta * min(1., step / length)
        if not free(nodes[index], point):
            return None, False
        parents.append(index)
        nodes.append(point)
        stats['nodes'] += 1
        return len(nodes) - 1, length <= step

    def trace(tree, index):
        path = []
        while index != -1:
            path.append(tree[0][index])
            index = tree[1][index]
        return path[::-1]

    for iteration in range(max_iterations):
        stats['iterations'] = iteration + 1
        sample = trees[1][0][0] if rng.random() < .15 else rng.uniform(limits[:, 0], limits[:, 1])
        index, _ = extend(trees[0], sample)
        if index is not None:
            target = trees[0][0][index]
            # Bounded connect, even for unusual caller limits.
            for _ in range(100):
                other, reached = extend(trees[1], target)
                if other is None:
                    break
                if reached:
                    left, right = trace(trees[0], index), trace(trees[1], other)
                    path = left + right[-2::-1]
                    if swapped:
                        path.reverse()
                    # Greedy shortcuts are checked with the same collision oracle.
                    result = [path[0]]
                    cursor = 0
                    while cursor < len(path) - 1:
                        next_index = len(path) - 1
                        while next_index > cursor + 1 and not free(path[cursor], path[next_index]):
                            next_index -= 1
                        result.append(path[next_index])
                        cursor = next_index
                    return result, stats
        trees.reverse()
        swapped = not swapped
    return None, stats
