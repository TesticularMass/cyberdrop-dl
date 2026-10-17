<div align="center">

# `cyberdrop-dl`

_Bulk asynchronous downloader for multiple file hosts_

[![License](https://img.shields.io/github/license/TesticularMass/cyberdrop-dl)](LICENSE)
[![linting - Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/TesticularMass/cyberdrop-dl/actions/workflows/ruff.yaml)
[![tests](https://github.com/TesticularMass/cyberdrop-dl/actions/workflows/ci.yaml/badge.svg?event=push)](https://github.com/TesticularMass/cyberdrop-dl/actions/workflows/ci.yaml)

![Cyberdrop-DL TUI Preview](docs/assets/cyberdrop-dl_tui_preview.png)

</div>

This repository is a fork of [Cyberdrop-DL/cyberdrop-dl](https://github.com/Cyberdrop-DL/cyberdrop-dl),
with additional fixes and optional Playwright browser support for handling site challenges.
Use the source installation below to run this fork. The `cyberdrop-dl-patched` package on PyPI and
upstream release installers distribute the upstream project.

## Getting Started

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then clone and run this repository:

```shell
git clone https://github.com/TesticularMass/cyberdrop-dl.git
cd cyberdrop-dl
uv sync --locked --all-extras
uv run cyberdrop-dl
```

The project requires Python 3.12 or newer; the checkout selects Python 3.13 through `.python-version`.
`uv` can install the required Python version automatically.

In the interactive interface, choose **Edit URLs** to add download links, then choose **Download**.
You can also put one URL per line in `URLs.txt` and download directly:

```shell
uv run cyberdrop-dl download --input-file URLs.txt
```

View available commands and download options with:

```shell
uv run cyberdrop-dl --help
uv run cyberdrop-dl download --help
```

See the [configuration guide](docs/reference/config/README.md) and
[application data locations](docs/getting-started/README.md#appdata-and-configuration) for settings,
download history, and logs.

## Optional Playwright Browser Support

Install Chromium for Playwright:

```shell
uv run python -m playwright install chromium
```

Enable browser support in your YAML configuration:

```yaml
network:
  playwright: true
  playwright_visible: false
```

Set `playwright_visible: true` to show the browser window. Both options default to `false`.
Browser support can help with site challenges, but does not guarantee that every challenge will clear.
To use a configuration file in the current directory:

```shell
uv run cyberdrop-dl --config-file config.yaml
```

## Documentation

- [Documentation contents](docs/SUMMARY.md)
- [Supported sites](docs/reference/supported-websites.md)
- [Command-line arguments](docs/reference/cli-arguments.md)
- [Frequently asked questions](docs/frequently-asked-questions.md)
- [Changelog](CHANGELOG.md)
- [Upstream wiki](https://script-ware.gitbook.io/cyberdrop-dl)

## Development and Contributing

The source installation above includes the development dependencies. Install the hooks and run the tests with:

```shell
uv run prek install
uv run pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for code style, crawler development, and upstream contribution guidance.
Report problems specific to this fork in [this repository's issue tracker](https://github.com/TesticularMass/cyberdrop-dl/issues).

## License

[GNU General Public License v3.0](LICENSE).
