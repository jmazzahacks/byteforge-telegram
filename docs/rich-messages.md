# Rich Messages (Bot API 10.1)

`send_rich_message()` / `send_rich_message_sync()` send a **Rich Message** — Telegram's
structured format that supports headings, lists, tables, media, block quotations,
collapsible blocks, footnotes, and formulas.

You express the content as a single **extended-HTML** or **Markdown** string inside an
[`InputRichMessage`](../src/byteforge_telegram/models.py). This is *not* the same as the
classic `parse_mode="HTML"` used by `send_message` — it's a separate endpoint with a much
larger tag set.

```python
from byteforge_telegram import TelegramBotController, InputRichMessage

bot = TelegramBotController("YOUR_BOT_TOKEN")

bot.send_rich_message_sync(
    chat_id="123456789",
    rich_message=InputRichMessage(html=(
        "<h2>Daily report</h2>"
        "<ul><li>All systems green</li><li>3 deploys</li></ul>"
        "<table><tr><th>Metric</th><th>Value</th></tr>"
        "<tr><td>Uptime</td><td>99.98%</td></tr></table>"
    )),
)
```

> **Important:** the library passes your rich text through **untouched** — no HTML escaping,
> tag repair, or message splitting. You are responsible for well-formed markup and for
> escaping literal `<`, `>`, and `&` as `&lt;`, `&gt;`, `&amp;`. (This is unlike
> `send_message`, which escapes and repairs for you.)

`InputRichMessage` takes exactly one of `html` or `markdown`, plus optional `is_rtl` and
`skip_entity_detection`. Plain URLs, e-mail addresses, @mentions, #hashtags, $cashtags,
bot commands, phone numbers, and bank-card numbers are auto-detected unless you set
`skip_entity_detection=True`.

## Limits

| Limit | Value |
|---|---|
| Text length | 32,768 UTF-8 chars (incl. custom-emoji alt text and formula source) |
| Blocks | 500 (incl. nested blocks, list items, table rows, quotation/details blocks) |
| Nesting depth | 16 levels |
| Media attachments | 50 total (photos + videos + audio) |
| Table columns | 20 |

## Supported HTML tags

### Inline formatting
| Tag(s) | Meaning |
|---|---|
| `<b>`, `<strong>` | bold |
| `<i>`, `<em>` | italic |
| `<u>`, `<ins>` | underline |
| `<s>`, `<strike>`, `<del>` | strikethrough |
| `<mark>` | highlighted / marked |
| `<sub>` / `<sup>` | subscript / superscript |
| `<code>` | inline fixed-width code |
| `<tg-spoiler>` | spoiler |
| `<a href="...">` | link — supports `http(s)://`, `mailto:`, `tel:`, `tg://user?id=...` (mention), and in-document `#anchor` |
| `<a name="...">` | anchor target for in-document links |
| `<tg-reference name="...">...</tg-reference>` | footnote/reference text, linkable via `<a href="#...">` |
| `<tg-emoji emoji-id="...">👍</tg-emoji>` | custom emoji (fallback char as content) |
| `<tg-time unix="..." format="...">` | formatted date-time |
| `<tg-math>` ... `</tg-math>` | inline formula — content is **raw LaTeX** |

### Headings & structure
| Tag(s) | Meaning |
|---|---|
| `<h1>`–`<h6>` | headings (h1 largest) |
| `<p>` | paragraph |
| `<br>` | line break |
| `<hr/>` | divider |
| `<footer>` | footer text |
| `<pre>` | preformatted code block |
| `<pre><code class="language-python">` | code block with language |
| `<blockquote>` | block quotation (use `<br>` for lines, `<cite>` for author) |
| `<aside>` | pull quote (with optional `<cite>`) |
| `<details>` / `<details open>` + `<summary>` | collapsible block; body may contain rich content; `open` expands by default |
| `<tg-math-block>` ... `</tg-math-block>` | block formula — **raw LaTeX** |

### Lists
| Tag(s) | Meaning |
|---|---|
| `<ul><li>` | unordered list |
| `<ol><li>` | ordered list; `<ol>` accepts `start`, `type`, `reversed`; `<li>` accepts `value`, `type` |
| `<li><input type="checkbox" checked>` | checklist item |

### Tables
| Tag(s) | Meaning |
|---|---|
| `<table>` | table; accepts `bordered`, `striped` |
| `<caption>` | table caption |
| `<tr>`, `<th>`, `<td>` | row / header cell / cell; `<td>` accepts `colspan`, `rowspan`, `align`, `valign` |

> Table cells may contain **inline formatting only** (no nested blocks).

### Media (separate blocks only; HTTP/HTTPS URLs only)
| Tag(s) | Meaning |
|---|---|
| `<img src="...">`, `<video src="...">`, `<audio src="...">` | photo / video / audio block |
| `<figure>` + `<figcaption>` | media with a caption (caption may include `<cite>` for credit) |
| `tg-spoiler` (attribute on media inside `<figure>`) | mark the media as a spoiler |
| `<tg-map lat="..." long="..." zoom="...">` | map |
| `<tg-collage>` | collage of images/videos |
| `<tg-slideshow>` | slideshow of images/videos |

> `<tg-thinking>` exists but is only valid in `sendRichMessageDraft`, which this library
> does not yet wrap — so it is **not** usable here.

## Supported HTML entities

- All **numeric** HTML entities (e.g. `&#10;`).
- Named entities — only these: `&lt;` `&gt;` `&amp;` `&quot;` `&apos;` `&nbsp;` `&hellip;`
  `&mdash;` `&ndash;` `&lsquo;` `&rsquo;` `&ldquo;` `&rdquo;`.

## Other rules

- Only the tags listed above are supported.
- A programming language can be set only via nested `<pre><code class="language-...">`; a
  standalone `<code>` cannot specify a language.
- Images / videos / audio can be specified **only** as separate media blocks, never inline.
- Formula source (`<tg-math>`, `<tg-math-block>`) is treated as **raw LaTeX**.
- **Markdown mode** (`markdown=...`) is GitHub-Flavored-Markdown-compatible and may also
  contain the HTML tags above. Markdown is *not* parsed inside block HTML tags except
  `<details>`, `<tg-collage>`, and `<tg-slideshow>`.

---

*Compiled from the [Telegram Bot API — Rich Message Formatting Options](https://core.telegram.org/bots/api#rich-message-formatting-options)
(Bot API 10.1) as of 2026-06-28. Telegram's live documentation is the authoritative source;
this feature is new and the tag set may evolve.*
