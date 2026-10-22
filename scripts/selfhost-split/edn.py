"""Tiny EDN emitter (dict -> {:k v}, list -> [..], set -> #{..}); keys given as str are keywordised
when they look like identifiers, names stay strings only inside values flagged by sym()."""
import re

class Sym(str):
    pass

_KW = re.compile(r"^[A-Za-z_*+!?<>=/.-][A-Za-z0-9_*+!?<>=/.-]*$")

def dumps(x, indent=0, pretty=True):
    pad = "  " * indent
    if x is None:
        return "nil"
    if x is True:
        return "true"
    if x is False:
        return "false"
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, str):
        return '"' + x.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(x, (int, float)):
        return repr(x)
    if isinstance(x, dict):
        if not x:
            return "{}"
        items = []
        for k, v in x.items():
            ks = (":" + k) if isinstance(k, str) and not isinstance(k, Sym) and _KW.match(k) else dumps(k)
            items.append(ks + " " + dumps(v, indent + 1, pretty))
        if not pretty or sum(len(i) for i in items) < 100 and not any("\n" in i for i in items):
            return "{" + ", ".join(items) + "}"
        return "{" + ("\n" + pad + "  ").join([""] + items).lstrip("\n").lstrip() .join(["", ""]) if False else "{" + items[0] + "".join("\n" + pad + " " + i for i in items[1:]) + "}"
    if isinstance(x, (list, tuple)):
        if not x:
            return "[]"
        items = [dumps(v, indent + 1, pretty) for v in x]
        if not pretty or sum(len(i) for i in items) < 100 and not any("\n" in i for i in items):
            return "[" + " ".join(items) + "]"
        return "[" + items[0] + "".join("\n" + pad + " " + i for i in items[1:]) + "]"
    if isinstance(x, (set, frozenset)):
        return "#{" + " ".join(dumps(v) for v in sorted(x, key=str)) + "}"
    raise TypeError(type(x))
