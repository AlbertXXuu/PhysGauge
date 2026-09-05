// Open a local Studio with playwright-cli, then run:
// playwright-cli run-code --filename scripts/check_home_navigation.js
async (page) => {
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(await page.evaluate(() => location.hostname))) {
    throw new Error('Run this check against a local PhysGauge Studio.');
  }
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  const logo = page.getByRole('button', { name: 'AlvenX — Back to top', exact: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  const desktopHeader = await page.evaluate(() => {
    const header = document.querySelector('.site-header');
    const wordmark = document.querySelector('[data-alvenx-home]');
    const wordmarkImage = wordmark.querySelector('img');
    const style = getComputedStyle(header);
    const wordmarkStyle = getComputedStyle(wordmark);
    return {
      position: style.position,
      top: style.top,
      zIndex: style.zIndex,
      minHeight: style.minHeight,
      gap: style.gap,
      padding: style.padding,
      borderRadius: style.borderRadius,
      backgroundColor: style.backgroundColor,
      backgroundImage: style.backgroundImage,
      backdropFilter: style.backdropFilter || style.webkitBackdropFilter,
      wordmark: {
        width: wordmark.getBoundingClientRect().width,
        imageWidth: wordmarkImage.getBoundingClientRect().width,
        padding: wordmarkStyle.padding,
        borderWidth: wordmarkStyle.borderWidth,
        margin: wordmarkStyle.margin,
        backgroundColor: wordmarkStyle.backgroundColor,
        backgroundImage: wordmarkStyle.backgroundImage,
        appearance: wordmarkStyle.appearance,
      },
    };
  });
  check(desktopHeader.position === 'fixed' && desktopHeader.top === '14px' && desktopHeader.zIndex === '100', 'Header placement differs from the shared contract.');
  check(desktopHeader.minHeight === '70px' && desktopHeader.gap === '28px' && desktopHeader.padding === '12px 18px 12px 22px', 'Header geometry differs from the shared contract.');
  check(desktopHeader.borderRadius === '26px' && desktopHeader.backgroundColor === 'rgba(255, 255, 255, 0.26)' && desktopHeader.backgroundImage === 'none', 'Header glass differs from the shared contract.');
  check(desktopHeader.backdropFilter === 'blur(18px) saturate(1.48)' && desktopHeader.wordmark.width === 160 && desktopHeader.wordmark.imageWidth === 160, 'Header blur or wordmark width differs from the shared contract.');
  check(desktopHeader.wordmark.padding === '0px' && desktopHeader.wordmark.borderWidth === '0px' && desktopHeader.wordmark.margin === '0px', 'Wordmark button spacing or border differs from the reset contract.');
  check(desktopHeader.wordmark.backgroundColor === 'rgba(0, 0, 0, 0)' && desktopHeader.wordmark.backgroundImage === 'none' && desktopHeader.wordmark.appearance === 'none', 'Wordmark button background or native appearance was not reset.');
  await logo.focus();
  check(await logo.evaluate(element => element === document.activeElement && getComputedStyle(element).outlineStyle !== 'none'), 'Wordmark button keyboard focus is not visible.');
  const inactiveTab = page.getByRole('tab', { name: 'Learned-model study', exact: true });
  const idleTab = await inactiveTab.evaluate(element => ({ rect: element.getBoundingClientRect().toJSON(), background: getComputedStyle(element).backgroundColor }));
  await inactiveTab.hover();
  const hoverTab = await inactiveTab.evaluate(element => ({ rect: element.getBoundingClientRect().toJSON(), background: getComputedStyle(element).backgroundColor }));
  check(idleTab.background === 'rgba(0, 0, 0, 0)' && hoverTab.background === 'rgba(255, 255, 255, 0.72)', 'View-tab idle or hover state differs from the contract.');
  check(idleTab.rect.x === hoverTab.rect.x && idleTab.rect.y === hoverTab.rect.y && idleTab.rect.width === hoverTab.rect.width && idleTab.rect.height === hoverTab.rect.height, 'View-tab hover displaced its target.');
  await inactiveTab.focus();
  check(await inactiveTab.evaluate(element => element === document.activeElement && getComputedStyle(element).outlineStyle !== 'none'), 'View-tab keyboard focus is not visible.');
  await page.getByRole('combobox', { name: 'Cases', exact: true }).selectOption('2');
  await page.getByRole('spinbutton', { name: 'Seed', exact: true }).fill('731');
  await page.getByRole('button', { name: 'Run local smoke check' }).click();
  await page.waitForFunction(() => document.querySelector('#run-status').textContent.startsWith('PASS'));
  await page.getByRole('tab', { name: 'Learned-model study', exact: true }).click();
  await page.evaluate(() => {
    window.__homeProbe = { original: window.scrollTo, calls: [] };
    window.scrollTo = function (options) {
      window.__homeProbe.calls.push(options);
      return window.__homeProbe.original.call(window, options);
    };
  });
  const state = () => page.evaluate(() => ({
    url: location.href,
    historyLength: history.length,
    origin: performance.timeOrigin,
    cases: document.querySelector('#smoke-cases').value,
    seed: document.querySelector('#smoke-seed').value,
    result: document.querySelector('#run-status').textContent,
    records: document.querySelector('#metric-records').textContent,
    selected: document.querySelector('[role="tab"][aria-selected="true"]').id,
    panels: [...document.querySelectorAll('[data-panel]')].map(panel => [panel.id, panel.hidden]),
  }));
  const baseline = await state();
  check(baseline.records === '20' && baseline.selected === 'learned-tab', 'Fresh evidence fixture did not load.');
  const cases = [];
  try {
    for (const reducedMotion of ['no-preference', 'reduce']) {
      await page.emulateMedia({ reducedMotion });
      await page.evaluate(() => {
        window.__homeProbe.original.call(window, { top: 0, behavior: 'instant' });
        window.__homeProbe.calls.length = 0;
      });
      await logo.click();
      check(await page.evaluate(() => window.scrollY === 0 && window.__homeProbe.calls.length === 0), 'Top click must be a no-op.');
      check(JSON.stringify(await state()) === JSON.stringify(baseline), 'Top click changed URL, view, inputs, evidence, or document.');
      cases.push(`${reducedMotion}: top click is a no-op`);
      for (const activation of ['pointer', 'Enter', 'Space']) {
        await page.evaluate(() => {
          window.__homeProbe.original.call(window, { top: document.documentElement.scrollHeight, behavior: 'instant' });
          window.__homeProbe.calls.length = 0;
        });
        check(await page.evaluate(() => window.scrollY > 0), 'Bottom-scroll setup failed.');
        if (activation === 'pointer') {
          await logo.click();
        } else {
          await logo.focus();
          await page.keyboard.press(activation);
        }
        await page.waitForFunction(() => window.scrollY === 0);
        const calls = await page.evaluate(() => window.__homeProbe.calls);
        check(calls.length === 1 && calls[0].top === 0, 'Logo must perform one document-top scroll.');
        check(calls[0].behavior === (reducedMotion === 'reduce' ? 'instant' : 'smooth'), 'Motion preference was ignored.');
        check(JSON.stringify(await state()) === JSON.stringify(baseline), 'Return-to-top changed URL, view, inputs, evidence, or document.');
        if (activation !== 'pointer') {
          check(await logo.evaluate(element => element === document.activeElement && getComputedStyle(element).outlineStyle !== 'none'), 'Keyboard focus must remain visible on the Logo.');
        }
        cases.push(`${reducedMotion}: ${activation} preserves URL/history/view/inputs/fresh evidence`);
      }
    }
    const mobileHeaders = [];
    for (const width of [390, 360]) {
      await page.setViewportSize({ width, height: 800 });
      const mobileHeader = await page.evaluate(() => {
        const wordmark = document.querySelector('[data-alvenx-home]');
        return {
          viewportWidth: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
          wordmarkWidth: wordmark.getBoundingClientRect().width,
          wordmarkImageWidth: wordmark.querySelector('img').getBoundingClientRect().width,
          tabsDisplay: getComputedStyle(document.querySelector('.site-header nav')).display,
          menuDisplay: getComputedStyle(document.querySelector('[data-view-menu]')).display,
        };
      });
      check(mobileHeader.scrollWidth === mobileHeader.viewportWidth, `${width}px viewport has horizontal overflow.`);
      check(mobileHeader.wordmarkWidth === 160 && mobileHeader.wordmarkImageWidth === 160, `${width}px viewport compressed the canonical wordmark.`);
      check(mobileHeader.tabsDisplay === 'none' && mobileHeader.menuDisplay === 'block', `${width}px viewport did not use the compact view menu.`);
      mobileHeaders.push({ requestedWidth: width, ...mobileHeader });
    }
    const menu = page.locator('[data-view-menu]');
    const summary = menu.locator('summary');
    await summary.focus();
    check(await summary.evaluate(element => element === document.activeElement && getComputedStyle(element).outlineStyle !== 'none'), 'Compact menu keyboard focus is not visible.');
    await summary.click();
    await menu.locator('[data-view="calibration"]').click();
    check(await page.locator('#calibration-view').isVisible(), 'Compact menu did not select Calibration.');
    await summary.click();
    await menu.locator('[data-view="learned"]').click();
    check(await page.locator('#learned-view').isVisible(), 'Compact menu did not select Learned-model study.');
    check(JSON.stringify(await state()) === JSON.stringify(baseline), 'Compact menu changed inputs, evidence, history, or document while restoring the selected view.');
    await summary.click();
    await page.keyboard.press('Escape');
    check(!(await menu.evaluate(element => element.open)) && await summary.evaluate(element => element === document.activeElement), 'Escape did not close the compact menu and restore focus.');
    cases.push('desktop header geometry and interaction states match the shared contract');
    cases.push('390px and 360px compact menus preserve the 160px wordmark without overflow');
    cases.push('compact menu switches views and closes with Escape');
    return { passed: cases.length, cases, preserved: baseline, desktopHeader, mobileHeaders };
  } finally {
    await page.evaluate(() => {
      window.scrollTo = window.__homeProbe.original;
      delete window.__homeProbe;
    });
  }
}
