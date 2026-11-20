"""Compare our source against another codebase: share of 10-token runs that also occur there.

  python tools/provenance_check.py OTHER_DIR [OUR_DIR]

A clean-room rewrite scores near 0 %; copied-and-renamed code scores high even after renaming,
because identifiers are normalised away (every name becomes ID, every literal LIT).
"""
import io
import keyword
import pathlib
import sys
import tokenize


def norm_tokens(src):
    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING):
                continue
            if t.type == tokenize.NAME:
                out.append(t.string if keyword.iskeyword(t.string) else "ID")
            elif t.type in (tokenize.STRING, tokenize.NUMBER):
                out.append("LIT")
            else:
                out.append(t.string)
    except (tokenize.TokenError, IndentationError):
        pass
    return out


def shingles(toks, n=int(__import__("os").environ.get("RUN", "25"))):
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def main(other, ours):
    theirs = set()
    for p in pathlib.Path(other).rglob("*.py"):
        theirs |= shingles(norm_tokens(p.read_text(encoding="utf-8", errors="ignore")))
    worst = 0.0
    for p in sorted(pathlib.Path(ours).rglob("*.py")):
        mine = shingles(norm_tokens(p.read_text(encoding="utf-8")))
        if not mine:
            continue
        share = len(mine & theirs) / len(mine)
        worst = max(worst, share)
        print(f"{share * 100:5.1f}%  {p}")
    print(f"highest: {worst * 100:.1f}%")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "core")
