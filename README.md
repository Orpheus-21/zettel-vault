# zettel-vault

A Claude Code skill that turns saved web articles into Zettelkasten notes.

## What it does

You save articles as Markdown files in the `Clippings/` folder of a vault. The skill reads each article. It writes one permanent note for each claim in the article. Then it moves the article to `Sources/`.

Each permanent note holds one claim, in short plain sentences. The note links to its source article. The skill adds no opinion and no outside facts. The article is the only source.

A Python script, `vault.py`, writes the notes, moves the files, and keeps a search index. The script enforces the note format.

## Requirements

- Claude Code.
- Python 3. The script was tested with Python 3.14.
- A folder of Markdown articles. A web clipper such as Obsidian Web Clipper makes these files.

The skill works on a plain folder. It does not need Obsidian. The notes use `[[wikilinks]]`, so Obsidian or any similar program shows the links.

## Install

1. Clone the repo.

```bash
git clone https://github.com/Orpheus-21/zettel-vault.git
```

2. Copy the skill folder to your Claude Code skills folder.

```bash
cp -r zettel-vault/skills/zettel-vault ~/.claude/skills/
```

3. Copy the command file. This step is optional. It adds the `/vault` command.

```bash
mkdir -p ~/.claude/commands
cp zettel-vault/commands/vault.md ~/.claude/commands/
```

4. Set the vault path. Choose any folder. Add this line to your shell profile.

```bash
export VAULT=~/path/to/your/vault
```

If you do not set `VAULT`, Claude asks you for the path.

## Usage

1. Create the vault folders. Run `/vault init` in Claude Code. The command creates `Clippings/`, `Sources/`, and `Permanent/`.
2. Save articles as `.md` files in `Clippings/`.
3. Run `/vault` in Claude Code. Claude processes every article in `Clippings/`.

You can also ask in plain words: "process my clippings".

An article of 40000 characters or more is not read until you give an order. This protects you from a large token cost.

The script has these commands. Claude runs them. You can run them too.

| Command | Action |
|---|---|
| `init` | Create the folders. |
| `inbox` | List the articles in `Clippings/` with their size. |
| `write <title> <article>` | Write one claim note. The note text comes from stdin. |
| `archive <article>` | Check the notes, remove images, and move the article to `Sources/`. |
| `index` | Rebuild the search index. |
| `related <note>` | List the notes that share key words with a note. |
| `find <term>...` | List the notes that hold every term. |
| `topics` | List the topic entry notes. |
| `topic <name>` | Create or extend a topic entry note. Note names come from stdin. |
| `check` | Report format errors and broken links. |

Example:

```bash
VAULT=~/path/to/your/vault python3 ~/.claude/skills/zettel-vault/scripts/vault.py check
```

## Configuration

| Setting | Default | Meaning |
|---|---|---|
| `VAULT` | none | The path of the vault folder. The script stops with an error if it is not set. |
| `LONG` in `vault.py` | `40000` | The article size in characters at which Claude asks before it reads. |
| `TOPIC` in `vault.py` | `Topic - ` | The file name prefix of topic entry notes. |

## Optional: the ste-replies skill

The skill works alone. Notes are clearer when you also install the [ste-replies](https://github.com/Orpheus-21/ste-replies) skill. It makes Claude write in ASD-STE100 Simplified Technical English: short sentences, one fact in each sentence, and one name for each thing. If the skill is installed, `zettel-vault` loads it before it writes notes. The style never changes what the article says.

## How it works

The vault has three folders and one hidden folder:

- `Clippings/` holds new articles.
- `Permanent/` holds claim notes and topic entry notes.
- `Sources/` holds processed articles. Each one gets the properties `type: source` and `processed: <date>`.
- `.vault/index.tsv` holds the search index.

A claim note has a title that states one claim, plain text, and a last line `Source: [[article name]]`. It has no heading, no tag, no table, no image, and no link to another claim note.

The `write` command refuses a note that breaks the format. It then updates the index. The index keeps 12 key words for each note. The command prints the notes that share two or more key words with the new note. Claude uses this list to avoid a duplicate note and to find notes for a topic.

A topic entry note is named `Topic - <name>`. It holds only lines of the form `- [[claim note]]`. Claude creates one when 8 or more claim notes hold the same term.

The rules in `SKILL.md` bind Claude. Claude gives no opinion. Claude uses only the article as a source. Claude never follows a link in an article. Claude records every claim, with the article's hedges and numbers.

## License

GPL version 3 or any later version. See the `LICENSE` file.
