# Cyberdrop-DL Modernization Design

## Summary

Modernize Cyberdrop-DL to run cleanly on a current CPython-only baseline with current dependency APIs while preserving the existing CLI and YAML config surface. The work should remove brittle compatibility code, refresh packaging and CI to the new support policy, and keep the downloader behavior verified by regression tests rather than assumptions.

## Goals

- Keep the existing CLI entry points and user-facing config schema stable.
- Update the codebase to work with current library releases and current supported APIs.
- Allow raising the Python minimum version if that materially simplifies the upgrade.
- Allow dropping PyPy support if that reduces compatibility burden.
- Strengthen regression coverage around the modernization hotspots.

## Non-Goals

- Do not redesign the downloader architecture.
- Do not introduce new user-facing CLI features.
- Do not rename or restructure config files in a way that changes the current user workflow.
- Do not perform unrelated refactors outside the touched modernization areas.

## Support Policy

- Target a modern CPython-only runtime baseline.
- Set `CPython 3.13+` as the supported runtime floor.
- Remove PyPy from supported runtimes, packaging expectations, and CI.
- Align local tooling, tox, and GitHub Actions to the same supported version set.

## Architecture Constraints

The top-level architecture remains unchanged:

- CLI arguments still parse through the existing argument model stack.
- YAML config still validates through the existing Pydantic-based config models.
- Manager startup still builds the same runtime graph.
- Networking still uses the existing `aiohttp` and `curl-cffi` session model.
- Crawlers still expose the same contracts and feed the same downloader/storage flow.

Modernization happens inside these boundaries. Internal APIs may be simplified, but the observable CLI and config behavior should remain equivalent.

## Workstreams

### 1. Runtime, Packaging, and Tooling Baseline

Update the project metadata and automation to reflect the modernized support policy:

- revise `pyproject.toml` runtime metadata and dependency constraints
- remove outdated interpreter compatibility accommodations
- align `tox.ini` and GitHub Actions workflows to the new supported matrix
- keep install, lint, test, and release flows coherent with the new Python floor

This workstream should make the support contract explicit in packaging and CI instead of leaving compatibility to chance.

### 2. Compatibility API Cleanup

Replace brittle or outdated implementation details with current supported APIs, especially where the code relies on:

- private dependency internals such as Pydantic sentinels
- explicit event loop plumbing that newer libraries no longer want
- compatibility imports that only exist for older interpreters
- obsolete runtime branches kept solely for dropped environments

Known hotspots already identified during exploration:

- `cyberdrop_dl/config/_common.py`
- `cyberdrop_dl/managers/client_manager.py`
- compatibility imports and typing fallbacks across crawlers and tests

The cleanup should preserve semantics while removing unnecessary legacy coupling.

### 3. Verification Hardening

Use tests to lock down the current public behavior before and during modernization:

- preserve CLI smoke coverage
- preserve startup and validation error behavior
- cover config model loading/saving behavior affected by field/default handling
- cover DNS/session bootstrap behavior affected by resolver and async client changes
- keep crawler/model regressions green on the modernized dependency stack

Where a modernization change touches behavior that is currently implicit, add narrow regression tests before changing the implementation.

### 4. Dependency Refresh

Refresh runtime and development dependencies against the new baseline, but do so deliberately rather than bumping everything blindly:

- prefer current stable releases that support the chosen Python floor
- resolve breakages by updating code to supported APIs, not by pinning old versions indefinitely
- keep optional dependency error paths explicit and actionable

The dependency refresh should follow the architecture constraints and verification guardrails above.

## Components and Data Flow

The existing data flow remains:

1. CLI arguments and YAML config load into Pydantic models.
2. The manager graph builds runtime services from those validated settings.
3. Networking sessions and resolver setup power crawlers and downloads.
4. Crawlers emit media items that the downloader, database, and storage layers consume.

Modernization should only change the implementation details within these stages. It should not change the input/output contract between them.

## Error Handling Requirements

- Preserve current startup logging behavior for successful runs, validation failures, YAML failures, and general startup exceptions.
- Preserve graceful DNS fallback behavior: prefer async resolution, fall back cleanly when async resolver setup is unavailable.
- Preserve clear actionable errors for optional dependencies such as `curl-cffi`.
- Enforce the new runtime support policy in packaging and CI rather than through confusing runtime failures.

## Testing Strategy

Run targeted tests early while modernizing the relevant areas, then finish with a broader regression pass.

Minimum targeted coverage:

- `tests/test_cli.py`
- `tests/test_dns_resolver.py`
- `tests/test_manager.py`
- config/model tests touched by the implementation
- crawler regressions impacted by dependency/API changes

Broader verification target:

- full pytest suite, except any pre-existing intentionally skipped network-sensitive tests
- lint or static checks already required by the repo

If the modernization reveals flaky or environment-coupled tests, fix or scope them explicitly rather than silently dropping coverage.

## Risks and Mitigations

- Private or deprecated APIs may have hidden behavior differences.
  Mitigation: add narrow regression tests around touched paths before refactoring them.

- Dependency upgrades may surface cross-platform issues in async networking or packaging.
  Mitigation: keep CI aligned with the new support matrix and verify session/bootstrap behavior directly.

- Raising the Python floor may accidentally leak into user-facing behavior if codepaths were implicitly relying on older compatibility helpers.
  Mitigation: preserve CLI/config behavior with targeted tests and avoid public-surface refactors.

## Implementation Shape

The implementation should proceed in small, reviewable slices:

1. Lock the support policy and tooling baseline.
2. Add or adjust regression tests around identified modernization hotspots.
3. Update compatibility-sensitive code paths to current APIs.
4. Refresh dependencies and clean up now-dead compatibility branches.
5. Run broader verification and fix fallout.

This ordering keeps breakages attributable and reduces the chance of a large undifferentiated upgrade diff.

## Success Criteria

- The project installs and runs on the new supported CPython baseline.
- The existing CLI and config surface still behave the same for users.
- Modern dependency versions are used without relying on known private/legacy APIs.
- CI, tox, and packaging accurately represent the supported runtime matrix.
- The relevant regression suite passes on the modernized codebase.
