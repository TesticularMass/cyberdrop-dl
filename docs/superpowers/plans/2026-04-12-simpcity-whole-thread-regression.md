# SimpCity Whole-Thread Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offline, fixture-based SimpCity whole-thread regression test that locks down current XenForo extraction behavior for one validated SimpCity thread.

**Architecture:** Keep the change entirely inside the test suite. Add one sanitized whole-thread HTML fixture under `tests/test_files/xenforo/`, then add SimpCity-specific assertions in `tests/crawlers/test_xenforo.py` that parse the fixture through `ForumPost.new(...)`, reuse `SimpCityCrawler` extraction helpers, normalize XenForo redirect links offline, and assert the known per-post extraction results.

**Tech Stack:** `pytest`, `pytest-asyncio`, `BeautifulSoup`, existing XenForo crawler helpers in `tests/crawlers/test_xenforo.py`

---

## File Structure

### Files to Create

- `tests/test_files/xenforo/simpcity_whole_thread_les_chesticles.html`
  Responsibility: sanitized whole-thread SimpCity fixture that preserves the real post/article/content nesting and quote structure needed by `ForumPost.new(...)`.

### Files to Modify

- `tests/crawlers/test_xenforo.py`
  Responsibility: fixture loader helpers plus the SimpCity-specific regression tests.

## Task 1: Add The Whole-Thread Fixture

**Files:**
- Create: `tests/test_files/xenforo/simpcity_whole_thread_les_chesticles.html`
- Modify: `tests/crawlers/test_xenforo.py`
- Test: `tests/crawlers/test_xenforo.py::test_simpcity_whole_thread_fixture_contains_expected_post_ids`

- [ ] **Step 1: Write the failing fixture smoke test**

Add this near the other XenForo test helpers in `tests/crawlers/test_xenforo.py`:

```python
SIMPCITY_WHOLE_THREAD_FIXTURE = (
    Path(__file__).resolve().parents[1] / "test_files" / "xenforo" / "simpcity_whole_thread_les_chesticles.html"
)


def _load_xenforo_fixture(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def test_simpcity_whole_thread_fixture_contains_expected_post_ids() -> None:
    soup = _load_xenforo_fixture(SIMPCITY_WHOLE_THREAD_FIXTURE)
    articles = soup.select("article.message[id*=post]")
    ids = [int(article["id"].rsplit("-", 1)[-1]) for article in articles]
    assert ids == [
        659664,
        761355,
        943678,
        3173859,
        3174102,
        3284977,
        3297485,
        3301990,
        44157189,
        44217641,
        45075694,
    ]
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run:

```bash
python -m pytest tests/crawlers/test_xenforo.py::test_simpcity_whole_thread_fixture_contains_expected_post_ids -v -p no:cacheprovider
```

Expected:

```text
FAIL ... FileNotFoundError: ... simpcity_whole_thread_les_chesticles.html
```

- [ ] **Step 3: Create the sanitized whole-thread fixture**

Create `tests/test_files/xenforo/simpcity_whole_thread_les_chesticles.html` with this exact content:

```html
<html>
  <body>
    <article class="message message--post" id="js-post-659664">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              <a href="https://jpg6.su/img/inb3ja"><img class="bbImage" src="https://simp1.selti-delivery.ru/images/ADE9702D-BAD9-4DAB-BE13-1340B334D45A.md.jpg" /></a>
              <a href="https://jpg6.su/img/inbZAH"><img class="bbImage" src="https://simp1.selti-delivery.ru/images/FAF16779-0151-461A-B56A-F6A5A7D5A6A7.md.jpg" /></a>
              <a href="https://jpg6.su/img/inbLWu"><img class="bbImage" src="https://simp1.selti-delivery.ru/images/36E0B645-741D-42D2-8923-4DF52311C502.md.jpg" /></a>
              <a href="https://onlyfans.com/les.chesticles/media">OnlyFans</a>
              <a href="https://instagram.com/les.chesticles?igshid=YmMyMTA2M2Y=">Instagram</a>
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-761355">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              <a href="https://jpg6.su/img/micsAH"><img class="bbImage" src="https://simp4.selti-delivery.ru/g2rxt9qd8wc91.md.jpg" /></a>
              <a href="/redirect/?to=aHR0cHM6Ly93d3cucmVkZGl0LmNvbS91c2VyL2xlcy1jaGVzdGljbGVzLw&e=1&m=b64">Reddit</a>
              <a href="/redirect/?to=aHR0cHM6Ly93d3cuZGVwb3AuY29tL2xlc2NoZXN0aWNsZXMv&e=1&m=b64">Depop</a>
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-943678">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              <a href="https://jpg6.su/img/8h5sPi"><img class="bbImage" src="https://simp4.selti-delivery.ru/237q2qzze4m91f4cbe0e27fd2a15a.md.jpg" /></a>
              <a href="https://jpg6.su/img/8h5c0P"><img class="bbImage" src="https://simp4.selti-delivery.ru/k3zqncz7l4m9191ce0eada5ace347.md.jpg" /></a>
              <a href="https://jpg6.su/img/8h5Q7o"><img class="bbImage" src="https://simp4.selti-delivery.ru/zyortmzbe4m9116f79626d853988b.md.jpg" /></a>
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-3173859">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              <a href="https://onlyfans.com/u386107680">OnlyFans profile</a>
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-3174102">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">hopefully more comes out soon</div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-3284977">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              <blockquote>
                <div class="bbWrapper">
                  <a href="/goto/post?id=3174102">Donpierre said:</a>
                </div>
              </blockquote>
              Sofar nothing on her OF that you can't see on her insta
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-3297485">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              <blockquote>
                <div class="bbWrapper">
                  <a href="/goto/post?id=3284977">dexterscock said:</a>
                </div>
              </blockquote>
              Worth the follow?
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-3301990">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              <blockquote>
                <div class="bbWrapper">
                  <a href="/goto/post?id=3297485">Donpierre said:</a>
                </div>
              </blockquote>
              at this point... negative.
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-44157189">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              <a href="https://jpg6.su/img/NxwG7Um"><img class="bbImage" src="https://simp6.selti-delivery.ru/images4/IMG_879659805eab35eeb647.md.jpg" /></a>
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-44217641">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              <a href="https://bunkr.cr/a/oFTJIwjx">Bunkr album</a>
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>

    <article class="message message--post" id="js-post-45075694">
      <div class="message-content">
        <div class="message-userContent">
          <article class="message-body js-selectToQuote">
            <div class="bbWrapper">
              Do you have anymore PPV in your dms?
              <blockquote>
                <div class="bbWrapper">
                  <a href="/goto/post?id=44157189">noconye said:</a>
                </div>
              </blockquote>
            </div>
            <div class="js-selectToQuoteEnd">&nbsp;</div>
          </article>
        </div>
      </div>
    </article>
  </body>
</html>
```

- [ ] **Step 4: Run the smoke test to verify it passes**

Run:

```bash
python -m pytest tests/crawlers/test_xenforo.py::test_simpcity_whole_thread_fixture_contains_expected_post_ids -v -p no:cacheprovider
```

Expected:

```text
PASSED
```

- [ ] **Step 5: Commit the fixture checkpoint**

```bash
git add tests/crawlers/test_xenforo.py tests/test_files/xenforo/simpcity_whole_thread_les_chesticles.html
git commit -m "test: add simpcity whole-thread fixture"
```

## Task 2: Add The SimpCity Whole-Thread Regression Test

**Files:**
- Modify: `tests/crawlers/test_xenforo.py`
- Test: `tests/crawlers/test_xenforo.py::test_simpcity_whole_thread_preserves_extraction_regression_shape`

- [ ] **Step 1: Write the failing regression test**

Add this below the existing SimpCity XenForo extraction tests in `tests/crawlers/test_xenforo.py`:

```python
def _simpcity_fixture_posts() -> dict[int, _forum.ForumPost]:
    crawler = crawler_instances[crawlers.SimpCityCrawler]
    soup = _load_xenforo_fixture(SIMPCITY_WHOLE_THREAD_FIXTURE)
    posts: dict[int, _forum.ForumPost] = {}
    for article in soup.select(crawler.SELECTORS.posts.article):
        post = _forum.ForumPost.new(article, crawler.SELECTORS.posts)
        posts[post.id] = post
    return posts


@pytest.mark.asyncio
async def test_simpcity_whole_thread_preserves_extraction_regression_shape() -> None:
    crawler = crawler_instances[crawlers.SimpCityCrawler]
    posts = _simpcity_fixture_posts()

    expected_images_by_post = {
        659664: [
            "https://simp1.selti-delivery.ru/images/ADE9702D-BAD9-4DAB-BE13-1340B334D45A.md.jpg",
            "https://simp1.selti-delivery.ru/images/FAF16779-0151-461A-B56A-F6A5A7D5A6A7.md.jpg",
            "https://simp1.selti-delivery.ru/images/36E0B645-741D-42D2-8923-4DF52311C502.md.jpg",
        ],
        761355: [
            "https://simp4.selti-delivery.ru/g2rxt9qd8wc91.md.jpg",
        ],
        943678: [
            "https://simp4.selti-delivery.ru/237q2qzze4m91f4cbe0e27fd2a15a.md.jpg",
            "https://simp4.selti-delivery.ru/k3zqncz7l4m9191ce0eada5ace347.md.jpg",
            "https://simp4.selti-delivery.ru/zyortmzbe4m9116f79626d853988b.md.jpg",
        ],
        3173859: [],
        3174102: [],
        3284977: [],
        3297485: [],
        3301990: [],
        44157189: [
            "https://simp6.selti-delivery.ru/images4/IMG_879659805eab35eeb647.md.jpg",
        ],
        44217641: [],
        45075694: [],
    }

    expected_links_by_post = {
        659664: [
            "https://onlyfans.com/les.chesticles/media",
            "https://instagram.com/les.chesticles?igshid=YmMyMTA2M2Y=",
        ],
        761355: [
            "https://www.reddit.com/user/les-chesticles",
            "https://www.depop.com/leschesticles",
        ],
        943678: [],
        3173859: [
            "https://onlyfans.com/u386107680",
        ],
        3174102: [],
        3284977: [],
        3297485: [],
        3301990: [],
        44157189: [],
        44217641: [
            "https://bunkr.cr/a/oFTJIwjx",
        ],
        45075694: [],
    }

    for post_id, expected_images in expected_images_by_post.items():
        assert list(crawler._images(posts[post_id])) == expected_images

    actual_links_by_post = {
        post_id: await _normalize_extracted_links(crawler, post)
        for post_id, post in posts.items()
    }
    assert actual_links_by_post == expected_links_by_post

    all_links = {link for links in actual_links_by_post.values() for link in links}
    assert all_links == {
        "https://onlyfans.com/les.chesticles/media",
        "https://instagram.com/les.chesticles?igshid=YmMyMTA2M2Y=",
        "https://www.reddit.com/user/les-chesticles",
        "https://www.depop.com/leschesticles",
        "https://onlyfans.com/u386107680",
        "https://bunkr.cr/a/oFTJIwjx",
    }

    assert {
        link
        for link in all_links
        if "instagram.com" not in link and "bunkr.cr" not in link
    } == {
        "https://onlyfans.com/les.chesticles/media",
        "https://www.reddit.com/user/les-chesticles",
        "https://www.depop.com/leschesticles",
        "https://onlyfans.com/u386107680",
    }
```

- [ ] **Step 2: Run the regression test to verify it fails**

Run:

```bash
python -m pytest tests/crawlers/test_xenforo.py::test_simpcity_whole_thread_preserves_extraction_regression_shape -v -p no:cacheprovider
```

Expected:

```text
FAIL ... NameError: name '_normalize_extracted_links' is not defined
```

- [ ] **Step 3: Add the minimal link-normalization helper**

Add this helper immediately above the new async test in `tests/crawlers/test_xenforo.py`:

```python
async def _normalize_extracted_links(
    crawler: xenforo.XenforoCrawler, post: _forum.ForumPost
) -> list[str]:
    normalized: list[str] = []
    for link in crawler._external_links(post):
        absolute = await crawler.get_absolute_link(link)
        assert absolute is not None
        normalized.append(str(absolute))
    return normalized
```

- [ ] **Step 4: Run the regression test to verify it passes**

Run:

```bash
python -m pytest tests/crawlers/test_xenforo.py::test_simpcity_whole_thread_preserves_extraction_regression_shape -v -p no:cacheprovider
```

Expected:

```text
PASSED
```

- [ ] **Step 5: Commit the regression test**

```bash
git add tests/crawlers/test_xenforo.py
git commit -m "test: add simpcity whole-thread regression"
```

## Task 3: Verify The Broader XenForo And SimpCity Coverage

**Files:**
- Modify: none
- Test: `tests/crawlers/test_xenforo.py`, `tests/test_simpcity_restore.py`

- [ ] **Step 1: Run the focused SimpCity regression targets**

Run:

```bash
python -m pytest tests/crawlers/test_xenforo.py::test_simpcity_whole_thread_fixture_contains_expected_post_ids tests/crawlers/test_xenforo.py::test_simpcity_whole_thread_preserves_extraction_regression_shape -v -p no:cacheprovider
```

Expected:

```text
2 passed
```

- [ ] **Step 2: Run the full XenForo test file**

Run:

```bash
python -m pytest tests/crawlers/test_xenforo.py -v -p no:cacheprovider
```

Expected:

```text
76 passed, 1 xfailed, 1 xpassed
```

- [ ] **Step 3: Run the SimpCity restore regression file**

Run:

```bash
python -m pytest tests/test_simpcity_restore.py -v -p no:cacheprovider
```

Expected:

```text
5 passed
```

- [ ] **Step 4: Verify the worktree is clean after the prior commits**

```bash
git status --short
```

Expected:

```text
<no output>
```
