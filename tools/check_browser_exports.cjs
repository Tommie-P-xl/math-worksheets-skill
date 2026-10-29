/* Exercise actual clipboard, file downloads and print CSS offline. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.MWS_PLAYWRIGHT_MODULE || 'playwright');

async function main() {
  const browser = await chromium.launch({headless: true, ...(process.env.MWS_BROWSER_CHANNEL ? {channel: process.env.MWS_BROWSER_CHANNEL} : {})});
  const out = process.env.MWS_EXPORT_DIR || fs.mkdtempSync(path.join(os.tmpdir(), 'mws-exports-'));
  fs.mkdirSync(out, {recursive: true});
  try {
    const context = await browser.newContext({viewport: {width: 1500, height: 1100}, offline: true, acceptDownloads: true});
    await context.addInitScript(() => {
      Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: async text => { window.copiedText = text; }}});
      window.print = () => { window.printRequested = true; };
    });
    const page = await context.newPage(), errors = [], network = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
    await page.goto(pathToFileURL(path.resolve(process.argv[2] || path.join(__dirname, '../docs/examples/bank-browser/browser.html'))).href);
    const questions = JSON.parse(await page.locator('#bank-data').textContent()).questions;
    await page.getByRole('button', {name: '详细展示', exact: true}).click();
    // Check every question's code export, including figures embedded in answers.
    for (const question of questions) {
      await page.getByRole('searchbox').fill(question.short_id);
      await page.getByRole('button', {name: '复制题干 Markdown', exact: true}).click();
      const stem = await page.evaluate(() => window.copiedText);
      assert.ok(stem.includes('## 题干'));
      assert.ok(!stem.includes('## 完整解答'));
      if (question.item.diagram?.code) assert.ok(stem.includes(question.item.diagram.code.trim()));
      await page.locator('.answers-panel > summary').click();
      await page.getByRole('button', {name: '复制答案 Markdown', exact: true}).click();
      const answer = await page.evaluate(() => window.copiedText);
      assert.ok(answer.includes('## 答案'));
      assert.ok(!answer.includes('## 题干'));
      assert.ok(!answer.includes('data:image/'), 'Saved drawings must export as code rather than raster data');
      for (const method of question.item.alternative_solutions || []) {
        assert.ok(answer.includes(method.title), 'Markdown omitted a saved solution method');
        assert.ok((await page.locator('.answer-body').innerText()).includes(method.title));
      }
      assert.ok(/\$[^$]+\$/.test(stem + answer));
    }
    // Prefer a question with both a primary TikZ image and an answer-only image.
    const question = questions.find(q => q.previews.length && q.content_images) || questions.find(q => q.previews.length) || questions[0];
    await page.getByRole('searchbox').fill(question.short_id);
    await page.locator('.answers-panel > summary').click();
    const controls = page.locator('.export-controls').first();
    const mdDownload = page.waitForEvent('download');
    await controls.getByRole('button', {name: '下载 题干.md', exact: true}).click();
    const md = await mdDownload;
    await md.saveAs(path.join(out, md.suggestedFilename()));
    assert.ok(fs.readFileSync(path.join(out, md.suggestedFilename()), 'utf8').includes('## 题干'));
    const results = [];
    for (const scope of ['stem', 'answer', 'both']) {
      await controls.locator('select').selectOption(scope);
      await controls.getByRole('button', {name: '导出 PDF', exact: true}).click();
      await page.waitForFunction(() => document.getElementById('export-preview-status').textContent === '');
      const headings = await page.locator('#export-sheet h2, #export-sheet h3').allTextContents();
      assert.equal(headings.includes('题干'), scope !== 'answer');
      assert.equal(headings.includes('答案'), scope !== 'stem');
      for (const method of question.item.alternative_solutions || []) {
        assert.equal(headings.some(heading => heading.includes(method.title)), scope !== 'stem', 'Visual export must include every selected solution method');
      }
      await page.getByRole('button', {name: '打印 / 保存 PDF', exact: true}).click();
      assert.equal(await page.evaluate(() => window.printRequested), true);
      await page.emulateMedia({media: 'print'});
      assert.equal(await page.locator('.wrap').isVisible(), false);
      assert.equal(await page.locator('#export-sheet').isVisible(), true);
      assert.equal(await page.locator('.export-preview-head').isVisible(), false);
      const pdf = path.join(out, question.short_id + '-' + scope + '.pdf');
      await page.pdf({path: pdf, printBackground: true, preferCSSPageSize: true});
      assert.ok(fs.readFileSync(pdf).subarray(0, 4).equals(Buffer.from('%PDF')));
      await page.emulateMedia({media: 'screen'});
      await page.getByRole('button', {name: '关闭预览', exact: true}).click();
      // Mobile export must use the same legible full-width PNG as desktop.
      if (scope === 'both') await page.setViewportSize({width: 390, height: 844});
      const pending = page.waitForEvent('download', {timeout: 60000});
      await controls.getByRole('button', {name: '导出 PNG', exact: true}).click();
      const download = await pending, png = path.join(out, download.suggestedFilename());
      await download.saveAs(png);
      const bytes = fs.readFileSync(png);
      assert.equal(bytes.subarray(1, 4).toString(), 'PNG');
      assert.equal(bytes.readUInt32BE(16), 1520);
      assert.ok(bytes.readUInt32BE(20) > 200);
      // Ensure the result contains actual rendered content rather than a blank canvas.
      const colored = await page.evaluate(async url => {
        const image = new Image(); image.src = url; await image.decode();
        const canvas = document.createElement('canvas'); canvas.width = image.width; canvas.height = image.height;
        const ctx = canvas.getContext('2d'); ctx.drawImage(image, 0, 0);
        const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        let count = 0; for (let i = 0; i < pixels.length; i += 4) if (pixels[i] < 180 && pixels[i + 1] < 180 && pixels[i + 2] < 180 && pixels[i + 3]) count++;
        return count;
      }, 'data:image/png;base64,' + bytes.toString('base64'));
      assert.ok(colored > 1000, 'PNG is blank or missing its text');
      results.push({scope, width: 1520, height: bytes.readUInt32BE(20), inkPixels: colored});
      await page.getByRole('button', {name: '关闭预览', exact: true}).click();
    }
    await page.getByRole('button', {name: '摘要卡片', exact: true}).click();
    assert.equal(await page.locator('.cards .export-controls').count(), 0);
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    console.log(JSON.stringify({markdownQuestions: questions.length, pdfAndPng: results, offline: true, out}));
  } finally {
    await browser.close();
    if (!process.env.MWS_EXPORT_DIR) fs.rmSync(out, {recursive: true, force: true});
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
