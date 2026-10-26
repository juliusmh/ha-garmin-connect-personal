# Garmin Connect Personal API for Home Assistant

A Home Assistant integration that pulls data from Garmin Connect
using Garmin's official [Personal API](https://developer.garmin.com/gc-developer-program/personal/personal-api).
Add several people, each with their own API key, and every person becomes a
_device_ in Home Assistant.

Requires Home Assistant 2026.6.4 or newer.

## Installation

### HACS

1. In HACS, open the menu (⋮) in the top right and choose **Custom repositories**.
2. Add `https://github.com/juliusmh/ha-garmin-connect-personal` with the type **Integration**.
3. Search for **Garmin Connect Personal** in HACS and download it.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/garmin_connect_personal` into the `custom_components`
   folder of your Home Assistant configuration directory.
2. Restart Home Assistant.

## Configuration

Each person needs their own Personal API key.

1. Sign in to Garmin Connect as that person and open
   [Personal API Tokens](https://connect.garmin.com/app/settings/personalApiToken).
2. Create a key and copy it.
3. In Home Assistant, go to **Settings → Devices & services → Add integration**
   and search for **Garmin Connect Personal**.
4. Paste the API key.

Repeat these steps for every person you want to add. Adding the same Garmin
account twice is rejected.

The device is named after the Garmin display name, which is often a random ID.
Rename the device to the person's name, and Home Assistant offers to rename
the entities with it.

If Garmin rejects a key later, for example because it was deleted, Home Assistant
shows a **Re-authenticate** notification. Enter a new key for the same person
there.

## Entities

Each person gets the following entities, where `<person>` is the device name.
Data is refreshed every 15 minutes.

| Entity | Description |
| --- | --- |
| `binary_sensor.<person>_is_awake` | On unless the current time lies within the person's most recent sleep. Attributes: `sleep_start`, `sleep_end`. |
| `sensor.<person>_sleep_score` | Overall sleep score (0–100). Attributes: `qualifier` (e.g. `GOOD`), `calendar_date`. |
| `sensor.<person>_sleep_duration` | Total sleep time, excluding naps. |
| `sensor.<person>_deep_sleep` | Time in deep sleep. |
| `sensor.<person>_light_sleep` | Time in light sleep. |
| `sensor.<person>_rem_sleep` | Time in REM sleep. |
| `sensor.<person>_awake_time_during_sleep` | Time awake during the sleep window. |
| `sensor.<person>_times_awake_during_sleep` | Number of times the person woke up. |
| `sensor.<person>_average_heart_rate_during_sleep` | Average heart rate (bpm). |
| `sensor.<person>_average_respiration_during_sleep` | Average respiration (breaths per minute). |
| `sensor.<person>_average_stress_during_sleep` | Average stress level. |
| `sensor.<person>_last_sync` | When the person's device last synced with Garmin Connect (diagnostic). |

Durations are shown in hours. You can change the unit per entity in its settings.

### Good to know

- **Sleep data appears after a sync.** Garmin files a night under the date the
  person woke up. Until last night has synced, the sensors show the night before.
  Check **Last sync** to see how current the data is.
- **`is_awake` is not live.** Garmin usually receives a night's sleep only after
  the watch syncs in the morning, so while the person is asleep the sensor still
  reports the previous night and stays on.

## Troubleshooting

To see every request the integration makes, enable debug logging:

```yaml
logger:
  logs:
    custom_components.garmin_connect_personal: debug
    garmin_personal_api: info
```

Bearer tokens are cached per person in
`.storage/garmin_connect_personal/` inside your configuration directory. The
cached token is deleted when you remove that person.

## Development

Development needs [Docker](https://www.docker.com/) and [uv](https://docs.astral.sh/uv/).

| Command | Description |
| --- | --- |
| `make dev` | Starts Home Assistant at http://localhost:8123 in Docker, with the integration loaded and `config/` as the configuration directory. Stop it with Ctrl+C. |
| `make lint` | Formats and lints the code with ruff. |
| `make test` | Runs the tests with [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component). |

Home Assistant doesn't reload integration code on the fly. Restart `make dev`
after changing the code. To try another Home Assistant version, run
`make dev HA_VERSION=<version>`.

To call the Personal API directly, for example to inspect a response, use the
library's CLI:

```shell
export GARMIN_PERSONAL_API_KEY='…'
uvx --from garmin-connect-personal-api-python gc-personal sleep
```

### Tests and editor support

`make test` installs Home Assistant, the Garmin library and the test tools into
`.venv` on its first run, as defined in `pyproject.toml`. Point your editor at
`.venv/bin/python` for autocompletion and type checking. To create the
environment without running the tests, run `uv sync`.

The tests mock the Garmin API, so they don't need an API key or network access.

### Releasing

Push a tag to create a release:

```shell
git tag v0.2.0
git push origin v0.2.0
```

The release workflow runs the lint and tests, then publishes a GitHub release
with `garmin_connect_personal.zip`, which HACS installs. The version in the
zip's `manifest.json` is taken from the tag, so `manifest.json` doesn't need to
be changed for a release. Tags with a suffix, such as `v0.2.0-beta.1`, become
pre-releases.

## Credits

Built on Garmin's [connect-personal-api-python](https://github.com/garmin/connect-personal-api-python)
library and started from ludeeus'
[integration_blueprint](https://github.com/ludeeus/integration_blueprint).

This project is not affiliated with or endorsed by Garmin.

## License

MIT. See [LICENSE](LICENSE).
