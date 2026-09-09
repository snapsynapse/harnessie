const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const puppeteer = require('/Users/snap/.agents/skills/a11y-audit/deps/node_modules/puppeteer');

const [baseUrl, scanPath, outputPath] = process.argv.slice(2);
if (!baseUrl || !scanPath || !outputPath) {
  throw new Error('usage: review-driver.cjs BASE_URL SCAN_JSON OUTPUT_JSON');
}

function rgb(value) {
  const parts = value.match(/[\d.]+/g).map(Number);
  return parts.slice(0, 3);
}

function luminance(value) {
  const channels = rgb(value).map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(first, second) {
  const a = luminance(first);
  const b = luminance(second);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

function minimumContrast(fontSize, fontWeight) {
  const pixels = Number.parseFloat(fontSize);
  const weight = Number.parseInt(fontWeight, 10) || (fontWeight === 'bold' ? 700 : 400);
  return pixels >= 24 || (pixels >= 18.6667 && weight >= 700) ? 3 : 4.5;
}

async function observeElement(page, selector) {
  const matches = await page.$$(selector);
  assert.equal(matches.length, 1, `${selector}: expected one element, found ${matches.length}`);
  const element = matches[0];
  await element.evaluate((node) => {
    const wrapper = node.closest('.table-wrap');
    if (!wrapper) return;
    const nodeRect = node.getBoundingClientRect();
    const wrapperRect = wrapper.getBoundingClientRect();
    wrapper.scrollLeft += nodeRect.left - wrapperRect.left - 12;
  });
  await new Promise((resolve) => setTimeout(resolve, 40));
  return element.evaluate((node) => {
    const style = getComputedStyle(node);
    let backgroundNode = node;
    let background = null;
    while (backgroundNode) {
      const candidate = getComputedStyle(backgroundNode).backgroundColor;
      if (candidate !== 'rgba(0, 0, 0, 0)' && candidate !== 'transparent') {
        background = candidate;
        break;
      }
      backgroundNode = backgroundNode.parentElement;
    }
    const wrapper = node.closest('.table-wrap');
    const nodeRect = node.getBoundingClientRect();
    const wrapperRect = wrapper ? wrapper.getBoundingClientRect() : null;
    const visibleWidth = wrapperRect
      ? Math.max(0, Math.min(nodeRect.right, wrapperRect.right) - Math.max(nodeRect.left, wrapperRect.left))
      : nodeRect.width;
    return {
      text: node.textContent.trim(),
      color: style.color,
      background,
      fontSize: style.fontSize,
      fontWeight: style.fontWeight,
      textDecorationLine: style.textDecorationLine,
      bounds: {
        left: nodeRect.left,
        right: nodeRect.right,
        width: nodeRect.width,
      },
      wrapper: wrapperRect ? {
        left: wrapperRect.left,
        right: wrapperRect.right,
        width: wrapperRect.width,
        clientWidth: wrapper.clientWidth,
        scrollWidth: wrapper.scrollWidth,
        scrollLeft: wrapper.scrollLeft,
        tabindex: wrapper.tabIndex,
      } : null,
      visibleFraction: nodeRect.width ? visibleWidth / nodeRect.width : 1,
    };
  });
}

async function keyboardChecks(page, base, results) {
  const targets = [
    ['quickstart.html', 'pre:nth-child(19)'],
    ['agent-file-ownership.html', 'pre:nth-child(24)'],
    ['ringer.html', 'pre:nth-child(14)'],
    ['threat-model.html', '.table-wrap'],
  ];
  for (const width of [1280, 375]) {
    for (const [route, target] of targets) {
      await page.setViewport({ width, height: 800 });
      await page.goto(`${base}/${route}`, { waitUntil: 'networkidle0' });
      let tabs = 0;
      let reached = false;
      while (tabs < 180) {
        await page.keyboard.press('Tab');
        tabs += 1;
        reached = await page.evaluate((query) => document.activeElement.matches(query), target);
        if (reached) break;
      }
      assert(reached, `${route} ${width}: Tab did not reach ${target}`);
      const before = await page.$eval(target, (node) => ({
        scrollLeft: node.scrollLeft,
        overflow: node.scrollWidth - node.clientWidth,
        outlineStyle: getComputedStyle(node).outlineStyle,
        outlineWidth: getComputedStyle(node).outlineWidth,
        text: node.textContent,
      }));
      assert(before.overflow > 0, `${route} ${width}: target did not overflow`);
      assert.equal(before.outlineStyle, 'solid');
      assert(Number.parseFloat(before.outlineWidth) >= 2);
      await page.keyboard.down('ArrowRight');
      await new Promise((resolve) => setTimeout(resolve, 400));
      await page.keyboard.up('ArrowRight');
      await new Promise((resolve) => setTimeout(resolve, 150));
      const after = await page.$eval(target, (node) => ({ scrollLeft: node.scrollLeft, text: node.textContent }));
      assert(after.scrollLeft > before.scrollLeft, `${route} ${width}: ArrowRight did not scroll`);
      assert.equal(after.text, before.text);
      await page.keyboard.press('Tab');
      const tabExited = await page.evaluate((query) => !document.activeElement.matches(query), target);
      assert(tabExited);
      await page.keyboard.down('Shift');
      await page.keyboard.press('Tab');
      await page.keyboard.up('Shift');
      assert(await page.evaluate((query) => document.activeElement.matches(query), target));
      await page.keyboard.down('Shift');
      await page.keyboard.press('Tab');
      await page.keyboard.up('Shift');
      const reverseExited = await page.evaluate((query) => !document.activeElement.matches(query), target);
      assert(reverseExited);
      results.push({
        route,
        width,
        target,
        tabs,
        overflow: before.overflow,
        scrollBefore: before.scrollLeft,
        scrollAfter: after.scrollLeft,
        visibleFocus: true,
        tabExited,
        reverseExited,
        textPreserved: true,
      });
    }
  }
}

async function motionChecks(page, base) {
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'no-preference' }]);
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`${base}/`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('.video-toggle', { visible: true });
  const initial = await page.$eval('.hero-clip', (video) => ({ paused: video.paused, muted: video.muted }));
  const initialLabel = await page.$eval('.video-toggle', (button) => button.getAttribute('aria-label'));
  await page.click('.video-toggle');
  await new Promise((resolve) => setTimeout(resolve, 100));
  const paused = await page.$eval('.hero-clip', (video) => video.paused);
  const pausedLabel = await page.$eval('.video-toggle', (button) => button.getAttribute('aria-label'));
  await page.click('.video-toggle');
  await new Promise((resolve) => setTimeout(resolve, 100));
  const resumed = await page.$eval('.hero-clip', (video) => !video.paused);
  const resumedLabel = await page.$eval('.video-toggle', (button) => button.getAttribute('aria-label'));
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.reload({ waitUntil: 'networkidle0' });
  const reduced = await page.$eval('.hero-clip', (video) => ({ paused: video.paused, autoplay: video.hasAttribute('autoplay') }));
  assert.equal(initial.muted, true);
  assert.equal(initialLabel, initial.paused ? 'Play the animation' : 'Pause the animation');
  assert.equal(paused, true);
  assert.equal(pausedLabel, 'Play the animation');
  assert.equal(resumed, true);
  assert.equal(resumedLabel, 'Pause the animation');
  assert.equal(reduced.paused, true);
  assert.equal(reduced.autoplay, false);
  return { initial, initialLabel, paused, pausedLabel, resumed, resumedLabel, reduced };
}

(async () => {
  const scan = JSON.parse(fs.readFileSync(scanPath));
  const browser = await puppeteer.launch({ headless: true });
  const results = {
    reviewedAt: new Date().toISOString(),
    sourceScan: scanPath,
    axeVersion: scan.axe_version,
    browser: await browser.version(),
    viewports: [1280, 640, 375],
    viewportNotes: {
      1280: 'normal desktop width',
      640: 'reflow proxy for a 1280 CSS-pixel viewport at 200 percent zoom; not a human browser-zoom test',
      375: 'narrow layout',
    },
    contrast: [],
    links: [],
    keyboard: [],
    motion: null,
  };
  try {
    const page = await browser.newPage();
    const pageSpecs = [
      ['guide.html', (url) => url.endsWith('/guide.html')],
      ['threat-model.html', (url) => url.endsWith('/threat-model.html')],
    ];
    for (const [route, matchesRoute] of pageSpecs) {
      const scanResult = scan.results.find((entry) => matchesRoute(entry.url));
      assert(scanResult, `${route}: scan result missing`);
      const contrastRule = scanResult.axe.incomplete.find((entry) => entry.id === 'color-contrast');
      const contrastSelectors = contrastRule ? contrastRule.nodes.map((node) => node.target[0]) : [];
      const linkRule = scanResult.axe.incomplete.find((entry) => entry.id === 'link-in-text-block');
      const linkSelectors = linkRule ? linkRule.nodes.map((node) => node.target[0]) : [];
      for (const width of results.viewports) {
        await page.setViewport({ width, height: 900 });
        await page.goto(`${baseUrl}/${route}`, { waitUntil: 'networkidle0' });
        for (const selector of contrastSelectors) {
          const observed = await observeElement(page, selector);
          const ratio = contrast(observed.color, observed.background);
          const minimum = minimumContrast(observed.fontSize, observed.fontWeight);
          results.contrast.push({ route, width, selector, ...observed, ratio, minimum, passes: ratio >= minimum });
        }
        for (const selector of linkSelectors) {
          const observed = await observeElement(page, selector);
          const surrounding = await page.$eval(selector, (node) => getComputedStyle(node.parentElement).color);
          const colorDifferenceRatio = contrast(observed.color, surrounding);
          const persistentUnderline = observed.textDecorationLine.split(' ').includes('underline');
          results.links.push({
            route,
            width,
            selector,
            text: observed.text,
            color: observed.color,
            surrounding,
            background: observed.background,
            colorDifferenceRatio,
            persistentUnderline,
            passesNonColorCue: persistentUnderline || colorDifferenceRatio >= 3,
          });
        }
        if (route === 'guide.html' || route === 'threat-model.html') {
          const selector = route === 'guide.html' ? '.table-wrap[aria-labelledby="the-cli"]' : '.table-wrap';
          const wrapper = await page.$(selector);
          assert(wrapper, `${route}: table wrapper missing`);
          await wrapper.evaluate((node) => { node.scrollLeft = node.scrollWidth; node.focus(); });
          await wrapper.screenshot({ path: path.join(path.dirname(outputPath), `${route.replace('.html', '')}-${width}-right.png`) });
        }
      }
    }
    await keyboardChecks(page, baseUrl, results.keyboard);
    results.motion = await motionChecks(page, baseUrl);
    assert(results.contrast.every((entry) => entry.passes), 'one or more measured text contrast targets failed');
    const grouped = new Map();
    for (const entry of results.contrast) {
      const key = `${entry.route}\u0000${entry.selector}`;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(entry);
    }
    results.dispositions = Array.from(grouped.values()).map((entries, index) => ({
      id: `M${String(index + 1).padStart(3, '0')}`,
      route: entries[0].route,
      selector: entries[0].selector,
      status: 'resolved_measured_contrast',
      minimumObservedRatio: Math.min(...entries.map((entry) => entry.ratio)),
      requiredRatio: Math.max(...entries.map((entry) => entry.minimum)),
      widths: entries.map((entry) => ({
        width: entry.width,
        ratio: entry.ratio,
        minimum: entry.minimum,
        color: entry.color,
        background: entry.background,
        visibleFraction: entry.visibleFraction,
        scrollLeft: entry.wrapper.scrollLeft,
        scrollWidth: entry.wrapper.scrollWidth,
        clientWidth: entry.wrapper.clientWidth,
      })),
    }));
    fs.writeFileSync(outputPath, `${JSON.stringify(results, null, 2)}\n`);
    const linkFailures = results.links.filter((entry) => !entry.passesNonColorCue).length;
    console.log(`PASS: ${results.contrast.length} contrast measurements and ${results.keyboard.length} keyboard cases; ${linkFailures} link-cue failures`);
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
