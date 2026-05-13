import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from playwright.async_api import (
    BrowserContext,
    Page,
    async_playwright,
)

from claude_agent import ClaudeAgent

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)

SESSION_FILE = Path(__file__).parent / "session.json"
APPLIED_FILE = Path(__file__).parent / "applied_jobs.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# --------------------------------------------------------------------------- #
#  Applied-jobs log                                                            #
# --------------------------------------------------------------------------- #

def load_applied_ids() -> set[str]:
    if APPLIED_FILE.exists():
        return {e["id"] for e in json.loads(APPLIED_FILE.read_text())}
    return set()


def log_applied(job_id: str, title: str, company: str) -> None:
    data = json.loads(APPLIED_FILE.read_text()) if APPLIED_FILE.exists() else []
    data.append(
        {
            "id": job_id,
            "title": title,
            "company": company,
            "applied_at": datetime.now().isoformat(),
        }
    )
    APPLIED_FILE.write_text(json.dumps(data, indent=2))


# --------------------------------------------------------------------------- #
#  Bot                                                                         #
# --------------------------------------------------------------------------- #

class LinkedInBot:
    def __init__(self, config: dict):
        self.config = config
        self.search = config["search"]
        self.claude = ClaudeAgent(config)
        self.applied_ids = load_applied_ids()

    # ------------------------------------------------------------------ #

    async def run(self) -> None:
        if not SESSION_FILE.exists():
            logger.error("session.json not found. Run save_session.py first.")
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=30,
                args=["--start-maximized"],
            )
            context = await browser.new_context(
                storage_state=str(SESSION_FILE),
                viewport={"width": 1280, "height": 800},
                user_agent=USER_AGENT,
            )
            page = await context.new_page()

            try:
                await self._search_and_apply(page, context)
            except KeyboardInterrupt:
                logger.info("Stopped by user.")
            finally:
                try:
                    await context.storage_state(path=str(SESSION_FILE))
                except Exception:
                    pass
                try:
                    await browser.close()
                except Exception:
                    pass

    # ------------------------------------------------------------------ #

    async def _search_and_apply(self, page: Page, context: BrowserContext) -> None:
        search_urls = self.search.get("search_urls", [])
        if not search_urls or search_urls == ["PASTE_YOUR_LINKEDIN_SEARCH_URL_HERE"]:
            logger.error("No search_urls set in config.json.")
            return

        max_apps = self.search.get("max_applications", 25)
        delay = self.search.get("delay_between_apps_seconds", 4)
        applied = 0

        for search_url in search_urls:
            if applied >= max_apps:
                break
            applied = await self._process_search_url(page, search_url, applied, max_apps, delay)

        logger.info(f"Done. Total applied this run: {applied}")

    async def _process_search_url(
        self, page: Page, search_url: str, applied: int, max_apps: int, delay: int
    ) -> int:
        logger.info(f"Search URL: {search_url}")
        base_url = search_url.split("&currentJobId=")[0].split("?currentJobId=")[0]
        page_num = 1

        while applied < max_apps:
            # Navigate to the search page for this iteration
            logger.info(f"  Loading page {page_num}...")
            await page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # Check for login redirect
            if any(x in page.url for x in ("login", "authwall", "checkpoint")):
                logger.error("Redirected to login — session expired. Run save_session.py.")
                return applied

            # Wait for job links to render
            try:
                await page.wait_for_selector('a[href*="/jobs/view/"]', timeout=15000)
            except Exception:
                body = await page.evaluate("() => document.body.innerText.slice(0, 400)")
                logger.warning(f"No job links appeared. Page: {body}")
                break

            await self._scroll_job_list(page)
            await page.wait_for_timeout(600)

            job_ids = await self._collect_job_ids_from_links(page)
            if not job_ids:
                logger.warning(f"No jobs on page {page_num}.")
                break

            logger.info(f"Page {page_num}: {len(job_ids)} job(s).")
            new_this_page = 0

            for job_id in job_ids:
                if applied >= max_apps:
                    break
                if job_id in self.applied_ids:
                    continue

                new_this_page += 1

                # Load job in the right panel by adding currentJobId to the search URL
                job_url = f"{base_url}&currentJobId={job_id}"
                logger.info(f"  Navigating to: {job_url}")
                try:
                    await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    logger.warning(f"  goto failed: {e}")
                    continue
                await page.wait_for_timeout(2500)

                # Detect login redirect
                current = page.url
                if "login" in current or "authwall" in current or "checkpoint" in current:
                    logger.error("Redirected to login — session expired. Run save_session.py to refresh.")
                    return applied
                logger.info(f"  Loaded: {current}")

                title = await self._safe_text(page, [
                    ".job-details-jobs-unified-top-card__job-title h1",
                    ".jobs-unified-top-card__job-title h1",
                    "h1.t-24", "h1",
                ])
                company = await self._safe_text(page, [
                    ".job-details-jobs-unified-top-card__company-name a",
                    ".jobs-unified-top-card__company-name a",
                    ".topcard__org-name-link",
                    ".job-details-jobs-unified-top-card__primary-description-without-tagline a",
                ])

                easy_btn = await self._find_easy_apply_button(page)
                if not easy_btn:
                    logger.info(f"  skip (no Easy Apply): {title} @ {company}")
                    self.applied_ids.add(job_id)
                    continue

                logger.info(f"  applying: {title} @ {company}")
                await easy_btn.click()
                await page.wait_for_timeout(2000)

                ok = await self._handle_modal(page, title, company)
                await self._force_close_any_modal(page)

                if ok:
                    self.applied_ids.add(job_id)
                    log_applied(job_id, title, company)
                    applied += 1
                    logger.info(f"  APPLIED ({applied}/{max_apps}): {title} @ {company}")
                else:
                    logger.warning(f"  FAILED or SKIPPED: {title} @ {company}")

                await page.wait_for_timeout(delay * 1000)

            if new_this_page == 0:
                logger.info("No new jobs on this page.")
                break

            # Advance to next page of search results
            await self._force_close_any_modal(page)
            await page.goto(base_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            next_btn = await page.query_selector("button[aria-label='View next page']")
            if not next_btn:
                logger.info("No next page.")
                break
            try:
                await next_btn.click(timeout=8000)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(1500)
                page_num += 1
            except Exception:
                break

        return applied

    async def _collect_job_ids_from_links(self, page: Page) -> list[str]:
        """Extract unique job IDs from /jobs/view/<id> hrefs on the page."""
        import re
        hrefs: list[str] = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a[href*="/jobs/view/"]'))
                          .map(a => a.href)"""
        )
        if hrefs:
            logger.info(f"  Sample href: {hrefs[0]}")  # one-time debug to verify format
        seen: set[str] = set()
        ids: list[str] = []
        for href in hrefs:
            m = re.search(r"/jobs/view/(\d+)", href)
            if m:
                jid = m.group(1)
                if jid not in seen:
                    seen.add(jid)
                    ids.append(jid)
        return ids

    # ------------------------------------------------------------------ #
    #  Modal handler                                                       #
    # ------------------------------------------------------------------ #

    # LinkedIn uses different modal class names — match any of them
    _MODAL_SELECTOR = (
        ".jobs-easy-apply-modal, "
        "[data-test-modal-id='easy-apply-modal'], "
        ".artdeco-modal[role='dialog']"
    )

    async def _handle_modal(self, page: Page, title: str, company: str) -> bool:
        try:
            await page.wait_for_selector(self._MODAL_SELECTOR, timeout=7000)
        except Exception:
            logger.warning("  Modal did not appear.")
            return False

        last_page_html = ""
        stuck_count = 0

        for _step in range(20):
            await page.wait_for_timeout(900)

            # Handle resume upload page — just click "Use resume" / Next without uploading
            await self._handle_resume_step(page)

            # Fill visible fields
            await self._fill_visible_fields(page, title, company)
            await page.wait_for_timeout(500)

            # Submit?
            submit = await page.query_selector("button[aria-label='Submit application']")
            if submit and await submit.is_enabled():
                await submit.click()
                await page.wait_for_timeout(3000)
                await self._dismiss_confirmation(page)
                await page.wait_for_timeout(1000)
                return True

            # Detect validation errors and log them
            errors = await self._collect_field_errors(page)
            if errors:
                logger.warning(f"  Validation errors: {errors}")

            # Try to advance
            advanced = await self._click_advance_button(page)
            if not advanced:
                logger.warning("  No advance button found — giving up on this job.")
                break

            # Detect stuck state (same page content after clicking Next)
            try:
                modal_el = await page.query_selector(self._MODAL_SELECTOR)
                current_html = await modal_el.inner_html() if modal_el else ""
                if current_html == last_page_html:
                    stuck_count += 1
                    if stuck_count >= 2:
                        logger.warning("  Stuck on same modal page — giving up.")
                        break
                else:
                    stuck_count = 0
                last_page_html = current_html
            except Exception:
                pass

        await self._discard_modal(page)
        return False

    async def _handle_resume_step(self, page: Page) -> None:
        """Skip the resume upload page by clicking the existing-resume option."""
        for sel in [
            "button[aria-label='Use resume']",
            "label[data-test-resume-choice]",
            ".jobs-resume-picker__resume-btn-label",
        ]:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(500)
                    return
            except Exception:
                pass

    async def _collect_field_errors(self, page: Page) -> list[str]:
        """Return visible validation error messages from the modal."""
        errors = []
        for sel in [
            ".artdeco-inline-feedback--error",
            "[data-test-form-element-error-message]",
            ".fb-form-element__error-text",
        ]:
            try:
                els = await page.query_selector_all(sel)
                for el in els:
                    if await el.is_visible():
                        txt = (await el.inner_text()).strip()
                        if txt:
                            errors.append(txt)
            except Exception:
                pass
        return errors

    async def _click_advance_button(self, page: Page) -> bool:
        """Click the primary forward button inside the modal. Returns True if found."""
        selectors = [
            "button[aria-label='Continue to next step']",
            "button[aria-label='Review your application']",
        ]
        for sel in selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_enabled():
                await btn.click()
                return True

        # Fallback: any primary button with forward-moving text inside the modal
        for modal_sel in [self._MODAL_SELECTOR]:
            modal_el = await page.query_selector(modal_sel)
            if not modal_el:
                continue
        buttons = await page.query_selector_all(f"{self._MODAL_SELECTOR} button.artdeco-button--primary")
        for btn in buttons:
            text = (await btn.inner_text()).strip().lower()
            if any(t in text for t in ("next", "review", "continue", "submit")):
                if await btn.is_enabled():
                    await btn.click()
                    return True

        return False

    # ------------------------------------------------------------------ #
    #  Form filling                                                        #
    # ------------------------------------------------------------------ #

    async def _fill_visible_fields(self, page: Page, title: str, company: str) -> None:
        modal = await page.query_selector(".jobs-easy-apply-modal")
        if not modal:
            return

        # --- Text / number inputs ---
        inputs = await modal.query_selector_all(
            "input:not([type='hidden']):not([type='file']):not([type='radio']):not([type='checkbox'])"
        )
        for inp in inputs:
            if not await inp.is_visible():
                continue
            existing = (await inp.input_value()).strip()
            if existing:
                continue
            label = await self._label_for(page, inp)
            if not label:
                continue
            input_type = await inp.get_attribute("type") or "text"
            field_type = "number" if input_type == "number" else "text"
            answer = await self.claude.get_answer(label, field_type, title, company)
            if answer:
                await inp.fill(answer)

        # --- Selects ---
        selects = await modal.query_selector_all("select")
        for sel in selects:
            if not await sel.is_visible():
                continue
            options_els = await sel.query_selector_all("option")
            option_texts = [await o.inner_text() for o in options_els]
            label = await self._label_for(page, sel)
            if not label:
                continue
            answer = await self.claude.get_answer(label, "select", title, company, options=option_texts)
            if answer:
                try:
                    await sel.select_option(label=answer)
                except Exception:
                    pass

        # --- Radio groups ---
        await self._fill_radio_groups(page, modal, title, company)

        # --- Textareas ---
        textareas = await modal.query_selector_all("textarea")
        for ta in textareas:
            if not await ta.is_visible():
                continue
            existing = (await ta.input_value()).strip()
            if existing:
                continue
            label = await self._label_for(page, ta)
            if not label:
                continue
            answer = await self.claude.get_answer(label, "textarea", title, company)
            if answer:
                await ta.fill(answer)

    async def _fill_radio_groups(self, page: Page, modal, title: str, company: str) -> None:
        """Fill radio-button groups by reading fieldset legends."""
        fieldsets = await modal.query_selector_all("fieldset")
        for fieldset in fieldsets:
            legend = await fieldset.query_selector("legend")
            if not legend:
                continue
            question = (await legend.inner_text()).strip()
            if not question:
                continue

            radios = await fieldset.query_selector_all("input[type='radio']")
            if not radios:
                continue

            # Skip if already answered
            any_checked = any([await r.is_checked() for r in radios])
            if any_checked:
                continue

            option_labels: list[str] = []
            for radio in radios:
                radio_id = await radio.get_attribute("id")
                lbl_text = ""
                if radio_id:
                    lbl_el = await page.query_selector(f"label[for='{radio_id}']")
                    if lbl_el:
                        lbl_text = (await lbl_el.inner_text()).strip()
                option_labels.append(lbl_text)

            answer = await self.claude.get_answer(
                question, "radio", title, company, options=option_labels
            )

            for i, radio in enumerate(radios):
                if i < len(option_labels) and option_labels[i].strip().lower() == answer.strip().lower():
                    # Click the label (the visible target) not the hidden input
                    radio_id = await radio.get_attribute("id")
                    clicked = False
                    if radio_id:
                        lbl = await page.query_selector(f"label[for='{radio_id}']")
                        if lbl:
                            await lbl.click()
                            clicked = True
                    if not clicked:
                        await radio.click(force=True)
                    break

    # ------------------------------------------------------------------ #
    #  Utilities                                                           #
    # ------------------------------------------------------------------ #

    async def _label_for(self, page: Page, element) -> str:
        """Return the human-readable label associated with a form element."""
        try:
            el_id = await element.get_attribute("id")
            if el_id:
                lbl = await page.query_selector(f"label[for='{el_id}']")
                if lbl:
                    return (await lbl.inner_text()).strip()
            aria = await element.get_attribute("aria-label")
            if aria:
                return aria.strip()
            placeholder = await element.get_attribute("placeholder")
            if placeholder:
                return placeholder.strip()
            # Walk up to find a wrapping label
            text = await element.evaluate(
                "el => { const l = el.closest('label'); return l ? l.innerText : ''; }"
            )
            if text:
                return text.strip()
        except Exception:
            pass
        return ""

    async def _find_easy_apply_button(self, page: Page):
        # Wait for the apply section to render before checking
        try:
            await page.wait_for_selector(
                "button.jobs-apply-button, .jobs-s-apply button, [aria-label*='Easy Apply']",
                timeout=6000,
            )
        except Exception:
            pass

        selectors = [
            "button[aria-label*='Easy Apply']",
            "button.jobs-apply-button",
            ".jobs-s-apply button",
            ".jobs-apply-button",
        ]
        for sel in selectors:
            try:
                btns = await page.query_selector_all(sel)
                for btn in btns:
                    if await btn.is_visible():
                        text = (await btn.inner_text()).strip()
                        if "easy apply" in text.lower():
                            return btn
            except Exception:
                continue
        return None

    async def _force_close_any_modal(self, page: Page) -> None:
        """Close any open artdeco modal overlay so it never blocks the page."""
        for _ in range(3):
            try:
                overlay = await page.query_selector(
                    "[data-test-modal-container], .artdeco-modal-overlay[aria-hidden='false']"
                )
                if not overlay:
                    return
                # Try close/dismiss buttons inside the modal first
                for close_sel in [
                    "button[aria-label='Dismiss']",
                    "button[aria-label='Close']",
                    "[data-test-modal-close-btn]",
                ]:
                    btn = await page.query_selector(close_sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(600)
                        # Confirm discard if prompted
                        for discard_sel in [
                            "button[data-control-name='discard_native_overlay']",
                            "button.artdeco-button--primary:has-text('Discard')",
                        ]:
                            d = await page.query_selector(discard_sel)
                            if d and await d.is_visible():
                                await d.click()
                                await page.wait_for_timeout(600)
                        break
                else:
                    # Nothing to click — press Escape as last resort
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(600)
            except Exception:
                pass

    async def _dismiss_confirmation(self, page: Page) -> None:
        for sel in [
            "button[aria-label='Dismiss']",
            "button[aria-label='Close']",
        ]:
            try:
                btn = await page.wait_for_selector(sel, timeout=3000)
                if btn:
                    await btn.click()
                    return
            except Exception:
                pass

    async def _discard_modal(self, page: Page) -> None:
        """Close modal without submitting and confirm discard."""
        for close_sel in ["button[aria-label='Dismiss']", "button[aria-label='Close']"]:
            try:
                btn = await page.query_selector(close_sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(800)
                    break
            except Exception:
                pass
        # Confirm discard dialog
        for discard_sel in [
            "button[data-control-name='discard_native_overlay']",
            "button:has-text('Discard')",
        ]:
            try:
                btn = await page.query_selector(discard_sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    return
            except Exception:
                pass

    async def _scroll_job_list(self, page: Page) -> None:
        """Scroll the left job-list panel so LinkedIn renders all ~25 cards on the page."""
        panel_selectors = [
            ".jobs-search-results-list",
            ".scaffold-layout__list",
            "[data-view-name='job-search-results-list']",
        ]
        panel = None
        for sel in panel_selectors:
            panel = await page.query_selector(sel)
            if panel:
                break

        if panel:
            for _ in range(8):
                await panel.evaluate("el => el.scrollTop += 500")
                await page.wait_for_timeout(400)
            # Scroll back to top so cards are clickable from the start
            await panel.evaluate("el => el.scrollTop = 0")
            await page.wait_for_timeout(300)
        else:
            # Fallback: scroll the whole page
            await page.evaluate("window.scrollBy(0, 3000)")
            await page.wait_for_timeout(600)
            await page.evaluate("window.scrollTo(0, 0)")

    async def _collect_job_cards(self, page: Page):
        for sel in [
            ".job-card-container[data-job-id]",
            "[data-occludable-job-id]",
            ".jobs-search-results__list-item",
            "li.scaffold-layout__list-item",
            "[data-job-id]",
            ".job-card-list",
        ]:
            cards = await page.query_selector_all(sel)
            if cards:
                logger.info(f"  Found {len(cards)} cards via '{sel}'")
                return cards
        logger.warning("  _collect_job_cards: no cards found with any selector")
        return []

    async def _safe_text(self, page: Page, selectors: list[str]) -> str:
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    text = (await el.inner_text()).strip()
                    if text:
                        return text
            except Exception:
                pass
        return "Unknown"
