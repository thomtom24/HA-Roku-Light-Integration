# Roku Ambient Light (Home Assistant custom integration)

Monitors the active Roku app via local Roku ECP (port 8060), downloads its icon, finds a prominent saturated colour, and sets a selected colour-capable light. Each Roku gets its own integration instance and enable switch.

## Install

1. Copy `custom_components/roku_ambient_light` into your Home Assistant `/config/custom_components/` directory.
2. Restart Home Assistant.
3. Settings → Devices & services → Add integration → **Roku Ambient Light**.
4. Enter your Roku IP address (prefer a DHCP reservation) and select your Bloom or other RGB light.
5. Under the integration's **Configure** menu, set brightness, transition, light, and what happens when Roku returns Home.
6. Repeat for additional Roku boxes.

The switch `switch.<roku>_ambient_lighting` turns the behaviour on/off. A 5-second poll is used. App icon colours are cached until Home Assistant restarts. When the Roku returns Home, you can turn it off (default), restore the previous light state, or leave it unchanged.

## Requirements and limitations

- Roku and Home Assistant must be on networks permitting HTTP to TCP port 8060; Roku's mobile-app/control setting must allow local access.
- The target light must support RGB/HS/XY colours. The integration does not control an app's on-screen video colours.
- Some Roku apps do not expose usable icon artwork. Errors are logged and the light is left unchanged.
- The enable switch restores its previous state after Home Assistant restarts, if a prior state is available.
- If another automation changes the light while Roku is active, the integration may restore the older state when Roku returns Home.
- Only configure one Roku for each light unless you intentionally accept conflicting control.
- Third-party, community custom component; not an official Roku or Home Assistant integration.

## v1.1 changes

- Default home-screen action is **off**.
- Detect common Roku home/screen-saver names as idle.
- Restore the enable switch state on restart.
- Turning the enable switch off leaves the current light state untouched.

**Important:** This is a prototype custom integration and has not yet been tested against a physical Roku or Hue Bloom. Verify Roku ECP availability on port 8060 and review Home Assistant logs after installation.

## v1.2: Optional white light on pause

In **Configure** for each Roku, enable **Set light to white when playback is paused**. The option is off by default. When paused, the light changes to white at the configured brightness; when playback resumes, it returns to the active app's icon colour. Returning to Roku Home turns the light off by default.

For the most reliable pause detection, select the matching Roku `media_player` entity (from Home Assistant's built-in Roku integration) in the optional field. If no entity is selected, this custom integration attempts Roku's `/query/media-player` endpoint; not all Roku apps expose pause status through that endpoint. Pause detection depends on the Roku app reporting its state.

## v1.2 changes

- App opening always turns the configured light on, even if it was previously off.
- Optional per-Roku **Set light to white while paused** setting (off by default). Uses Roku ECP `/query/media-player` playback state. When playback resumes, restores the app icon colour.
- Returning to the Roku Home screen turns the light off by default, including from paused playback.
- Playback-state support depends on the Roku app; if no state is exposed, normal app colour remains. White uses the configured brightness and transition.
