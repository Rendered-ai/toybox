# Sun

Directional sunlight, positioned by **time-of-day and compass
direction** rather than a location in metres. Use for outdoor scenes
where you want to control the sun angle, cast-shadow direction, and
warmth.

For interior lighting, use `Light` (spot / point) instead.

## Inputs

| Input | What it controls |
|---|---|
| **Elevation (deg)** | How high the sun sits above the horizon. `0` = sunrise/sunset (long shadows across the ground), `45` = mid-morning, `90` = high noon (near-vertical shadows). |
| **Azimuth (deg)** | Compass direction the sun shines *from*. `0` = north, `90` = east, `180` = south, `270` = west. Shadows fall the opposite direction. |
| **Strength (W/m²)** | Sun intensity. Bright noon = ~3–5; overcast = ~0.5–1; golden hour = ~1–2; moonlight fake = ~0.05. |
| **Color** | Sunlight tint. `[1, 1, 1]` is neutral. `[1.0, 0.7, 0.4]` = warm sunrise; `[1.0, 0.5, 0.3]` = warm sunset; `[0.85, 0.9, 1.0]` = cool overcast. |
| **Angular Size (deg)** | How "sharp" shadow edges are. `0.53` = real sun (crisp shadows); `2–5` = hazy day (softer edges); `15–25` = heavy overcast (nearly no shadow definition). |

## Output

| Output | Where it goes |
|---|---|
| **Light** | Wire into a scene's `Lights` input. |

## Common configurations

**Randomized time-of-day** — Elevation fed by `Random Uniform` [15, 75]
(skip the horizon), Azimuth fed by `Random Uniform` [80, 280] (skip
looking north), Color and Angular Size each fed by a `Random Choice`
that pairs matching values (warm+crisp for morning, cool+soft for
overcast).

**Fixed noon** — Elevation 80, Azimuth 180, Strength 4, default Color.
Sun straight up with sharp shadows.

## Notes

- Only one Sun per scene makes physical sense; the pipeline accepts
  more but the render just adds them together.
- Location has no effect — sunlight is directional, so only orientation
  matters.
