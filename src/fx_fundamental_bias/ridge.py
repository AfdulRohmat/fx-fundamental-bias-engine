"""Dependency-free ridge routines for the small registered research models."""

from __future__ import annotations

from collections.abc import Sequence


class SingularModelError(ValueError):
    """Raised when a registered linear system cannot be solved."""


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [[*matrix[index], vector[index]] for index in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise SingularModelError("Ridge normal equations are singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    left - factor * right
                    for left, right in zip(
                        augmented[row], augmented[column], strict=True
                    )
                ]
    return [augmented[index][-1] for index in range(size)]


def ridge_fit(
    design: Sequence[Sequence[float]],
    target: Sequence[float],
    *,
    penalty: float,
    unpenalized: frozenset[int] = frozenset(),
    nonnegative: frozenset[int] = frozenset(),
) -> tuple[float, ...]:
    if not design or len(design) != len(target):
        raise ValueError("Design and target must be non-empty and aligned")
    width = len(design[0])
    if width == 0 or any(len(row) != width for row in design):
        raise ValueError("Design matrix is ragged")
    active = set(range(width))
    while True:
        columns = sorted(active)
        gram = [[0.0 for _ in columns] for _ in columns]
        rhs = [0.0 for _ in columns]
        for row, outcome in zip(design, target, strict=True):
            for left_index, left_column in enumerate(columns):
                lhs_value = row[left_column]
                rhs[left_index] += lhs_value * outcome
                for right_index, right_column in enumerate(columns):
                    gram[left_index][right_index] += lhs_value * row[right_column]
        for index, column in enumerate(columns):
            if column not in unpenalized:
                gram[index][index] += penalty
            gram[index][index] += 1e-10
        fitted = _solve(gram, rhs)
        candidate = [0.0] * width
        for column, value in zip(columns, fitted, strict=True):
            candidate[column] = value
        violations = [
            column
            for column in sorted(nonnegative & active)
            if candidate[column] < 0
        ]
        if not violations:
            return tuple(candidate)
        active.remove(min(violations, key=lambda column: candidate[column]))


def predict(row: Sequence[float], coefficients: Sequence[float]) -> float:
    if len(row) != len(coefficients):
        raise ValueError("Prediction vector does not match coefficients")
    return sum(left * right for left, right in zip(row, coefficients, strict=True))
