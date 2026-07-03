# Wiring Notes

The wiring plan stays intentionally simple for Mirrage v1.

## First Rule

Do not modify mains wiring.

Use normal certified power supplies, plugs, USB, HDMI/DisplayPort, Ethernet, and
safe cable management. If electrical work is needed, use a qualified
professional.

## Target Layout

```text
wall outlet
  -> surge protector / power strip
    -> display power
    -> mini PC power
    -> speaker power if needed

mini PC
  -> HDMI / DisplayPort to display
  -> USB microphone
  -> USB or 3.5mm speakers
  -> Ethernet where possible
```

## Cable Requirements

- display power
- mini PC power
- video cable
- USB microphone
- speaker cable
- Ethernet cable
- optional USB hub
- temporary keyboard/mouse during setup

## Routing Rules

- keep power bricks accessible
- leave service loops
- add strain relief at the frame exit
- avoid tight HDMI/DisplayPort bends
- keep cables away from hot surfaces
- do not crush cables between frame and wall
- label cables before final mounting

More detail is in [cable-routing.md](cable-routing.md).
