# ADR 0006 — Deterministic calculations

Status: accepted

Context: A model that computes returns cannot be tested cheaply and can invent numbers.

Decision: NumPy and pandas implement the formulas. Models may only restate the results.

Alternatives: Ask the model to calculate, then check it.

Consequences: Unit tests cover the math without an API key. The narrative cannot add a fact that the engine did not emit.
