#!/usr/bin/env python3
"""
parser.py  -  Table-driven LL(1) Predictive Parser
Compiler Design Assignment 01 - Part (iii)

Pipeline
    1. Scanner   : converts source text into tokens (same token classes as lexer.l)
    2. Grammar   : LL(1) grammar (no left recursion, no left factoring needed)
    3. FIRST / FOLLOW sets computed automatically
    4. LL(1) parsing table built automatically (conflicts are reported)
    5. Stack-based predictive parser with step-by-step trace
    6. Parse tree printed on success, syntax error reported on failure

Run :  python3 parser.py input.txt
"""
import re
import sys

EPS = "ε"
END = "$"

# ----------------------------------------------------------------------------
# 1. SCANNER
# ----------------------------------------------------------------------------
KEYWORDS = {"int", "float", "if", "else", "while", "print"}
TOKEN_SPEC = [
    ("COMMENT",  r"//[^\n]*|/\*.*?\*/"),
    ("SKIP",     r"[ \t\r\n]+"),
    ("FLOAT",    r"\d+\.\d+"),
    ("NUM",      r"\d+"),
    ("ID",       r"[A-Za-z_][A-Za-z_0-9]*"),
    ("STR",      r'"[^"\n]*"'),
    ("RELOP",    r"==|!=|<=|>=|<|>"),
    ("ASSIGN",   r"="),
    ("PLUS",     r"\+"),
    ("MINUS",    r"-"),
    ("MUL",      r"\*"),
    ("DIV",      r"/"),
    ("LP",       r"\("),
    ("RP",       r"\)"),
    ("LB",       r"\{"),
    ("RB",       r"\}"),
    ("SEMI",     r";"),
    ("BAD",      r"."),
]
MASTER = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC), re.S)


def scan(text):
    """Return list of (terminal, lexeme, line)."""
    tokens, line = [], 1
    for m in MASTER.finditer(text):
        kind, lex = m.lastgroup, m.group()
        if kind in ("SKIP", "COMMENT"):
            line += lex.count("\n")
            continue
        if kind == "BAD":
            raise SyntaxError(f"Lexical error at line {line}: unknown character '{lex}'")
        if kind == "ID" and lex in KEYWORDS:
            kind = lex                      # keyword token is its own terminal
        elif kind == "ID":
            kind = "id"
        elif kind in ("NUM", "FLOAT"):
            kind = "num"
        elif kind == "STR":
            kind = "str"
        elif kind == "RELOP":
            kind = "relop"
        else:
            kind = lex                      # operators / delimiters: the symbol itself
        tokens.append((kind, lex, line))
    tokens.append((END, END, line))
    return tokens


# ----------------------------------------------------------------------------
# 2. GRAMMAR (LL(1))
# ----------------------------------------------------------------------------
GRAMMAR = {
    "Program":  [["StmtList"]],
    "StmtList": [["Stmt", "StmtList"], [EPS]],
    "Stmt":     [["Decl"],
                 ["id", "=", "Expr", ";"],
                 ["if", "(", "Cond", ")", "{", "StmtList", "}", "ElsePart"],
                 ["while", "(", "Cond", ")", "{", "StmtList", "}"],
                 ["print", "Expr", ";"]],
    "Decl":     [["Type", "id", "DeclTail", ";"]],
    "Type":     [["int"], ["float"]],
    "DeclTail": [["=", "Expr"], [EPS]],
    "ElsePart": [["else", "{", "StmtList", "}"], [EPS]],
    "Cond":     [["Expr", "relop", "Expr"]],
    "Expr":     [["Term", "Expr'"]],
    "Expr'":    [["+", "Term", "Expr'"], ["-", "Term", "Expr'"], [EPS]],
    "Term":     [["Factor", "Term'"]],
    "Term'":    [["*", "Factor", "Term'"], ["/", "Factor", "Term'"], [EPS]],
    "Factor":   [["(", "Expr", ")"], ["id"], ["num"], ["str"]],
}
START = "Program"
NONTERMS = list(GRAMMAR)


def is_nt(sym):
    return sym in GRAMMAR


# ----------------------------------------------------------------------------
# 3. FIRST and FOLLOW
# ----------------------------------------------------------------------------
def compute_first():
    first = {nt: set() for nt in GRAMMAR}
    changed = True
    while changed:
        changed = False
        for nt, prods in GRAMMAR.items():
            for prod in prods:
                before = len(first[nt])
                first[nt] |= first_of_seq(prod, first)
                changed |= len(first[nt]) != before
    return first


def first_of_seq(seq, first):
    out = set()
    for sym in seq:
        if sym == EPS:
            out.add(EPS)
            return out
        if not is_nt(sym):
            out.add(sym)
            return out
        out |= first[sym] - {EPS}
        if EPS not in first[sym]:
            return out
    out.add(EPS)
    return out


def compute_follow(first):
    follow = {nt: set() for nt in GRAMMAR}
    follow[START].add(END)
    changed = True
    while changed:
        changed = False
        for nt, prods in GRAMMAR.items():
            for prod in prods:
                for i, sym in enumerate(prod):
                    if not is_nt(sym):
                        continue
                    f = first_of_seq(prod[i + 1:], first)
                    before = len(follow[sym])
                    follow[sym] |= f - {EPS}
                    if EPS in f:
                        follow[sym] |= follow[nt]
                    changed |= len(follow[sym]) != before
    return follow


# ----------------------------------------------------------------------------
# 4. PARSING TABLE
# ----------------------------------------------------------------------------
def build_table(first, follow):
    table, conflicts = {}, []
    for nt, prods in GRAMMAR.items():
        for prod in prods:
            f = first_of_seq(prod, first)
            for t in f - {EPS}:
                put(table, conflicts, nt, t, prod)
            if EPS in f:
                for t in follow[nt]:
                    put(table, conflicts, nt, t, prod)
    return table, conflicts


def put(table, conflicts, nt, t, prod):
    if (nt, t) in table and table[(nt, t)] != prod:
        conflicts.append((nt, t))
    table[(nt, t)] = prod


def show(prod):
    return " ".join(prod)


# ----------------------------------------------------------------------------
# 5. PREDICTIVE PARSER (with parse tree)
# ----------------------------------------------------------------------------
class Node:
    def __init__(self, label):
        self.label, self.kids = label, []


def parse(tokens, table, verbose=True):
    root = Node(START)
    stack = [(END, None), (START, root)]
    pos, step = 0, 1
    if verbose:
        print(f"{'Step':<5}{'Stack (top at right)':<46}{'Input':<24}Action")
        print("-" * 110)
    while stack:
        sym, node = stack[-1]
        tok, lex, line = tokens[pos]
        stk = " ".join(s for s, _ in stack)
        stk = stk if len(stk) <= 44 else "…" + stk[-43:]
        rest = " ".join(t[1] for t in tokens[pos:pos + 3])
        rest = rest + (" …" if pos + 3 < len(tokens) else "")

        if sym == END and tok == END:
            if verbose:
                print(f"{step:<5}{stk:<46}{rest:<24}ACCEPT")
            return root
        if not is_nt(sym):                         # terminal on top of the stack
            if sym == tok:
                if verbose:
                    print(f"{step:<5}{stk:<46}{rest:<24}match '{lex}'")
                node.label = f"{sym}  ({lex})" if sym in ("id", "num", "str", "relop") else sym
                stack.pop()
                pos += 1
            else:
                raise SyntaxError(f"Syntax error at line {line}: expected '{sym}' but found '{lex}'")
        else:                                      # non-terminal on top of the stack
            prod = table.get((sym, tok))
            if prod is None:
                expected = sorted(t for (n, t) in table if n == sym)
                raise SyntaxError(
                    f"Syntax error at line {line}: unexpected '{lex}' while parsing <{sym}>; "
                    f"expected one of: {', '.join(expected)}")
            if verbose:
                print(f"{step:<5}{stk:<46}{rest:<24}{sym} → {show(prod)}")
            stack.pop()
            kids = [Node(s) for s in prod]
            node.kids = kids
            for k in reversed(kids):
                if k.label != EPS:
                    stack.append((k.label, k))
        step += 1
    raise SyntaxError("Parser stack exhausted unexpectedly")


def print_tree(node, prefix="", last=True, root=True):
    if root:
        print(node.label)
    else:
        print(prefix + ("└── " if last else "├── ") + node.label)
    child_prefix = "" if root else prefix + ("    " if last else "│   ")
    for i, k in enumerate(node.kids):
        print_tree(k, child_prefix, i == len(node.kids) - 1, False)


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "input.txt"
    quiet_tree = "--no-tree" in sys.argv
    src = open(path, encoding="utf-8").read()

    print("=" * 30, "GRAMMAR (LL(1))", "=" * 30)
    for nt, prods in GRAMMAR.items():
        print(f"  {nt:<9} → " + "  |  ".join(show(p) for p in prods))

    first = compute_first()
    follow = compute_follow(first)
    print("\n" + "=" * 30, "FIRST & FOLLOW", "=" * 30)
    print(f"  {'Non-terminal':<14}{'FIRST':<48}FOLLOW")
    for nt in NONTERMS:
        print(f"  {nt:<14}{'{ ' + ', '.join(sorted(first[nt])) + ' }':<48}"
              f"{{ {', '.join(sorted(follow[nt]))} }}")

    table, conflicts = build_table(first, follow)
    print("\n" + "=" * 30, "LL(1) CHECK", "=" * 30)
    if conflicts:
        print("  Grammar is NOT LL(1). Conflicts:", conflicts)
        sys.exit(1)
    print(f"  No conflicts in the parsing table ({len(table)} entries) -> grammar is LL(1).")

    print("\n" + "=" * 30, f"PARSING: {path}", "=" * 30)
    print("Source:")
    for i, l in enumerate(src.splitlines(), 1):
        print(f"  {i:>2} | {l}")
    print()
    try:
        tokens = scan(src)
        tree = parse(tokens, table)
    except SyntaxError as e:
        print("\n" + "!" * 4, e)
        print("RESULT: PARSING FAILED")
        sys.exit(1)

    print("\nRESULT: PARSING SUCCESSFUL - input is syntactically valid.")
    if not quiet_tree:
        print("\n" + "=" * 30, "PARSE TREE", "=" * 30)
        print_tree(tree)


if __name__ == "__main__":
    main()
