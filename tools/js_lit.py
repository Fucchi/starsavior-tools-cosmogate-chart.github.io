"""Minimal parser/writer for the restricted JS object-literal syntax used in
data/characters.js (and similar files in this repo).

Supports: object literals with quoted or bare identifier keys, arrays,
double/single-quoted strings, numbers, true/false/null, and function-call
expressions like defaultAllySkill(...). Comments (// and /* */) are skipped.

Not a general JS parser -- only handles what this codebase actually emits.
"""
import re


class Call:
    """Represents a JS function-call expression, e.g. defaultAllySkill(...)."""
    __slots__ = ("name", "args")

    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"Call({self.name!r}, {self.args!r})"

    def __eq__(self, other):
        return isinstance(other, Call) and self.name == other.name and self.args == other.args


TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<linecomment>//[^\n]*)
  | (?P<blockcomment>/\*.*?\*/)
  | (?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
  | (?P<number>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
  | (?P<ident>[A-Za-z_$][A-Za-z0-9_$]*)
  | (?P<punct>[{}\[\]():,])
""", re.VERBOSE | re.DOTALL)


def tokenize(text):
    tokens = []
    pos = 0
    n = len(text)
    while pos < n:
        m = TOKEN_RE.match(text, pos)
        if not m:
            raise SyntaxError(f"Unexpected character at {pos}: {text[pos:pos+30]!r}")
        pos = m.end()
        kind = m.lastgroup
        if kind in ("ws", "linecomment", "blockcomment"):
            continue
        tokens.append((kind, m.group()))
    return tokens


def _unescape_js_string(raw):
    body = raw[1:-1]
    quote = raw[0]
    out = []
    i = 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "`": "`"}
            if nxt in mapping:
                out.append(mapping[nxt])
                i += 2
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, value):
        kind, val = self.next()
        if val != value:
            raise SyntaxError(f"Expected {value!r} but got {val!r} at token {self.i}")

    def parse_value(self):
        kind, val = self.peek()
        if kind == "punct" and val == "{":
            return self.parse_object()
        if kind == "punct" and val == "[":
            return self.parse_array()
        if kind == "string":
            self.next()
            return _unescape_js_string(val)
        if kind == "number":
            self.next()
            if "." in val or "e" in val or "E" in val:
                return float(val)
            return int(val)
        if kind == "ident":
            if val == "true":
                self.next()
                return True
            if val == "false":
                self.next()
                return False
            if val == "null" or val == "undefined":
                self.next()
                return None
            # identifier -- must be a call expression: name(args...)
            self.next()
            nk, nv = self.peek()
            if nk == "punct" and nv == "(":
                return self.parse_call(val)
            raise SyntaxError(f"Bare identifier {val!r} not supported as a value")
        raise SyntaxError(f"Unexpected token {kind!r} {val!r} at {self.i}")

    def parse_call(self, name):
        self.expect("(")
        args = []
        kind, val = self.peek()
        if not (kind == "punct" and val == ")"):
            while True:
                args.append(self.parse_value())
                kind, val = self.peek()
                if kind == "punct" and val == ",":
                    self.next()
                    kind, val = self.peek()
                    if kind == "punct" and val == ")":
                        break  # trailing comma
                    continue
                break
        self.expect(")")
        return Call(name, args)

    def parse_object(self):
        self.expect("{")
        result = {}
        kind, val = self.peek()
        if kind == "punct" and val == "}":
            self.next()
            return result
        while True:
            kkind, kval = self.next()
            if kkind == "string":
                key = _unescape_js_string(kval)
            elif kkind == "ident":
                key = kval
            elif kkind == "number":
                key = kval
            else:
                raise SyntaxError(f"Bad object key {kkind!r} {kval!r} at {self.i}")
            self.expect(":")
            value = self.parse_value()
            result[key] = value
            kind, val = self.peek()
            if kind == "punct" and val == ",":
                self.next()
                kind, val = self.peek()
                if kind == "punct" and val == "}":
                    break  # trailing comma
                continue
            break
        self.expect("}")
        return result

    def parse_array(self):
        self.expect("[")
        result = []
        kind, val = self.peek()
        if kind == "punct" and val == "]":
            self.next()
            return result
        while True:
            result.append(self.parse_value())
            kind, val = self.peek()
            if kind == "punct" and val == ",":
                self.next()
                kind, val = self.peek()
                if kind == "punct" and val == "]":
                    break
                continue
            break
        self.expect("]")
        return result


def parse(text):
    """Parse a single JS value (object/array/literal) from text."""
    p = Parser(tokenize(text))
    value = p.parse_value()
    return value


_IDENT_KEY_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def _format_number(n):
    if isinstance(n, bool):
        return "true" if n else "false"
    if isinstance(n, int):
        return str(n)
    if n == int(n):
        return str(int(n))
    s = f"{n:.10f}".rstrip("0").rstrip(".")
    return s


def _escape_js_string(s):
    out = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{out}"'


def write_value(value, quote_keys=False):
    if isinstance(value, Call):
        args = ", ".join(write_value(a) for a in value.args)
        return f"{value.name}({args})"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return _format_number(value)
    if isinstance(value, str):
        return _escape_js_string(value)
    if isinstance(value, list):
        items = ", ".join(write_value(v) for v in value)
        return f"[{items}]"
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            if quote_keys or not _IDENT_KEY_RE.match(str(k)):
                key_str = _escape_js_string(str(k))
            else:
                key_str = str(k)
            parts.append(f"{key_str}:{write_value(v)}")
        return "{" + ", ".join(parts) + "}"
    raise TypeError(f"Cannot serialize value of type {type(value)}: {value!r}")
