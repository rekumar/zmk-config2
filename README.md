# zmk-config

Personal [ZMK](https://zmk.dev) configuration.

## Keyboards

| Keyboard | Board | Shields | Keymap |
| --- | --- | --- | --- |
| REKDactyl | `nice_nano` | `rekdactyl_left` / `rekdactyl_right` | [boards/shields/rekdactyl/rekdactyl.keymap](boards/shields/rekdactyl/rekdactyl.keymap) |
| REKDactyl2 | `nice_nano` | `rekdactyl2_left` / `rekdactyl2_right` | [boards/shields/rekdactyl2/rekdactyl2.keymap](boards/shields/rekdactyl2/rekdactyl2.keymap) |
| Corne | `nice_nano` | `corne_left` / `corne_right` | [config/corne.keymap](config/corne.keymap) |
| beekeeb Toucan2 | `seeeduino_xiao_ble` | `toucan_left` / `toucan_right` | [config/toucan.keymap](config/toucan.keymap) |

Builds are selected in [build.yaml](build.yaml); firmware is produced by the GitHub
Actions workflow and downloaded from the run's artifacts.

## Toucan2

The [beekeeb Toucan2](https://beekeeb.com/introducing-toucan2/) is a wireless split
42-key column-staggered keyboard with a nice!view display on the left half and an
Azoteq TPS43 trackpad on the right half. Board support is ported from
[beekeeb/zmk-keyboard-toucan2](https://github.com/beekeeb/zmk-keyboard-toucan2).

The keymap is the Corne keymap ported over unchanged — the Toucan2 has the same
3x6 + 3-thumb matrix, so every layer maps 1:1, including the `&none` outer pinky
columns. Toucan2-specific additions:

- **MOUSE layer (7)** — held automatically while a finger rests on the trackpad, so
  the thumb keys become left / right / middle click. Everything else is `&trans`.
- **Scrolling** — the trackpad scrolls instead of moving the pointer while LOWER or
  RAISE is held (`scroller` node in [boards/shields/toucan/toucan.dtsi](boards/shields/toucan/toucan.dtsi)).
- **`&studio_unlock`** on the SYS layer (SYS + `X` position), since the left half is
  built with [ZMK Studio](https://zmk.dev/docs/features/studio) enabled.
- **Trackpad gestures** — pinch-to-zoom and three-finger swipes are mapped to macOS
  shortcuts. Set `TOUCAN_WIN_MODE` in `toucan.dtsi` for the Windows equivalents.

Other things worth knowing:

- Trackpad tuning (sensitivity, scroll angle, invert) lives in the `tps43_trackpad`
  node in [boards/shields/toucan/toucan_right.overlay](boards/shields/toucan/toucan_right.overlay).
- Per-half settings (sleep timeouts, display style) are in
  [toucan_left.conf](boards/shields/toucan/toucan_left.conf) and
  [toucan_right.conf](boards/shields/toucan/toucan_right.conf); shared settings such as
  the keyboard name are in [config/toucan.conf](config/toucan.conf).
- ZMK and the module dependencies are pinned to `v0.3` in
  [config/west.yml](config/west.yml), matching the versions the Toucan2 trackpad and
  display code are built against.

Local build:

```sh
west build -b seeeduino_xiao_ble -- \
  -DSHIELD="toucan_left rgbled_adapter nice_view_gem" \
  -DZMK_CONFIG="$(pwd)/config" -DCONFIG_ZMK_STUDIO=y
west build -b seeeduino_xiao_ble -- \
  -DSHIELD="toucan_right rgbled_adapter" -DZMK_CONFIG="$(pwd)/config"
```

## Credits

- `boards/shields/toucan` and `boards/shields/nice_view_gem` are taken from
  [beekeeb/zmk-keyboard-toucan2](https://github.com/beekeeb/zmk-keyboard-toucan2) (MIT).
- `nice_view_gem` is itself modified from
  [M165437/nice-view-gem](https://github.com/M165437/nice-view-gem) (MIT).
- The embedded QuinqueFive font is by GGBotNet, licensed under the SIL Open Font
  License 1.1 — see [QuinqueFive_License.txt](QuinqueFive_License.txt).
- The trackpad driver is based on
  [geeksville/zmk_driver_azoteq](https://github.com/geeksville/zmk_driver_azoteq).
