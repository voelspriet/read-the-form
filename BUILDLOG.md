# Build log

Every step, in order, including the wrong turns. Written as it happened.

---

## Step 0. Where the idea came from

Not from the hackathon. From a stale number.

While checking a public tool of mine, aircraftdefects.com, against its own API, I
found the page saying **170,201 reports** while the API said **1,541,548**. The
literal was left over from an earlier build, when the database really did hold
three years. It had been wrong for months, in eleven places, on a site whose whole
argument is that public records should be legible.

Fixing that meant reading the FAA's raw form, which is nine boxes of codes. That
is where the tool came from: if I need a lookup table open in another window to
read a public safety record, so does everybody else.

**Lesson kept:** the fix was not to type the correct number in. It was to stop
typing numbers. The page now asks the database its own size on every load.

---

## Step 1. Check the model can actually be run, before designing for it

GLM-5.3-Flash weights went up on Hugging Face under MIT on 27 August.

```
zai-org/GLM-5.3-Flash     321,323,031,390 params, FP8, 62 weight files
smallest 4-bit MLX build  178 GB
M4 Pro                     48 GB RAM, 187 GB free disk
M2 Max                     96 GB RAM
```

It does not fit on either machine. Mixture of experts, 320B total with 18B active,
which helps speed and not memory: every weight still has to be resident.

So: API, not local. Four minutes of arithmetic saved a day of downloading.

---

## Step 2. Get the API contract right before writing a line

```
POST https://api.z.ai/api/paas/v4/chat/completions
Authorization: Bearer <key>
model: glm-5.3-flash
```

OpenAI-compatible. Images go in as content blocks:
`{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}`

Z.ai also runs an **Anthropic-compatible** endpoint at
`https://api.z.ai/api/anthropic`, which lets Claude Code drive GLM. That became
step 6.

---

## Step 3. Decide what the model is allowed to do

This is the only design decision that matters.

The tempting version: hand the model the photograph and ask it to explain the
report. It would work, it would demo beautifully, and it would be unusable for
journalism, because the model will expand a code it has never seen into something
plausible and will not flag it.

So the prompt forbids interpretation:

> Transcribe ONLY what is written in each box. Do NOT expand, translate, interpret
> or guess the meaning of any code. If a box is empty or unreadable, return null.

Meaning comes from the FAA's own tables, applied in `decode()`. A code that is not
in them renders as the raw code in red, labelled undecoded.

**The model reads. The tables decide.**

---

## Step 4. Do not rebuild the data layer

aircraftdefects.com already holds the FAA lookup tables and 1,757,828 reports
behind a public API. The reader fetches `/api/glossary` for the code tables and
`/api/search` for comparison reports.

Verified before wiring anything:

```
/api/search?jasc=2530             4,403 reports
/api/search?nature=B             53,260
/api/search?jasc=2530&nature=B    3,622
```

---

## Step 5. First working version

`app.py`, 174 lines. Three endpoints: `/api/read`, `/api/similar`, `/api/health`.
One page, no framework, no build step.

The page shows the form twice, side by side: **As filed** and **What it says**.
The gap between the two columns is the entire argument.

---

## Step 6. Hand the build to GLM itself

From here, Claude Code drives GLM-5.3-Flash rather than Claude:

```bash
./run-with-glm.sh
```

which sets `ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic` and points every
model tier at `glm-5.3-flash`. Same agent, same tools, different brain.

The launcher refuses to start without a real key, and prints a warning about
running it in a separate tab: exporting those variables into a session on a Claude
subscription silently moves the work onto a metered API.

---

## Things that went wrong

**A `return` alone on its line.** Rewriting a renderer on the parent project, I
left `return` at the end of a line with the template literal beginning on the
next. JavaScript's automatic semicolon insertion made it return `undefined`, and
the tab bar rendered zero tabs. `node --check` passed. The page returned 200.
Every API was fine. Only driving it in a real browser caught it.

**`.format()` on a tuple.** A measured sentence was meant to be substituted into a
glossary term. I applied `.format()` to the tuple containing the string rather
than the string, and my own `except Exception: pass` swallowed the error, so the
API served the literal text `OPERATOR_GAP_SENTENCE`. The blanket except is now a
logged warning.

**Clamping a date range in the wrong direction.** Selecting a year set the end
date to 31 December unconditionally, so "2026" captioned itself as running to 31
December over a count that stopped in August. Fixing it naively then produced "1
Dec 2026 to 20 Aug 2026", a range running backwards, for any period entirely in
the future. It now clamps only where the period and the file overlap.

**Assuming where the gap was.** I predicted a 2006-era operator list would be
blind to new airlines. Measured: for 2025 it already named 98.5% of reports. The
hole was at the other end. For 1999 it named 82%, leaving 6,841 reports with a
code and no name, the largest being TWA, which was gone before the codebook was
printed.

---

## Still open

- The key. Everything above the API line needs one, and it is the one step a human
  has to do.
- Field (i), District Office, resolves for 323 offices and not for historic ones
  such as `GL33`. It stays as the raw code, which is the honest outcome.
