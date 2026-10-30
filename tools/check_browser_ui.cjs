/* Offline browser regression check; Playwright is a maintainer/CI dependency. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.MWS_PLAYWRIGHT_MODULE || 'playwright');

function walk(nodes) {
  return (nodes || []).flatMap(node => [node, ...walk(node.children), ...(node.items || []).flatMap(walk)]);
}

function questionNodes(question) {
  return [...['stem', 'answer', 'solution', 'answer_extra'].flatMap(field => walk(question.content[field])),
    ...(question.content.alternative_solutions || []).flatMap(method => walk(method.nodes))];
}

async function main() {
  const options = {headless: true};
  if (process.env.MWS_BROWSER_CHANNEL) options.channel = process.env.MWS_BROWSER_CHANNEL;
  const browser = await chromium.launch(options);
  try {
    const context = await browser.newContext({viewport: {width: 1600, height: 1100}, offline: true});
    await context.addInitScript(() => Object.defineProperty(navigator, 'clipboard', {
      configurable: true, value: {writeText: async text => { window.copiedText = text; }}
    }));
    const page = await context.newPage(), errors = [], network = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
    const file = path.resolve(process.argv[2] || path.join(__dirname, '../docs/examples/bank-browser/browser.html'));
    await page.goto(pathToFileURL(file).href);
    const bank = JSON.parse(await page.locator('#bank-data').textContent());
    assert.ok(bank.questions.length >= 3);
    assert.deepEqual(bank.questions.map(question => question.short_id), bank.questions.map((_, index) => 'Q' + (index + 1)));
    assert.deepEqual(bank.questions.flatMap(question => [question.preview_note, ...question.content_notes.map(note => note.note)]).filter(Boolean), [], 'The test snapshot must have complete figure previews');
    assert.equal(await page.locator('#view-summary').getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('.cards img').count(), 0);
    assert.equal(await page.locator('.cards .stem, .cards .answers-panel').count(), 0);
    assert.equal(await page.locator('#cards').evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length), 3);
    const chosen = [bank.questions[0], bank.questions[2]];
    for (const question of chosen) await page.getByRole('checkbox', {name: '选择参考题 ' + question.short_id, exact: true}).check();
    await page.getByRole('button', {name: '复制题号', exact: true}).click();
    assert.equal(await page.evaluate(() => window.copiedText), chosen.map(question => question.short_id).join('、'));
    await page.getByRole('searchbox').fill(chosen[0].short_id);
    assert.equal(await page.locator('.card').count(), 1);
    assert.equal(await page.getByRole('checkbox', {name: '选择参考题 ' + chosen[0].short_id, exact: true}).isChecked(), true);
    await page.getByRole('button', {name: '重置筛选', exact: true}).click();
    await page.getByRole('searchbox').fill('Q999999');
    assert.ok((await page.locator('.empty').innerText()).includes('当前题库没有 Q999999'));
    assert.ok((await page.locator('.empty').innerText()).includes('连续编号'));
    await page.getByRole('button', {name: '重置筛选', exact: true}).click();
    if (process.env.MWS_SCREENSHOT_DIR) {
      fs.mkdirSync(process.env.MWS_SCREENSHOT_DIR, {recursive: true});
      await page.setViewportSize({width: 1600, height: 2000});
      await page.locator('.wrap').screenshot({path: path.join(process.env.MWS_SCREENSHOT_DIR, 'browser.png')});
      await page.setViewportSize({width: 1600, height: 1100});
    }
    await page.getByRole('button', {name: '详细展示', exact: true}).click();
    assert.equal(await page.locator('#cards').evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length), 1);
    let images = 0, formulas = 0, lists = 0;
    const pageCount = Math.ceil(bank.questions.length / 12);
    for (let index = 0; index < pageCount; index++) {
      const answers = page.locator('.answers-panel > summary');
      for (let question = 0; question < await answers.count(); question++) await answers.nth(question).click();
      await page.waitForFunction(() => document.querySelectorAll('.answer-body').length === document.querySelectorAll('.card').length);
      assert.equal(await page.locator('.math-error').count(), 0);
      assert.equal(await page.locator('.math-inline, .math-display, .katex-display').evaluateAll(elements => elements.filter(element => ['auto', 'scroll'].includes(getComputedStyle(element).overflowX)).length), 0, 'Formulas must not create scrollbar widgets');
      assert.ok(await page.locator('.cards img').evaluateAll(images => images.every(image => image.getBoundingClientRect().width <= 288 && image.getBoundingClientRect().height <= 224)), 'Default figures should stay near worksheet text scale');
      assert.ok(!(await page.locator('.cards').innerText()).includes('图形条件：'));
      const sourceText = await page.locator('.cards').evaluate(element => {
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        let text = '', next;
        while ((next = walker.nextNode())) if (!next.parentElement.closest('.katex')) text += next.textContent;
        return text;
      });
      assert.ok(!/\\(?:begin|end)\{(?:enumerate|tikzpicture|minipage)\}|\\(?:item|textbf|ans|par)\b/.test(sourceText), 'Raw LaTeX layout leaked into the page');
      images += await page.locator('.cards img').count();
      formulas += await page.locator('.cards .katex').count();
      lists += await page.locator('.cards .tex-list').count();
      await page.locator('.cards img').evaluateAll(async elements => {
        for (const image of elements) image.loading = 'eager';
        await Promise.all(elements.map(image => image.decode()));
        if (elements.some(image => !image.naturalWidth || !image.naturalHeight)) throw Error('Empty preview image');
      });
      if (index < pageCount - 1) await page.getByRole('button', {name: '下一页', exact: true}).click();
    }
    const expectedImages = bank.questions.reduce((total, question) => total + (question.previews.length || Number(Boolean(question.preview))) + questionNodes(question).filter(node => node.type === 'figure' && node.image).length, 0);
    const expectedLists = bank.questions.reduce((total, question) => total + questionNodes(question).filter(node => node.type === 'list').length, 0);
    assert.equal(images, expectedImages);
    assert.equal(lists, expectedLists);
    assert.ok(formulas > 5);
    await page.getByRole('searchbox').fill(chosen[1].short_id);
    await page.locator('.answers-panel > summary').click();
    await page.locator('.answer-body').waitFor();
    const zoom = page.locator('.figure-button').first();
    if (await zoom.count()) {
      await zoom.click();
      assert.equal(await page.locator('#figure-dialog').isVisible(), true);
      await page.locator('#large-figure').evaluate(image => image.decode());
      await page.keyboard.press('Escape');
    }
    if (process.env.MWS_SCREENSHOT_DIR) {
      await page.setViewportSize({width: 1600, height: 2600});
      await page.evaluate(() => { document.activeElement.blur(); scrollTo(0, 0); });
      await page.locator('.wrap').screenshot({path: path.join(process.env.MWS_SCREENSHOT_DIR, 'browser-detail.png')});
    }
    await page.setViewportSize({width: 390, height: 844});
    await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    if (await zoom.count()) {
      await zoom.click();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.getByRole('button', {name: '关闭', exact: true}).click();
    }
    await page.getByRole('button', {name: '摘要卡片', exact: true}).click();
    assert.equal(await page.locator('.cards img, .cards .answers-panel, .cards .figure-button').count(), 0);
    assert.equal(await page.locator('#figure-dialog').isVisible(), false);
    assert.equal(await page.locator('#large-figure').getAttribute('src'), null);
    await page.getByRole('button', {name: '复制参考提示词', exact: true}).click();
    assert.ok((await page.evaluate(() => window.copiedText)).includes(chosen[0].short_id + '、' + chosen[1].short_id));
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    console.log(JSON.stringify({questions: bank.questions.length, summaryColumns: 3, detailColumns: 1, images, formulas, lists, answersRendered: true, summaryImages: 0, offline: true, mobileOverflow: false}));
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
