#!/usr/bin/env python3
"""Mechanical steps for the zettel-vault skill. Claude writes the notes; this script enforces the format."""
import os, re, sys, datetime, inspect, collections
from pathlib import Path

VAULT = Path(os.environ.get("VAULT") or sys.exit("ERROR: set the VAULT environment variable to the vault folder")).expanduser()
INBOX, SOURCES, PERM = VAULT / "Clippings", VAULT / "Sources", VAULT / "Permanent"
BAD_TITLE = re.compile(r'[\\/:*?"<>|#^\[\]]')
INDEX = VAULT / ".vault" / "index.tsv"  # hidden: keeps Permanent/ clean and out of Obsidian
STOP = set("""according article author authors reported reports states about above after again also another because been before being between both could does during each from have having here into just like many more most much must only other over said same says some such than that their them then there these they this those through under very want were what when where which while will with would your""".split())
TOPIC = "Topic - "  # file name prefix of entry notes
LONG = 40000  # characters; above this Claude must ask the user first


def die(msg):
    sys.exit(f"ERROR: {msg}")


def init():
    for d in (INBOX, SOURCES, PERM):
        d.mkdir(parents=True, exist_ok=True)
    print(f"READY {VAULT}: Clippings/ Sources/ Permanent/")


def inbox():
    files = sorted(INBOX.glob("*.md")) if INBOX.is_dir() else []
    if not files:
        print("EMPTY")
    for f in files:
        n = len(f.read_text(encoding="utf-8"))
        print(f"{n}\t{'ASK-USER (long)' if n >= LONG else 'ok'}\t{f.name}")


def body_problems(text):
    p = []
    if text.lstrip().startswith("---"):
        p.append("frontmatter")
    if re.search(r"!\[", text):
        p.append("image")
    if re.search(r"^\s*#{1,6}\s", text, re.M):
        p.append("heading")
    if re.search(r"(?<!\S)#[A-Za-z]", text):
        p.append("tag")
    if re.search(r"^\s*\|", text, re.M):
        p.append("table")
    if re.search(r"\[\[", text):
        p.append("wikilink in body (the script adds the one source link)")
    return p


def good_title(t):
    return bool(t) and not BAD_TITLE.search(t) and not t.endswith((".", " ")) and len(t) <= 120


def terms(f):
    """Top 12 key words of a claim note. Title words count 3 times."""
    text = f.read_text(encoding="utf-8").rstrip().rsplit("\n", 1)[0]  # drop the Source line
    c = collections.Counter(w for w in re.findall(r"[a-z][a-z-]{3,}", (f.stem + " ") .lower() * 3 + text.lower()) if w not in STOP and w != "source")
    return [w for w, _ in c.most_common(12)]


def load_index():
    """Return {name: (mtime, source, terms)}. Re-read new or changed claim notes, drop deleted ones."""
    old = {}
    if INDEX.exists():
        for l in INDEX.read_text(encoding="utf-8").splitlines():
            n, m, src, t = l.split("\t")
            old[n] = (m, src, t.split(","))
    new = {}
    for f in PERM.glob("*.md"):
        if is_entry(f):
            continue
        m = str(f.stat().st_mtime_ns)
        if f.stem in old and old[f.stem][0] == m:
            new[f.stem] = old[f.stem]
        else:
            last = f.read_text(encoding="utf-8").rstrip().rsplit("[[", 1)[-1].rstrip("]")
            new[f.stem] = (m, last, terms(f))
    INDEX.parent.mkdir(exist_ok=True)
    INDEX.write_text("".join(f"{n}\t{m}\t{src}\t{','.join(t)}\n" for n, (m, src, t) in sorted(new.items())), encoding="utf-8")
    return new


def related(name, limit=8):
    """Rank other claim notes by key words shared with this note."""
    idx = load_index()
    if name not in idx:
        die(f"no claim note: {name}")
    mine = set(idx[name][2])
    rows = sorted(((len(mine & set(t)), n, sorted(mine & set(t))) for n, (_, _, t) in idx.items() if n != name and len(mine & set(t)) >= 2),
                  key=lambda r: (-r[0], r[1]))
    for k, n, sh in rows[:limit]:
        print(f"RELATED {k}\t{n}\t[{', '.join(sh)}]")
    print(f"{len(rows)} related note(s)" + (f", top {limit} shown" if len(rows) > limit else "") if rows else "NO RELATED NOTES")


def index():
    print(f"INDEX {len(load_index())} claim note(s) -> .vault/index.tsv")


def write(title, stem):
    title = title.strip()
    if not good_title(title) or title.startswith(TOPIC):
        die(f'bad claim title. No \\ / : * ? " < > | # ^ [ ], no final period, 120 characters max, no \'Topic - \' prefix: {title!r}')
    if not (INBOX / f"{stem}.md").exists():
        die(f"no article Clippings/{stem}.md")
    body = sys.stdin.read().strip()
    if not body:
        die("empty content on stdin")
    bad = body_problems(body)
    if bad:
        die("content has: " + ", ".join(bad))
    PERM.mkdir(parents=True, exist_ok=True)
    path = PERM / f"{title}.md"
    try:
        with open(path, "x", encoding="utf-8") as fh:
            fh.write(f"{body}\n\nSource: [[{stem}]]\n")
    except FileExistsError:
        die(f"note exists, choose a distinct claim title: {path.name}")
    print(f"WROTE {path.name}")
    related(title)


def split_fm(text):
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    return (m.group(1), text[m.end():]) if m else (None, text)


def strip_images(text):
    text = re.sub(r"!\[\[[^\]]*\]\]", "", text)
    return re.sub(r"!\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1), text)


def archive(name):
    stem = name[:-3] if name.endswith(".md") else name
    src, dst = INBOX / f"{stem}.md", SOURCES / f"{stem}.md"
    if not src.exists():
        die(f"no article Clippings/{stem}.md")
    if dst.exists():
        die(f"Sources/{stem}.md exists. Nothing moved.")
    link = f"[[{stem}]]"
    notes = [f for f in sorted(PERM.glob("*.md")) if link in f.read_text(encoding="utf-8")]
    if not notes:
        die("no permanent note links to this article. Nothing moved.")
    for f in notes:
        t = f.read_text(encoding="utf-8").rstrip()
        bad = body_problems(t.rsplit("\n", 1)[0])
        if bad or t.count("[[") != 1 or not t.endswith(f"Source: {link}"):
            die(f"{f.name} breaks the format ({', '.join(bad) or 'link line'}). Nothing moved.")
    fm, rest = split_fm(strip_images(src.read_text(encoding="utf-8")))
    add = [] if fm and re.search(r"^type:", fm, re.M) else ["type: source"]
    add.append(f"processed: {datetime.date.today()}")
    fm = "\n".join(([fm] if fm else [f'title: "{stem}"']) + add)
    SOURCES.mkdir(parents=True, exist_ok=True)
    dst.write_text(f"---\n{fm}\n---\n{rest}", encoding="utf-8")
    src.unlink()
    print(f"ARCHIVED {stem} -> Sources/ ({len(notes)} permanent notes)")


def is_entry(f):
    return f.name.startswith(TOPIC)


def find(*terms):
    """List notes whose name or text holds every term. Entry notes are marked E."""
    t = [x.lower() for x in terms]
    hits = [f for f in sorted(PERM.glob("*.md"))
            if all(x in (f.stem + " " + f.read_text(encoding="utf-8")).lower() for x in t)]
    for f in hits[:30]:
        print(("E " if is_entry(f) else "C ") + f.stem)
    print(f"{len(hits)} match(es)" + (", first 30 shown" if len(hits) > 30 else ""))


def topics():
    es = [f for f in sorted(PERM.glob("*.md")) if is_entry(f)]
    for f in es:
        print(f"{f.read_text(encoding='utf-8').count('[[')}\t{f.stem}")
    print("NONE" if not es else f"{len(es)} entry note(s)")


def topic(name):
    """Create or extend 'Topic - <name>'. Stdin: one note name per line. Entry notes list links only."""
    name = name.strip()
    if not good_title(name):
        die("bad topic name (same character rules as a claim title)")
    names = [l.strip() for l in sys.stdin if l.strip()]
    missing = [n for n in names if not (PERM / f"{n}.md").exists()]
    if missing or not names:
        die("no such note: " + "; ".join(missing) if missing else "no note names on stdin")
    path = PERM / f"{TOPIC}{name}.md"
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    have = set(re.findall(r"\[\[(.+?)\]\]", old))
    add = [n for n in dict.fromkeys(names) if n not in have and f"{n}.md" != path.name]
    path.write_text(old + "".join(f"- [[{n}]]\n" for n in add), encoding="utf-8")
    print(f"TOPIC {name}: +{len(add)} (total {len(have) + len(add)})")


def check():
    bad, n = [], 0
    for f in sorted(PERM.glob("*.md")):
        n += 1
        lines = f.read_text(encoding="utf-8").rstrip().split("\n")
        if is_entry(f):
            for l in lines:
                m = re.fullmatch(r"- \[\[(.+)\]\]", l)
                if not m or not (PERM / f"{m.group(1)}.md").exists():
                    bad.append(f"{f.name}: bad line {l!r}")
            continue
        m = re.fullmatch(r"Source: \[\[(.+)\]\]", lines[-1])
        p = body_problems("\n".join(lines[:-1])) + ([] if m else ["source line"])
        if m and not (SOURCES / f"{m.group(1)}.md").exists() and not (INBOX / f"{m.group(1)}.md").exists():
            p.append("source note missing")
        if p:
            bad.append(f"{f.name}: {', '.join(p)}")
    print("\n".join(bad) if bad else f"OK {n} note(s)")


CMDS = dict(init=init, inbox=inbox, write=write, archive=archive, index=index, related=related, find=find, topics=topics, topic=topic, check=check)
if __name__ == "__main__":
    c, a = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    try:
        inspect.signature(CMDS[c]).bind(*a)
    except (KeyError, TypeError):
        sys.exit("usage: vault.py init | inbox | write <title> <article> (stdin) | archive <article> | index | related <note> | find <term>... | topics | topic <name> (note names on stdin) | check")
    CMDS[c](*a)
