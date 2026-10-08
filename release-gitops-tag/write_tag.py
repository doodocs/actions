"""write_tag.py FILE YAML_PATH OLD NEW
Replace OLD with NEW on the single line that holds YAML_PATH in a block-style YAML file.
The path is resolved by walking indentation, so formatting, quotes and comments stay untouched.
Exits non-zero if the path cannot be resolved unambiguously."""
import re, sys

path, ypath, old, new = sys.argv[1:5]
seg_re = re.compile(r"\.([A-Za-z0-9_-]+)((?:\[\d+\])*)")
if not ypath.startswith(".") or seg_re.sub("", ypath) != "":
    sys.exit("unsupported YAML_PATH %r" % ypath)
segments = []
for key, idx in seg_re.findall(ypath):
    segments.append(("key", key))
    for n in re.findall(r"\[(\d+)\]", idx):
        segments.append(("index", int(n)))

with open(path, newline="") as f:
    lines = f.readlines()

def indent(s):
    return len(s) - len(s.lstrip(" "))

def meaningful(s):
    t = s.strip()
    return bool(t) and not t.startswith("#")

def block_after(i, base_indent):
    """[start, end) of lines strictly inside the block that follows line i (indent > base_indent)."""
    j = i + 1
    while j < len(lines) and (not meaningful(lines[j]) or indent(lines[j]) > base_indent):
        j += 1
    return i + 1, j

start, end = 0, len(lines)
item_line = None
last_line = None
for kind, val in segments:
    if kind == "key":
        key_pat = re.compile(r"^(\s*)(-\s+)?%s:(\s|$)" % re.escape(val))
        hits = []
        if item_line is None:
            level = None
            for i in range(start, end):
                if not meaningful(lines[i]):
                    continue
                if level is None:
                    level = indent(lines[i])
                m = key_pat.match(lines[i])
                if m and indent(lines[i]) == level and not m.group(2):
                    hits.append((i, level))
        else:
            # keys of a list item: the inline key on the dash line, then keys at that same column
            col = None
            for i in range(start, end):
                if not meaningful(lines[i]):
                    continue
                m = key_pat.match(lines[i])
                if i == item_line:
                    col = indent(lines[i]) + 2
                    if m and m.group(2):
                        hits.append((i, col))
                elif indent(lines[i]) == col and m and not m.group(2):
                    hits.append((i, col))
        if len(hits) != 1:
            sys.exit("key %r: expected exactly one match in lines %d-%d of %s, found %d" % (val, start + 1, end, path, len(hits)))
        key_line, key_col = hits[0]
        start, end = block_after(key_line, key_col)
        item_line = None
        last_line = key_line
    else:
        items = [i for i in range(start, end) if meaningful(lines[i]) and lines[i].lstrip().startswith("- ")]
        if items:
            top = min(indent(lines[i]) for i in items)
            items = [i for i in items if indent(lines[i]) == top]
        if val >= len(items):
            sys.exit("index %d out of range (%d items) at %s" % (val, len(items), ypath))
        item_line = items[val]
        nxt = items[val + 1] if val + 1 < len(items) else end
        start, end = item_line, nxt
        last_line = None

if last_line is None:
    sys.exit("YAML_PATH must end with a key")
key = segments[-1][1]
text = lines[last_line]
val_pat = re.compile(r'^(\s*(?:-\s+)?%s:\s*)(["\']?)%s(\2)(\s*(?:#.*)?)\r?\n?$' % (re.escape(key), re.escape(old)))
if not val_pat.match(text):
    sys.exit("line %d of %s is %r, expected '%s: %s'" % (last_line + 1, path, text.rstrip(), key, old))
lines[last_line] = text.replace(old, new, 1)
with open(path, "w", newline="") as f:
    f.writelines(lines)
print("replaced on line %d: %s" % (last_line + 1, lines[last_line].strip()))
