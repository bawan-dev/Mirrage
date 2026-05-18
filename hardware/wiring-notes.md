# Wiring Notes

These are the first wiring notes for Mirrage. This is not final wiring. It is just the safest way to think about the first prototype.

## First Rule

Do not mess with mains wiring.

For the first build, everything should use normal plugs, normal power bricks, USB, HDMI, or USB-C. No cutting power cables, no opening power supplies, no wiring anything into the wall.

## First Prototype Layout

Basic setup:

```text
wall outlet
  -> surge protector / power strip
    -> monitor power
    -> computer power
    -> speaker power if needed

computer
  -> HDMI / USB-C video to display
  -> USB microphone
  -> speaker output
  -> network over Wi-Fi or Ethernet
```

That is enough for the first physical test.

## Cable Plan

Need to leave room for:

- display power cable
- HDMI or USB-C video cable
- computer power cable
- USB microphone cable
- speaker cable or USB speaker cable
- Ethernet cable if Wi-Fi is unreliable

The frame should not be designed until these cable paths are measured. A mirror can look thin in drawings and still be annoying once cables are behind it.

## Display Wiring

For the first version:

- connect the computer to the display like a normal monitor
- do not hide the display power brick inside a sealed frame
- make sure the screen can be turned on without taking the mirror apart

If the final version uses a laptop panel and controller board, that gets its own wiring notes later. That path has more risk.

## Computer Placement

Possible placements:

- behind the mirror if the frame has enough depth and airflow
- under/near the mirror with one cable bundle going up
- outside the frame for the first prototype

First prototype should keep the computer outside the frame. It makes testing easier and avoids heat problems early.

## Audio Wiring

Voice is not built yet, so audio wiring should stay simple:

- USB mic plugged into the computer
- small speaker plugged into audio jack or USB
- no hidden microphone until voice actually works

Mic placement will matter later. Behind mirror material might sound bad, so that needs testing before committing to a hidden mic.

## Power Notes

Things I do not want:

- power bricks trapped in a sealed frame
- cables pinched by the frame
- power strip hanging loose behind the mirror
- no way to unplug the mirror quickly

Things I do want:

- easy access to power
- enough slack to remove the mirror safely
- cable ties or clips after the layout is tested
- airflow around the screen and computer

## Later Wiring

Possible future wiring:

- LED strip for edge lighting
- temperature sensor inside the frame
- physical power button
- motion or presence sensor
- cleaner internal speaker wiring

None of that is needed for the first prototype. First goal is screen, mirror material, computer, and basic audio space.

## Current Wiring Decision

First wiring setup:

- normal monitor power
- normal computer power
- HDMI or USB-C video
- external USB mic later
- external speaker later
- no permanent wiring until the mirror material and screen size are tested
