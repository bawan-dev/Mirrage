# Hardware Build Plan

These are the first hardware notes for Mirrage. Nothing here is final yet.

The main thing I need to avoid is buying parts too early. The software can already run, but the mirror build depends on a few real-world tests: brightness, mirror material, heat, frame depth, and cable routing.

## First Prototype

The first version should be simple:

1. Run Mirrage on a normal screen.
2. Put mirror material in front of it.
3. Check if the dashboard is bright enough.
4. Check if the text is still readable.
5. Decide if the display size feels right.

I do not need a perfect wall mount for the first test. I need proof that the screen/mirror combo works.

## Display

Best first move: use a monitor I already have.

That keeps the cost low and lets me test the mirror effect before choosing a thinner display.

Possible display paths:

- Existing monitor: easiest for testing, probably too thick for the final build.
- Portable monitor: thinner and cleaner, but smaller.
- Laptop panel with controller board: thin, but more wiring and more things that can go wrong.
- Small TV: good size, but the frame may get bulky fast.

For now, the existing monitor path makes the most sense.

## Mirror Material

Need to test this before making any final frame.

Options:

- Acrylic two-way mirror: light and easier to work with, but scratches easier.
- Glass two-way mirror: better final look, but heavier and less forgiving.
- Mirror film: cheap for experiments, but it can look bad if applied poorly.

First test should use acrylic or film. If the project gets to a cleaner wall version, glass might be worth it.

## Computer

The computer just needs to run the dashboard and backend at first.

Possible choices:

- Mini PC: best long-term option if I want local AI later.
- Raspberry Pi: small and low power, but weak for local AI.
- Old laptop or desktop: good for testing, not clean for the final mirror.

For now, the right answer is to use whatever already runs the app reliably. Local AI should not decide the hardware yet.

## Audio

Voice is not built yet, so I do not need hidden microphones or speakers right now.

First audio setup can be basic:

- USB mic or small USB mic array
- monitor speakers or a small external speaker
- external cables while testing

Later, the frame can hide the mic and speaker, but that should happen after voice actually works.

## Power And Heat

Things to watch:

- Do not seal power bricks inside the frame.
- Leave airflow behind the screen.
- Check heat after the dashboard runs for a while.
- Plan a cable exit before building anything permanent.
- Do not make the frame so thin that cables get crushed.

## Main Risks

- The mirror material could make the screen too dim.
- The frame could end up too thick.
- Heat could build up behind the mirror.
- A hidden microphone might sound bad.
- Glass could make the final build heavier than expected.

## Current Plan

Start with a software-first hardware test:

- existing screen
- cheap mirror material test
- no permanent frame yet
- external mic/speaker later
- final parts only after brightness and size feel right
