"""Deterministic mathematical verification with SymPy.

SECURITY: sympy.parse_expr ultimately calls eval(). Input here comes from OCR / LLM output
and teacher edits, so it is treated as untrusted: we whitelist characters and identifiers
before parsing and cap the length. Never pass raw text to parse_expr elsewhere.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

MAX_LEN = 200
_ALLOWED_CHARS = re.compile(r"^[0-9a-zA-Z+\-*/^().=,\s]*$")
_ALLOWED_FUNCS = {"sqrt", "pi", "abs", "Abs"}
_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)


class UnsafeOrInvalidExpression(ValueError):
    pass


@dataclass(frozen=True)
class Parsed:
    kind: str  # "expr" | "eq"
    expr: sp.Expr | None = None
    lhs: sp.Expr | None = None
    rhs: sp.Expr | None = None

    @property
    def free_symbols(self) -> set[sp.Symbol]:
        if self.kind == "expr":
            return set(self.expr.free_symbols)
        return set(self.lhs.free_symbols) | set(self.rhs.free_symbols)

    def as_zero_form(self) -> sp.Expr:
        """lhs - rhs for equations, expr for expressions."""
        return sp.expand(self.lhs - self.rhs) if self.kind == "eq" else self.expr


def normalize_text(text: str) -> str:
    t = text.strip()
    t = (
        t.replace("×", "*").replace("·", "*").replace("÷", "/").replace("−", "-")
        .replace("–", "-").replace("²", "^2").replace("³", "^3").replace("√", "sqrt")
        .replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    )
    # Turkish decimal comma: 3,5 -> 3.5 (only between digits)
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    # mixed-number like "2 1/3" is ambiguous; leave as is (teacher can correct)
    return t


def _check_safe(t: str) -> None:
    if len(t) > MAX_LEN:
        raise UnsafeOrInvalidExpression("too_long")
    if not _ALLOWED_CHARS.match(t):
        raise UnsafeOrInvalidExpression("disallowed_characters")
    if "__" in t:
        raise UnsafeOrInvalidExpression("disallowed_token")
    for word in re.findall(r"[A-Za-z]{2,}", t):
        if word not in _ALLOWED_FUNCS:
            # multi-letter tokens other than whitelisted funcs: treat as implicit product of
            # single-letter symbols ONLY if <= 3 letters (e.g. "ab"), otherwise reject.
            if len(word) > 3:
                raise UnsafeOrInvalidExpression(f"disallowed_identifier:{word}")


def _parse_side(t: str) -> sp.Expr:
    local = {c: sp.Symbol(c) for c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"}
    local.update({"sqrt": sp.sqrt, "pi": sp.pi, "abs": sp.Abs, "Abs": sp.Abs})
    try:
        return parse_expr(t, local_dict=local, global_dict={"Integer": sp.Integer, "Float": sp.Float,
                          "Rational": sp.Rational, "Symbol": sp.Symbol, "Mul": sp.Mul, "Add": sp.Add,
                          "Pow": sp.Pow}, transformations=_TRANSFORMS, evaluate=False)
    except Exception as exc:  # noqa: BLE001 - sympy raises many types
        raise UnsafeOrInvalidExpression(f"parse_error:{type(exc).__name__}") from exc


def parse_math(text: str | None) -> Parsed:
    if text is None or not text.strip():
        raise UnsafeOrInvalidExpression("empty")
    t = normalize_text(text)
    _check_safe(t)
    if t.count("=") > 1:
        raise UnsafeOrInvalidExpression("multiple_equals")
    if "=" in t:
        left, right = t.split("=")
        if not left.strip() or not right.strip():
            raise UnsafeOrInvalidExpression("empty_side")
        return Parsed(kind="eq", lhs=_parse_side(left), rhs=_parse_side(right))
    return Parsed(kind="expr", expr=_parse_side(t))


def try_parse(text: str | None) -> Parsed | None:
    try:
        return parse_math(text)
    except UnsafeOrInvalidExpression:
        return None


def _is_zero(e: sp.Expr) -> bool:
    try:
        return sp.simplify(e) == 0
    except Exception:  # noqa: BLE001
        return False


def solution_set(p: Parsed) -> set | None:
    """Solution set of a single-variable equation, None if not determinable."""
    if p.kind != "eq":
        return None
    syms = sorted(p.free_symbols, key=str)
    if len(syms) != 1:
        return None
    try:
        sols = sp.solve(sp.Eq(p.lhs, p.rhs), syms[0])
        return {sp.nsimplify(s) for s in sols}
    except Exception:  # noqa: BLE001
        return None


def equivalent(a: Parsed, b: Parsed) -> bool | None:
    """True/False if decidable, None if undecidable (e.g. mixed kinds, multivariable eq)."""
    if a.kind == "expr" and b.kind == "expr":
        return _is_zero(a.expr - b.expr)
    if a.kind == "eq" and b.kind == "eq":
        sa, sb = solution_set(a), solution_set(b)
        if sa is not None and sb is not None:
            return sa == sb
        # multivariable: equivalent if zero-forms are proportional by a nonzero constant
        za, zb = a.as_zero_form(), b.as_zero_form()
        if _is_zero(zb):
            return _is_zero(za)
        ratio = sp.simplify(za / zb)
        return bool(ratio.is_number and ratio != 0)
    return None


def answers_match(student: str | None, correct: str, answer_type: str) -> bool | None:
    """Compare a final answer to the key. None = cannot decide automatically."""
    if student is None or not student.strip():
        return False
    if answer_type == "multiple_choice":
        return student.strip().upper()[:1] == correct.strip().upper()[:1]
    if answer_type == "open_ended":
        return None
    sp_, cp = try_parse(student), try_parse(correct)
    if sp_ is None or cp is None:
        return None
    # "x = 5" vs "5": compare value of single-symbol equation to number
    if sp_.kind == "eq" and cp.kind == "expr":
        sol = solution_set(sp_)
        return None if sol is None else sol == {sp.nsimplify(cp.expr)}
    if sp_.kind == "expr" and cp.kind == "eq":
        sol = solution_set(cp)
        return None if sol is None else sol == {sp.nsimplify(sp_.expr)}
    return equivalent(sp_, cp)


def additive_terms(e: sp.Expr) -> list[sp.Expr]:
    return list(sp.Add.make_args(sp.expand(e)))
