# Read the form

Photograph an FAA Service Difficulty Report. Get back what it actually says, and
every other aircraft it has happened to.

Built for the [GLM-5.3 Flash Lightning Hackathon](https://cerebralvalley.ai/e/glm-5-3-flash-lightning-hackathon),
28 August to 1 September 2026.

## The problem

When a mechanic in America finds something wrong with an aircraft, it gets filed
with the FAA as a Service Difficulty Report. All of it is public. None of it is
readable.

The form has ten boxes. Nine of them are codes:

| Box | On the form | What it means |
|---|---|---|
| (a) Operator Designator | `CALA` | Continental Airlines Inc |
| (b) Operator Type | `A` | Airline |
| (c) JASC/ATA Code | `2530` | Buffet and galleys |
| (d) Stage of Operation | `IN` | On the ground, in maintenance |
| (e) How Discovered | `V` | Visual. Someone looked at it |
| (f) Nature of Condition | `B` | Smoke, fumes, odour or sparks |
| (g) Precautionary Procedures | `K` | None |
| (h) FAA Region | `GL` | Great Lakes |
| (i) District Office | `33` | not in any FAA table |
| (j) Flight Number | blank | not filed |

Read as English: a Continental aircraft had smoke or sparks from the galley,
found by eye during ground maintenance, no emergency procedure triggered.

Nothing there is secret. It is simply filed in a language nobody hands you a
dictionary for.

## What this does

Point a camera at the form. GLM-5.3-Flash reads the boxes. The FAA's own lookup
tables decode them. Then the corpus of 1,757,828 reports answers the question the
form cannot: how often does this happen, and to whom.

## The division of labour, which is the whole design

**The model reads. The tables decide.**

GLM-5.3-Flash is given exactly one job: transcribe the characters in each box. It
is never asked what a code means.

This is not caution for its own sake. Asked to interpret, any model will produce a
plausible expansion for a code it has never seen, and it will not tell you it
guessed. `ZONE 400` will come back as something that sounds right. On a public
safety record that is not a small error. It is a fabricated fact wearing the
formatting of a real one, and a reporter cannot see the difference.

So decoding is deterministic, from the FAA's published tables, and anything the
tables do not cover stays on screen as the raw code, in red, labelled as
undecoded. Field (i) in the example above does exactly that.

## Running it

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then put a real key in it, from https://z.ai
./.venv/bin/python app.py   # http://127.0.0.1:8210
```

There is a demo button on the page, so you do not need to find a form first.

## Built by GLM, not only with it

The later stages of this project were written by GLM-5.3-Flash itself, driving
Claude Code through Z.ai's Anthropic-compatible endpoint:

```bash
./run-with-glm.sh
```

See [BUILDLOG.md](BUILDLOG.md) for every step, including the parts that went wrong.

## Sources

- Reports and FAA code tables: [aircraftdefects.com](https://aircraftdefects.com)
- Raw data: `external.apic4e.faa.gov/sdrs/retrieve/SDR-YYYY.csv`, 1995 onward
- FAA lookup tables: `sdrs.faa.gov/Documents/SDRS Look-Up Tables.zip`
- Operator names: FAA Air Carrier/Operator cross-reference (Dec 2006, host retired)
  merged with the current list of certificated 121 and 135 operators

## What it cannot tell you

Not an accident database and not a safety ranking. A high count can mean an old
fleet, a large airline, or a maintenance department that inspects harder than its
competitors. Nothing is divided by fleet size or flying hours, because the FAA
file contains neither.

MIT.
