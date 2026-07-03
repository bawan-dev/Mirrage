# Thermal Design

Heat is one of the easiest ways to ruin a smart mirror build.

The display, compute device, speakers, power adapters, and frame depth all affect
temperature. Do not build Mirrage as a sealed box.

## Heat Sources

- display backlight and panel electronics
- mini PC or Raspberry Pi
- power bricks
- speakers or amplifier
- any USB hub
- sunlight or room heat near the wall

## Recommendations

- Leave ventilation at the bottom and top of the frame.
- Avoid sealing the back completely.
- Keep the mini PC away from the hottest part of the display if possible.
- Keep power bricks accessible and outside sealed cavities.
- Use short but not strained cables.
- Leave a small wall clearance for air movement.
- Prefer quiet passive airflow before adding fans.
- If fans are needed, use slow quiet fans and dust access.

## Vent Concept

```text
bottom frame gap
  -> cool air enters
    -> display and mini PC warm the air
      -> warm air exits through top gap
```

## Thermal Testing Checklist

Before final wall mounting:

- run Mirror Mode for 1 hour
- check display back temperature
- check mini PC temperature
- check power brick temperature
- run for 4 hours
- confirm the frame is warm but not hot
- confirm no cables are touching hot surfaces
- confirm the system does not throttle, crash, or restart
- repeat with room lights and normal ambient temperature

If the frame feels too warm after testing, increase ventilation or move heat
sources before mounting.

## What Not To Do

- do not bury power bricks inside a sealed frame
- do not block display vents
- do not press cables tightly against hot electronics
- do not assume a cool desk test means a closed wall frame is safe
- do not mount permanently before a multi-hour heat test
