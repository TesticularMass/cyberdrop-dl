# SimpCity Restore Design

Date: 2026-04-12
Status: Proposed
Topic: Restore SimpCity support with a best-effort, cookie-dependent caveat

## Summary

Restore SimpCity as a normal supported forum in CyberDropDownloader by re-enabling the existing `SimpCityCrawler`, restoring its presence in supported-site surfaces, and documenting that support is best-effort and requires valid SimpCity cookies with a matching `user-agent`.

This is a product-consistency change more than a net-new crawler implementation. The crawler already exists and already targets `https://simpcity.cr`, but the project currently leaves it in a half-restored state: the crawler is excluded from normal builds via `DEBUG_CRAWLERS`, some SimpCity-specific support logic is still `.su`-only, and user-facing docs still say support was dropped.

## Goals

- Re-enable `SimpCityCrawler` in normal builds.
- Keep `simpcity.cr` as the primary domain.
- Preserve backward compatibility for old `simpcity.su` URLs.
- Restore SimpCity to generated supported-site and supported-domain surfaces.
- Update manual docs so they describe the current restored state with a clear best-effort caveat.
- Keep the auth model cookie-based only.

## Non-Goals

- No automated SimpCity login flow.
- No anti-bot bypass or CAPTCHA solving feature.
- No custom fallback path that silently pretends unauthenticated scraping is supported.
- No large SimpCity-specific parser rewrite unless tests show existing behavior is broken.

## Current State

The current repository already contains an active `SimpCityCrawler` implementation in `cyberdrop_dl/crawlers/xenforo/simpcity.py`:

- `PRIMARY_URL` is already `https://simpcity.cr`
- `OLD_DOMAINS` already includes `simpcity.su`
- Xenforo login behavior already supports cookie-gated forums

The main blockers are elsewhere:

- `SimpCityCrawler` is listed inside `DEBUG_CRAWLERS` in `cyberdrop_dl/crawlers/__init__.py`, which excludes it from normal `CRAWLERS`.
- User-facing docs still route readers to `docs/simpcity-support-dropped.md`.
- `cache_manager.py` still contains a SimpCity-specific request-cache rule for `*.simpcity.su` only.
- Existing tests cover SimpCity parser behavior, but there is little coverage proving it is part of the normal enabled crawler set.

## Design

### 1. Re-enable the crawler

Remove `SimpCityCrawler` from the debug-only exclusion set in `cyberdrop_dl/crawlers/__init__.py`.

Effect:

- SimpCity becomes part of normal `CRAWLERS`
- SimpCity is included in `WEBSITE_CRAWLERS` / `FORUM_CRAWLERS` derived surfaces as appropriate
- generated supported-domain consumers pick it up again through the existing shared model

No new crawler class or special registration path is needed.

### 2. Keep the current domain model

Retain the current SimpCity crawler domain behavior:

- primary domain: `simpcity.cr`
- legacy alias: `simpcity.su`

This uses the existing `OLD_DOMAINS` and `transform_url()` behavior already provided by the base crawler infrastructure. Old `.su` inputs must continue to map into the current `.cr` path automatically.

### 3. Keep cookie-only authentication

Do not add username/password or challenge-bypass logic.

Runtime expectations remain:

- with valid cookies, SimpCity scraping works on a best-effort basis
- without cookies, the crawler must continue to fail through the existing Xenforo login path
- invalid cookies must continue to produce the existing invalid-cookie failure mode

This matches the current forum crawler model and avoids promising unsupported auth behavior.

### 4. Restore user-facing surfaces

There are two different restore paths:

- generated surfaces
- manual documentation surfaces

Generated surfaces:

- `docs/reference/supported-websites.md` is generated from the enabled crawler set
- supported-domain lists used by browser-cookie import and related UI are derived from `SUPPORTED_FORUMS` / `SUPPORTED_SITES_DOMAINS`

Once SimpCity is restored to normal `CRAWLERS`, these surfaces must reflect it after regeneration without custom SimpCity logic.

Manual surfaces:

- remove the current “support dropped” navigation entry from `docs/SUMMARY.md`
- replace that outdated removal guidance with a short operational caveat in current docs, primarily `docs/reference/configuration-options/settings/browser_cookies.md`

Required wording direction:

- SimpCity is supported again
- support is best-effort
- valid SimpCity cookies are required
- the configured `user-agent` must match the browser used for cookie extraction
- site-side anti-bot or rate-limit changes may still break support

### 5. Widen SimpCity-specific support logic

Update any SimpCity-specific logic that is still hard-coded to `.su` where doing so is required for the restored current domain to behave consistently.

Known required target:

- `cyberdrop_dl/managers/cache_manager.py`

The implementation must either:

- add `*.simpcity.cr`, or
- generalize the rule so both `.su` and `.cr` remain covered

The implementation must favor the smallest change that keeps both current and legacy domains working.

## Testing Strategy

Implementation must add or update targeted tests for:

1. Normal crawler registration
   Confirm `SimpCityCrawler` is part of normal `CRAWLERS`.

2. Supported-domain exposure
   Confirm SimpCity appears in `SUPPORTED_FORUMS` and downstream supported-domain surfaces.

3. Legacy URL compatibility
   Confirm old `simpcity.su` URLs still map correctly through the SimpCity crawler path.

4. Existing Xenforo behavior
   Keep current SimpCity parser and image extraction tests passing as the baseline behavior check.

Testing must stay narrow and regression-focused. The repo already has substantial Xenforo coverage; this work must add enablement coverage rather than duplicating parser tests.

## Verification Plan

During implementation, verify with:

- targeted `pytest` runs covering crawler registration and Xenforo tests
- regeneration of `docs/reference/supported-websites.md` through `scripts/tools/update_docs.py`
- manual diff review confirming:
  - SimpCity is restored to current supported-site surfaces
  - the best-effort cookie caveat is present
  - no doc text implies automatic login or anti-bot bypass

## Risks

### Site behavior changes

SimpCity can still change anti-bot or rate-limit behavior independently of this restore. The design handles that by keeping the documentation caveat explicit and by avoiding feature claims the code does not actually support.

### Inconsistent domain handling

Because the repo mixes old `.su` references with new `.cr` behavior, partial restoration could leave stale support code behind. The implementation must explicitly review SimpCity-specific `.su` references and update only the ones that affect runtime behavior or current docs.

### Overpromising support

If docs present SimpCity like an ordinary fully stable forum, users will infer login and anti-bot handling that does not exist. The manual docs must keep the best-effort caveat visible.

## Implementation Notes

- Prefer small edits in the existing crawler registration and docs flow.
- Avoid new abstractions unless a test shows the current structure is insufficient.
- Preserve the historical changelog entry about the prior removal; only current-facing docs should be updated to reflect the restored state.

## Acceptance Criteria

- `SimpCityCrawler` is enabled in normal builds.
- `simpcity.cr` appears again in supported-domain outputs after doc regeneration.
- old `simpcity.su` links remain accepted through the existing alias path.
- current docs no longer say SimpCity support is dropped.
- current docs state that SimpCity support is best-effort and requires valid cookies.
- targeted tests pass.
