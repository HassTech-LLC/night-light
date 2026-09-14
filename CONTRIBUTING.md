# Contributing to Night Light by HT

Night Light by HT is Windows-only and currently in alpha. Contributions should preserve transparent state reporting, one active warmth pipeline, and a guaranteed path back to a neutral display.

## Development setup

1. Install Python 3.11–3.14 on Windows 11.
2. Create and activate a virtual environment.
3. Run `python -m pip install -e ".[dev]"`.
4. Run `python -m pytest`.
5. Start the development build with `python main.py --background`.

Set `NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND=1` when running diagnostics that must not modify the real display. Set `NIGHT_LIGHT_BY_HT_CONFIG_DIR` to an isolated directory when testing persistence.

## Pull requests

- Keep health and sleep claims evidence-bound.
- Add tests for scheduler math, state transitions, persistence, and Windows integration fallbacks.
- Do not introduce a path that layers any HT display transform over Windows Night Light.
- Avoid committing generated executables, build folders, user settings, secrets, or machine-specific paths.
- Describe real-machine verification separately from mocked or unit-test results.

## Copyright and licensing of contributions

Night Light by HT is licensed under the GNU General Public License version 3 or
later, with the WebView2 additional permission recorded in `NOTICE`.

By submitting a contribution you agree to two things. First, you license your
contribution under the same terms as the project. Second, you assign copyright in
the contribution to HassTech, so the project can be relicensed, dual-licensed, or
offered under different terms in future without tracing every past contributor.
If you cannot assign copyright, say so in the pull request. The contribution can
still be accepted under the GPL alone, and it will be recorded so any later
relicensing effort knows to ask you first.

Do not contribute code you did not write or that carries an incompatible license.
Identify any third-party snippet and its license in the pull request.

## Reporting defects

Include Windows version, display type, HDR state, monitor count, expected state, effective state shown by the app, and exact reproduction steps. Use the security process for vulnerabilities.
