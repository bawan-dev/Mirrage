# Assembly Guide

This is the practical order for building Mirrage v1.

## Steps

1. Choose the display.
2. Run Mirrage on the display without mirror material.
3. Test display brightness and viewing angles.
4. Place a mirror material sample over the display.
5. Test visibility in daytime and nighttime room light.
6. Choose the compute device.
7. Install the operating system.
8. Install Docker and clone Mirrage.
9. Configure `.env`.
10. Start production Compose.
11. Enable Mirror Mode.
12. Enable systemd startup.
13. Open the frontend in kiosk mode.
14. Test backend health and frontend health.
15. Test audio output.
16. Test microphone input.
17. Test wake engine status.
18. Test manual wake detection.
19. Test Smart Home status if Home Assistant will be used.
20. Run a 1 hour heat test with the display on.
21. Run a 4 hour heat test before final mounting.
22. Measure final display, cable, ventilation, and service access dimensions.
23. Design the frame around the measured parts.
24. Build the frame.
25. Mount the display.
26. Mount the compute device with airflow and access.
27. Mount speakers.
28. Mount microphone in a testable position.
29. Route cables with strain relief and service loops.
30. Attach mirror material without pressure points.
31. Run final software checks.
32. Complete final heat check.
33. Wall mount using hardware rated for the total weight and wall type.
34. Confirm cable exit and power access.
35. Complete final safety check.

## First Boot Checklist

```text
1. Install OS.
2. Install Docker.
3. Clone Mirrage.
4. Configure .env.
5. Start production compose.
6. Enable systemd service.
7. Open frontend in kiosk mode.
8. Verify /api/health/full.
9. Test wake engine status.
10. Test Smart Home status.
11. Reboot and confirm Mirrage returns automatically.
```

## Safety Notes

- Do not modify mains wiring.
- Use certified power supplies.
- Do not overload extension leads.
- Keep ventilation clear.
- Keep power bricks accessible.
- Use proper wall fixings for the wall type and total weight.
- Ask a qualified professional for electrical or mounting work if unsure.
