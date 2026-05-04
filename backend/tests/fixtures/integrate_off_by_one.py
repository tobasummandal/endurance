"""Slide 5 example: trapezoidal integrator with an off-by-one bug.

The loop starts at i=1 instead of i=0, dropping the first interval.
The result is silently wrong but plausible.
"""


def integrate(f_values, dx):
    """Trapezoidal rule on a precomputed array of f(x) samples."""
    n = len(f_values)
    total = 0.0
    for i in range(1, n - 1):          # BUG: should be range(0, n - 1)
        total += 0.5 * (f_values[i] + f_values[i + 1]) * dx
    return total
