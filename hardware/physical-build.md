# Physical Build

This is the working plan for the first real Mirrage smart mirror.

The goal is not to buy the most impressive parts. The goal is to build a mirror
that can run every day, be repaired, stay cool, and look clean enough to belong
in a home.

## Recommended First Build

| Area | Recommendation |
| --- | --- |
| Display | 27 inch IPS monitor with VESA mount |
| Mirror material | Two-way acrylic sample first, then acrylic or glass based on brightness test |
| Compute | Intel N100 mini PC for the first wall-mounted version |
| Audio | Small wired USB or 3.5mm speakers hidden in the frame |
| Microphone | USB conference microphone for first reliable testing |
| Network | Ethernet if possible, Wi-Fi only if cable routing is not practical |
| Deployment | Linux, Docker production Compose, systemd startup, Mirror Mode enabled |
| Frame | Deep wooden shadow-box style with removable back panel |

## Product Shape

```text
wall
  -> frame with ventilation and service access
    -> two-way mirror material
    -> display
    -> mini PC
    -> microphone
    -> small speakers
    -> cable exit and strain relief
```

The mirror should not be a sealed box. The back should be removable, the mini PC
should be accessible, and power bricks should not be trapped inside a hot
enclosure.

## Preferred System Architecture

```text
Physical Mirror
  -> display, microphone, speakers, mini PC
  -> runs Mirrage frontend in kiosk mode
  -> runs backend with Docker production Compose
  -> connects over LAN to optional future AI server
  -> connects over LAN to Home Assistant when configured
```

The first physical mirror should not require a workstation GPU. Heavy local AI,
vision, and agent workloads can move to a future AI server while the mirror
stays a clean home appliance.

## Build Priorities

1. Screen visibility through mirror material.
2. Safe power and cable routing.
3. Heat management.
4. Reliable software startup after reboot.
5. Microphone and wake engine testing.
6. Clean frame finish.
7. Easy maintenance.

## Current Limits

- Real two-way mirror visibility must be tested with the chosen display.
- Real wake-word reliability requires microphone and model testing.
- Thermal behavior depends on the final frame depth and ventilation.
- Local AI performance depends on the compute device.
- Final cost depends on region, availability, and whether used parts are chosen.
- Wall mounting depends on wall type and total weight.

Do not permanently mount the mirror until the display, mirror material, heat,
audio, microphone, and software restart tests pass.
