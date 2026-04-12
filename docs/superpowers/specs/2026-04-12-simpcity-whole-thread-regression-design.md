# SimpCity Whole-Thread Regression Design

Date: 2026-04-12
Status: Proposed
Topic: Add a fixture-based SimpCity whole-thread regression test for XenForo extraction

## Summary

Add one offline, fixture-based regression test that preserves the real extraction behavior observed on a live SimpCity thread after the SimpCity crawler restore.

The test will use a sanitized whole-thread HTML fixture derived from `https://simpcity.cr/threads/anyone-have-anything-of-les-chesticles.78564/` and assert the extraction results that matter for regression safety:

- real embedded image links are still found
- real external links are still found
- quoted reply backlinks inside blockquotes are not extracted as child links
- the Bunkr album link remains discoverable
- the unsupported absolute URL set remains stable

This is a regression test for the current XenForo parsing contract as exercised by `SimpCityCrawler`, not a live-network crawler test.

## Goals

- Add one SimpCity-specific whole-thread fixture to catch link-extraction regressions in CI.
- Reuse the existing XenForo parsing path already covered by `ForumPost.new(...)` and the SimpCity crawler selectors.
- Preserve the currently validated behavior for quoted content cleanup.
- Keep the test fully offline and deterministic.

## Non-Goals

- No live SimpCity requests in CI.
- No cookie handling inside the test.
- No download assertions against JPG5, Bunkr, or any other downstream hosts.
- No generic XenForo test-harness rewrite.
- No attempt to preserve every cosmetic detail of the source thread HTML.

## Current Behavior To Preserve

Live verification on 2026-04-12 against the restored `SimpCityCrawler` established these extraction results for the target thread after applying the crawler's current XenForo cleanup path:

- post `659664`: 3 images, 2 external links
- post `761355`: 1 image, 2 external links
- post `943678`: 3 images
- post `3173859`: 1 external link
- post `3174102`: no extracted links
- post `3284977`: no extracted links
- post `3297485`: no extracted links
- post `3301990`: no extracted links
- post `44157189`: 1 image
- post `44217641`: 1 external link
- post `45075694`: no extracted links

The posts with no extracted links are still important. They prove that quoted reply backlinks such as `/goto/post?...` do not leak through after XenForo post cleanup.

The validated unsupported absolute URL set from the thread is:

- `https://onlyfans.com/les.chesticles/media`
- `https://www.reddit.com/user/les-chesticles`
- `https://www.depop.com/leschesticles`
- `https://onlyfans.com/u386107680`

For regression purposes, `Instagram` should be treated as a valid extracted external link, not as part of the unsupported URL set, because unsupported classification depends on downstream support policy rather than XenForo extraction itself.

## Design

### 1. Add a sanitized whole-thread fixture

Add one HTML fixture under:

- `tests/test_files/xenforo/simpcity_whole_thread_les_chesticles.html`

The fixture should preserve:

- the `<article class="message"...>` post structure
- `.message-userContent`
- linked `img.bbImage` content
- external anchor tags
- XenForo redirect links
- quoted blockquote content

The fixture should remove or normalize unstable noise where practical:

- unrelated navigation chrome
- IDs or attributes not used by the parser
- timestamps or metadata not required for extraction assertions
- script blocks, ads, or dynamic markup not consumed by the current test

The fixture must remain realistic enough that `ForumPost.new(...)` performs the same cleanup it would on a real page.

### 2. Keep the test in the existing XenForo test module

Add the regression test to:

- `tests/crawlers/test_xenforo.py`

Rationale:

- this file already contains XenForo-specific parsing helpers
- it already instantiates `SimpCityCrawler`
- it already tests post-level image and embed extraction behavior

This avoids inventing a second fixture harness for the same parser family.

### 3. Assert extraction through the real XenForo cleanup path

The regression test must:

1. load the whole-thread fixture with `BeautifulSoup`
2. select all XenForo post articles from the fixture
3. convert each article into `ForumPost` using `ForumPost.new(article, crawler.SELECTORS.posts)`
4. run the same extraction helpers the crawler uses for post content:
   - `_images(...)`
   - `_external_links(...)`

This is important because the quoted-content behavior depends on the cleanup performed inside `ForumPost.new(...)`, especially removal of:

- `blockquote`
- `fauxBlockLink`

The test must verify the post-cleanup output, not the raw DOM.

### 4. Normalize external-link expectations at the extraction layer

The regression should lock down extracted links at the XenForo layer, not at the full downstream crawl layer.

Expected handling:

- direct external URLs remain direct URLs
- XenForo redirect links should be normalized to the decoded absolute URL before assertion
- quoted `/goto/post` backlinks that only appear inside stripped quoted content should not appear in the extracted result

This keeps the test focused on the SimpCity/XenForo parsing contract rather than downloader or unsupported-site policy.

### 5. Use compact expected-data mappings

Expected results should be stored in compact mappings keyed by post id.

Recommended structure:

- `expected_images_by_post: dict[int, list[str]]`
- `expected_links_by_post: dict[int, list[str]]`

At minimum, the assertions must cover:

- the image-bearing posts observed in live validation
- the Bunkr album post
- the quote-only reply-chain posts that should remain empty after cleanup

The test should also assert the full extracted external-link set across the thread to make accidental selector broadening obvious.

## Test Cases

The whole-thread regression test must assert all of the following:

1. **Real image links survive cleanup**
   - posts `659664`, `761355`, `943678`, and `44157189` retain their expected image links

2. **Real external links survive cleanup**
   - posts `659664`, `761355`, `3173859`, and `44217641` retain their expected external links

3. **Quoted reply backlinks stay filtered**
   - posts `3284977`, `3297485`, `3301990`, and `45075694` produce no extracted external links after cleanup

4. **Bunkr album discovery stays intact**
   - post `44217641` still exposes `https://bunkr.cr/a/oFTJIwjx`

5. **Thread-wide external-link set remains stable**
   - the union of extracted external links across all posts matches the expected set from the fixture

## Verification Plan

During implementation, verify with:

- `python -m pytest tests/crawlers/test_xenforo.py -v -p no:cacheprovider`
- optionally a narrower target while iterating:
  - `python -m pytest tests/crawlers/test_xenforo.py -k simpcity -v -p no:cacheprovider`

Success criteria:

- the new SimpCity whole-thread test fails if quote cleanup regresses
- the new test fails if SimpCity image extraction or external-link extraction regresses
- the broader XenForo test file still passes

## Risks

### Fixture too raw

If the fixture preserves too much irrelevant markup, the test becomes hard to read and maintain. The implementation should keep only the markup needed to preserve the parser contract.

### Fixture too synthetic

If the fixture is overly simplified, it may stop representing the real SimpCity/XenForo structure and lose regression value. The implementation should preserve the exact post/article/content nesting used by the current parser.

### Testing the wrong layer

If the test asserts downloader outcomes instead of extraction outcomes, it will become flaky and couple XenForo parsing tests to unrelated host behavior. The implementation must stop at extracted links and post-level expectations.
