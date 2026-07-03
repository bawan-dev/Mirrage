# Hardware Build Plan

Mirrage is now planned as a real wall-mounted appliance, not a temporary desk
demo.

The first build should stay practical: prove the display/mirror combination,
keep heat under control, run the software reliably, and avoid permanent choices
until the physical tests pass.

## Recommended V1 Direction

| Area | Direction |
| --- | --- |
| Display | 27 inch IPS monitor with VESA mount |
| Mirror material | Two-way acrylic sample first; final acrylic or glass after visibility test |
| Compute | Intel N100 mini PC |
| Audio | Small wired USB or 3.5mm speakers |
| Microphone | USB conference microphone or USB mic array |
| Frame | Deep wooden shadow-box frame with removable back |
| Deployment | Linux, Docker production Compose, systemd, Mirror Mode |

## Build Manual

Start here:

- [Physical build overview](physical-build.md)
- [Display selection](display-selection.md)
- [Mirror material](mirror-glass.md)
- [Compute options](compute-options.md)
- [Audio](audio.md)
- [Microphones](microphones.md)
- [Thermal design](thermal-design.md)
- [Cable routing](cable-routing.md)
- [Frame design](frame-design.md)
- [Maintenance](maintenance.md)
- [Shopping list](shopping-list.md)
- [Cost estimate](cost-estimate.md)
- [Assembly guide](assembly-guide.md)
- [Testing checklist](testing-checklist.md)

## Current Build Order

1. Test Mirrage on a normal display.
2. Test mirror material samples over that display.
3. Choose the display size.
4. Choose compute hardware.
5. Run the production software stack on the target compute device.
6. Test audio and microphone placement.
7. Test heat for several hours.
8. Design the frame around measured parts.
9. Build the frame with service access and ventilation.
10. Mount only after final safety and software checks pass.

## Main Risks

- mirror material makes the display too dim
- frame becomes too thick or too hot
- microphone placement performs badly
- power bricks become inaccessible
- wall mounting is underestimated
- real costs differ from planning ranges

These risks should be tested before buying final-size mirror material or
building the permanent frame.
