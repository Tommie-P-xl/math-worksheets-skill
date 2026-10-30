'use strict';
const bank = JSON.parse(document.getElementById('bank-data').textContent);
const $ = id => document.getElementById(id);
const selected = new Map();
const filters = [...document.querySelectorAll('aside select')];
const pageSize = 12;
let page = 1, visible = [], view = 'summary';
try { if (localStorage.getItem('mws-bank-view') === 'detail') view = 'detail'; } catch {}
$('demo-notice').hidden = !bank.demo;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function formula(parent, value, display) {
  const element = node(display ? 'div' : 'span', undefined, display ? 'math-display' : 'math-inline');
  try {
    katex.render(value, element, {
      displayMode: Boolean(display), throwOnError: true, trust: false,
      strict: 'ignore', maxExpand: 1000, maxSize: 10,
      macros: { '\\ans': '\\boxed{#1}', '\\ansblank': '\\underline{\\quad}' }
    });
  } catch (error) {
    element.textContent = value;
    element.classList.add('math-error');
    element.title = '公式排版失败：' + error.message;
  }
  parent.append(element);
}

function figures(images, question, role, firstIndex = 1) {
  const group = node('div', undefined, 'figures');
  if (view !== 'detail') return group;
  images.forEach((source, index) => {
    const caption = question.short_id + ' ' + role + (index + firstIndex);
    const button = node('button', undefined, 'figure-button');
    const image = node('img', undefined, 'figure');
    button.type = 'button';
    button.setAttribute('aria-label', '放大 ' + caption);
    image.src = source;
    image.alt = caption;
    image.loading = 'lazy';
    button.append(image, node('span', role + (index + firstIndex) + ' · 点击放大'));
    button.addEventListener('click', () => {
      if (view !== 'detail') return;
      $('large-figure').src = source;
      $('large-figure').alt = caption;
      $('figure-title').textContent = caption;
      $('figure-dialog').showModal();
    });
    group.append(button);
  });
  return group;
}

function content(parent, nodes, question, role) {
  for (const item of nodes || []) {
    if (item.type === 'math') formula(parent, item.text, item.display);
    else if (item.type === 'text') parent.append(document.createTextNode(item.text));
    else if (item.type === 'break') {
      if (parent.lastChild?.nodeName !== 'BR') parent.append(node('br'));
    } else if (item.type === 'figure') {
      if (view !== 'detail') continue;
      if (item.image) parent.append(figures([item.image], question, role, item.index));
      else if (item.note) parent.append(node('p', item.note, 'diagram-note'));
    } else if (item.type === 'list') {
      const list = node(item.style === 'bullet' ? 'ul' : 'ol', undefined, 'tex-list');
      item.items.forEach((children, index) => {
        const entry = node('li');
        const number = item.style === 'bullet' ? '•' : item.style === 'circled' && index < 20 ? String.fromCodePoint(0x2460 + index) : '（' + (index + 1) + '）';
        entry.append(node('span', number, 'list-number'));
        const body = node('div');
        content(body, children, question, role);
        entry.append(body);
        list.append(entry);
      });
      parent.append(list);
    } else {
      const tag = { strong: 'strong', em: 'em', underline: 'u', group: 'span', paragraph: 'p' }[item.type];
      if (!tag) continue;
      const group = node(tag);
      content(group, item.children, question, role);
      parent.append(group);
    }
  }
}

function field(parent, title, nodes, question, role) {
  if (!nodes?.length) return;
  parent.append(node('h3', title));
  const body = node('div', undefined, 'content' + (role === '题图' ? '' : ' answer-content'));
  content(body, nodes, question, role);
  parent.append(body);
}

// Use the same content tree for display and export; mathematical source never
// passes through innerHTML, clipboard HTML, or the rendered KaTeX DOM.
function markdownText(value) {
  return value.replace(/[\\`*_{}\[\]<>$]/g, '\\$&');
}

function codeBlock(code, format) {
  const fence = '~'.repeat(Math.max(3, ...(code.match(/~+/g) || []).map(run => run.length + 1)));
  return '\n\n' + fence + (format || 'text') + '\n' + code.trim() + '\n' + fence + '\n\n';
}

function markdownNodes(nodes) {
  return (nodes || []).map(item => {
    if (item.type === 'text') return markdownText(item.text);
    if (item.type === 'math') return item.display ? '\n\n$$\n' + item.text.trim() + '\n$$\n\n' : '$' + item.text.trim() + '$';
    if (item.type === 'break') return '\n\n';
    if (item.type === 'figure') return item.code ? codeBlock(item.code, item.format) : item.image ? '\n\n![题图](' + item.image + ')\n\n' : '';
    if (item.type === 'list') return '\n\n' + item.items.map((children, index) => {
      const prefix = item.style === 'bullet' ? '- ' : (index + 1) + '. ';
      return prefix + markdownNodes(children).trim().replace(/\n/g, '\n' + ' '.repeat(prefix.length));
    }).join('\n') + '\n\n';
    const text = markdownNodes(item.children);
    if (item.type === 'paragraph') return '\n\n' + text.trim() + '\n\n';
    return item.type === 'strong' ? '**' + text + '**' : item.type === 'em' ? '*' + text + '*' : text;
  }).join('');
}

function markdown(question, scope) {
  let result = '# ' + question.short_id + ' ' + markdownNodes(question.content.title).trim() + '\n\n';
  if (scope !== 'answer') {
    result += '## 题干\n\n' + markdownNodes(question.content.stem);
    if (question.item.diagram?.code) result += codeBlock(question.item.diagram.code, question.item.diagram.format);
  }
  if (scope !== 'stem') {
    for (const [name, label] of [['answer', '答案'], ['solution', question.content.alternative_solutions?.length ? '解法一' : '完整解答']]) {
      if (question.content[name]?.length) result += '\n\n## ' + label + '\n\n' + markdownNodes(question.content[name]);
    }
    for (const [index, method] of (question.content.alternative_solutions || []).entries()) {
      result += '\n\n## ' + markdownText(methodTitle(index + 2, method.title)) + '\n\n' + markdownNodes(method.nodes);
    }
    if (question.content.answer_extra?.length) result += '\n\n## 答案补充\n\n' + markdownNodes(question.content.answer_extra);
  }
  return result.trim() + '\n';
}

function download(url, filename) {
  const link = node('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
}

function fitFormulas(root = document) {
  for (const element of root.querySelectorAll('.math-inline,.math-display')) {
    const math = element.querySelector('.katex'), html = element.querySelector('.katex-html');
    if (!math || !html) continue;
    math.style.fontSize = '';
    const container = element.closest('.content, h2, .summary') || element.parentElement;
    const available = container.clientWidth - 2;
    const width = html.getBoundingClientRect().width;
    if (available > 0 && width > available) math.style.fontSize = (parseFloat(getComputedStyle(math).fontSize) * available / width) + 'px';
  }
}

function fillAnswers(body, question) {
  field(body, '答案', question.content.answer, question, '答案图');
  const methods = question.content.alternative_solutions || [];
  field(body, methods.length ? '解法一' : '完整解答', question.content.solution, question, '解法一图');
  for (const [index, method] of methods.entries()) {
    const section = node('section', undefined, 'solution-method');
    field(section, methodTitle(index + 2, method.title), method.nodes, question, '解法' + (index + 2) + '图');
    body.append(section);
  }
  field(body, '答案补充', question.content.answer_extra, question, '补充图');
}

function methodTitle(number, title) {
  const chinese = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十'];
  return '解法' + (chinese[number - 1] || number) + ' · ' + title;
}

async function prepareExport(question, scope) {
  const sheet = $('export-sheet');
  sheet.replaceChildren();
  const title = node('h1');
  title.append(node('span', question.short_id + ' '));
  content(title, question.content.title, question, '标题图');
  sheet.append(title);
  if (scope !== 'answer') {
    field(sheet, '题干', question.content.stem, question, '题图');
    const images = question.previews?.length ? question.previews : question.preview ? [question.preview] : [];
    if (images.length) sheet.append(figures(images, question, '题图'));
    else if (question.preview_note) sheet.append(node('p', question.preview_note, 'diagram-note'));
  }
  if (scope !== 'stem') fillAnswers(sheet, question);
  for (const image of sheet.querySelectorAll('img')) image.loading = 'eager';
  $('export-preview-status').textContent = '正在准备公式与图片…';
  $('export-dialog').dataset.previousTitle = document.title;
  document.title = question.short_id + '-' + scope;
  $('export-dialog').showModal();
  await document.fonts.ready;
  await Promise.all([...sheet.querySelectorAll('img')].map(image => image.decode()));
  fitFormulas(sheet);
  $('export-preview-status').textContent = '';
  return sheet;
}

function exportTools(question, scope) {
  const block = node('div', undefined, 'export-controls');
  const tools = node('div', undefined, 'export-tools');
  const label = scope === 'stem' ? '题干' : '答案';
  tools.append(node('strong', label));
  const feedback = node('p', '', 'export-feedback');
  feedback.setAttribute('role', 'status');
  function button(text, action) {
    const control = node('button', text);
    control.type = 'button';
    control.addEventListener('click', async () => {
      control.disabled = true;
      feedback.textContent = '';
      try { await action(); }
      catch (error) {
        feedback.textContent = '导出未完成：' + (error.message || '请重试');
        if ($('export-dialog').open) $('export-preview-status').textContent = feedback.textContent;
      }
      finally { control.disabled = false; }
    });
    tools.append(control);
  }
  button('复制' + label + ' Markdown', async () => {
    const text = markdown(question, scope);
    const copied = await copy(text);
    feedback.textContent = copied ? label + ' Markdown 已复制。' : '请在下方文本框手动复制 Markdown。';
    block.querySelector('.export-copy')?.remove();
    if (!copied) {
      const area = node('textarea', text, 'export-copy');
      area.readOnly = true;
      area.setAttribute('aria-label', label + ' Markdown 内容');
      block.append(area);
      area.focus(); area.select();
    }
  });
  button('下载 ' + label + '.md', () => {
    const url = URL.createObjectURL(new Blob([markdown(question, scope)], {type: 'text/markdown;charset=utf-8'}));
    download(url, question.short_id + '-' + scope + '.md');
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    feedback.textContent = 'Markdown 文件已下载。';
  });
  const range = node('select');
  range.setAttribute('aria-label', question.short_id + ' ' + label + '导出范围');
  for (const [value, text] of [['stem', '仅题干'], ['answer', '仅答案'], ['both', '题干和答案']]) {
    const option = node('option', text); option.value = value; range.append(option);
  }
  range.value = scope;
  tools.append(range);
  button('导出 PDF', async () => {
    await prepareExport(question, range.value);
    feedback.textContent = '预览已打开，点击“打印 / 保存 PDF”。';
  });
  button('导出 PNG', async () => {
    const sheet = await prepareExport(question, range.value);
    $('export-preview-status').textContent = '正在生成 PNG…';
    // Freeze the export width so mobile exports stay as legible as desktop ones.
    const fontEmbedCSS = [...document.styleSheets[0].cssRules].filter(rule => rule.type === CSSRule.FONT_FACE_RULE).map(rule => rule.cssText).join('\n');
    sheet.style.width = '760px'; sheet.style.maxWidth = 'none';
    fitFormulas(sheet);
    let url;
    try {
      url = await htmlToImage.toPng(sheet, {backgroundColor: '#ffffff', pixelRatio: 2, width: 760, fontEmbedCSS});
    } finally {
      sheet.style.width = ''; sheet.style.maxWidth = '';
      fitFormulas(sheet);
    }
    download(url, question.short_id + '-' + range.value + '.png');
    $('export-preview-status').textContent = 'PNG 已下载。可关闭预览继续浏览。';
    feedback.textContent = 'PNG 已下载。';
  });
  block.append(tools, feedback);
  return block;
}

function detail(parent, title, value) {
  if (value === undefined || value === null || value === '') return;
  parent.append(node('h3', title), node('p', typeof value === 'string' ? value : JSON.stringify(value, null, 2)));
}

function metadata(question) {
  const item = question.item, panel = node('details', undefined, 'metadata-panel');
  panel.append(node('summary', '题目信息与来源'));
  const body = node('div', undefined, 'detail-body');
  const labels = { knowledge_span: '知识跨度', method_visibility: '方法显隐', calculation_load: '计算负荷', case_burden: '分类讨论', scaffolding: '提示与支架' };
  for (const [key, label] of Object.entries(labels)) detail(body, label, item.demand[key]);
  detail(body, '难度依据', item.demand.difficulty.reason);
  detail(body, '作答证据', item.demand.difficulty.evidence);
  detail(body, '验证记录', item.verification.notes);
  detail(body, '来源记录', item.sources.length ? item.sources : '无附加来源记录');
  detail(body, '修订信息', 'r' + question.revision + ' · ' + question.updated);
  detail(body, '内部 ID', item.id);
  panel.append(body);
  return panel;
}

function card(question) {
  const item = question.item;
  const article = node('article', undefined, 'card' + (selected.has(question.short_id) ? ' chosen' : ''));
  article.dataset.id = question.short_id;
  const top = node('div', undefined, 'card-top');
  const label = node('label', undefined, 'pick');
  const checkbox = node('input');
  checkbox.type = 'checkbox';
  checkbox.checked = selected.has(question.short_id);
  checkbox.setAttribute('aria-label', '选择参考题 ' + question.short_id);
  label.append(checkbox, node('span', '选作参考'));
  top.append(node('span', question.short_id, 'number'), label);
  const title = node('h2');
  content(title, question.content.title, question, '标题图');
  article.append(top, title);
  checkbox.addEventListener('change', () => {
    if (checkbox.checked && selected.size >= bank.limit) {
      checkbox.checked = false;
      $('status').textContent = '最多选择 ' + bank.limit + ' 道参考题（命题指南也计入 AI 的参考总上限）。';
      return;
    }
    if (checkbox.checked) selected.set(question.short_id, question);
    else selected.delete(question.short_id);
    article.classList.toggle('chosen', checkbox.checked);
    updateSelection();
  });
  const badges = node('div', undefined, 'badges');
  for (const tag of new Set([...item.tags.stages, ...item.tags.grades, ...item.tags.topics, ...item.tags.types, ...item.tags.methods])) badges.append(node('span', tag, 'badge'));
  article.append(badges);
  const difficulty = item.demand.difficulty;
  if (view === 'summary') {
    const summary = node('div', undefined, 'summary');
    content(summary, question.content.summary, question, '摘要图');
    article.append(summary);
    const button = node('button', '查看详情', 'show-detail');
    button.type = 'button';
    button.addEventListener('click', () => setView('detail', question.short_id));
    article.append(button);
  } else {
    article.append(exportTools(question, 'stem'));
    const stem = node('div', undefined, 'content stem');
    content(stem, question.content.stem, question, '题图');
    article.append(stem);
    const images = question.previews?.length ? question.previews : question.preview ? [question.preview] : [];
    if (images.length) article.append(figures(images, question, '题图'));
    else if (question.preview_note) article.append(node('p', question.preview_note, 'diagram-note'));
    const answers = node('details', undefined, 'answers-panel');
    answers.append(node('summary', '查看答案与完整解答'));
    let loaded = false;
    answers.addEventListener('toggle', () => {
      if (!answers.open || loaded || view !== 'detail') return;
      loaded = true;
      const body = node('div', undefined, 'answer-body');
      body.append(exportTools(question, 'answer'));
      fillAnswers(body, question);
      answers.append(body);
      requestAnimationFrame(() => fitFormulas(body));
    });
    article.append(answers, metadata(question));
  }
  article.append(node('div', '难度 ' + difficulty.estimate + '/5 · ' + (difficulty.basis === 'observed' ? '有作答数据依据' : '估计，未经作答数据校准') + ' · ' + item.demand.reasoning_steps + ' 步推理', 'meta'));
  return article;
}

function setView(mode, focus) {
  view = mode;
  if (view !== 'detail') {
    $('figure-dialog').close();
    $('large-figure').removeAttribute('src');
    $('export-dialog').close();
    $('export-sheet').replaceChildren();
  }
  try { localStorage.setItem('mws-bank-view', view); } catch {}
  render();
  if (focus) document.querySelector('article[data-id="' + focus + '"]')?.scrollIntoView({ block: 'start' });
}

for (const filter of filters) {
  const category = filter.dataset.category;
  if (category) {
    const values = [...new Set(bank.questions.flatMap(question => question.item.tags[category] || []))].sort((a, b) => a.localeCompare(b, 'zh-CN', { numeric: true }));
    for (const value of values) {
      const option = node('option', value);
      option.value = value;
      filter.append(option);
    }
  }
  filter.addEventListener('change', () => { page = 1; render(); });
}

function render() {
  const query = $('search').value.trim().toLocaleLowerCase();
  const terms = query.split(/\s+/).filter(Boolean);
  visible = bank.questions.filter(question => {
    const item = question.item;
    const haystack = [question.short_id, item.title, item.summary, item.stem, ...Object.values(item.tags).flat()].join(' ').toLocaleLowerCase();
    if (/^q\d+$/.test(query) ? question.short_id.toLowerCase() !== query : !terms.every(term => haystack.includes(term))) return false;
    return filters.every(filter => !filter.value || (filter.id === 'difficulty' ? String(item.demand.difficulty.estimate) === filter.value : (item.tags[filter.dataset.category] || []).includes(filter.value)));
  });
  const pages = Math.max(1, Math.ceil(visible.length / pageSize));
  page = Math.min(page, pages);
  $('count').textContent = '找到 ' + visible.length + ' 道 / 全部 ' + bank.questions.length + ' 道';
  $('cards').dataset.view = view;
  $('view-summary').setAttribute('aria-pressed', String(view === 'summary'));
  $('view-detail').setAttribute('aria-pressed', String(view === 'detail'));
  $('cards').replaceChildren(...visible.slice((page - 1) * pageSize, page * pageSize).map(card));
  if (!visible.length) {
    const empty = node('div', undefined, 'empty');
    const missingNumber = /^q\d+$/.test(query) && !bank.questions.some(question => question.short_id.toLowerCase() === query);
    empty.append(node('strong', missingNumber ? '当前题库没有 ' + query.toUpperCase() : bank.questions.length ? '没有符合条件的题目' : '题库还没有题目'), node('p', missingNumber ? '题目按首次收录顺序连续编号，请检查题号，或重置筛选浏览全部题目。' : bank.questions.length ? '试试其他关键词，或重置筛选。' : '先在聊天中审核并批准收录题目，再重新生成浏览页。'));
    $('cards').append(empty);
  }
  $('page').textContent = page + ' / ' + pages;
  $('prev').disabled = page === 1;
  $('next').disabled = page === pages;
  requestAnimationFrame(() => fitFormulas($('cards')));
}

function updateSelection() {
  const questions = [...selected.values()], ids = questions.map(question => question.short_id).join('、');
  document.querySelector('.selection').classList.toggle('has-selection', questions.length > 0);
  $('selection-count').textContent = '已选 ' + questions.length + ' 题 / 上限 ' + bank.limit + ' 题';
  $('selected-list').replaceChildren();
  for (const question of questions) {
    const button = node('button', question.short_id + ' ×');
    button.type = 'button';
    button.setAttribute('aria-label', '移除参考题 ' + question.short_id);
    button.addEventListener('click', () => { selected.delete(question.short_id); updateSelection(); render(); });
    $('selected-list').append(button);
  }
  $('prompt').value = questions.length ? '使用 math-worksheets，参考题库中的 ' + ids + '，生成同类型的新题。\n题库位置：' + bank.home + '\n浏览时版本：' + questions.map(question => question.short_id + ' r' + question.revision + '（' + question.item.title + '）').join('；') + '\n请先按题号读取原题、解答和难度信息；若当前修订或题目与上述不一致，请先指出。\n保持考查结构与推理要求，重新设计题目并独立验算。\n数量、年级、难度调整和交付物：［请补充］。\n本次仅作参考，新题暂不收录。' : '';
  for (const id of ['copy-ids', 'copy-prompt', 'clear']) $(id).disabled = !questions.length;
  $('status').textContent = questions.length ? '选题在切换视图、筛选和分页时保留。' : '勾选题目，复制简短题号或完整参考提示词。';
}

async function copy(text) {
  try {
    if (!navigator.clipboard) throw Error('clipboard unavailable');
    await navigator.clipboard.writeText(text);
    $('status').textContent = '已复制，可粘贴到聊天中。';
    return true;
  } catch {
    const temporary = node('textarea', text);
    document.body.append(temporary);
    temporary.select();
    let copied = false;
    try { copied = document.execCommand('copy'); } catch {}
    temporary.remove();
    $('status').textContent = copied ? '已复制，可粘贴到聊天中。' : '浏览器未允许自动复制，请从下方文本框手动复制。';
    if (!copied) {
      $('prompt-panel').open = true;
      $('prompt').value = text;
      $('prompt').focus();
      $('prompt').select();
    }
    return copied;
  }
}

$('close-figure').addEventListener('click', () => $('figure-dialog').close());
$('close-export').addEventListener('click', () => $('export-dialog').close());
$('export-dialog').addEventListener('close', () => {
  if ($('export-dialog').dataset.previousTitle) document.title = $('export-dialog').dataset.previousTitle;
});
$('print-export').addEventListener('click', () => window.print());
const formulaResize = new ResizeObserver(() => requestAnimationFrame(() => fitFormulas()));
formulaResize.observe($('cards'));
formulaResize.observe($('export-sheet'));
$('view-summary').addEventListener('click', () => setView('summary'));
$('view-detail').addEventListener('click', () => setView('detail'));
$('copy-ids').addEventListener('click', () => copy([...selected.keys()].join('、')));
$('copy-prompt').addEventListener('click', () => { updateSelection(); copy($('prompt').value); });
$('clear').addEventListener('click', () => { selected.clear(); updateSelection(); render(); });
$('search').addEventListener('input', () => { page = 1; render(); });
$('reset').addEventListener('click', () => { $('search').value = ''; filters.forEach(filter => filter.value = ''); page = 1; render(); });
$('prev').addEventListener('click', () => { page--; render(); });
$('next').addEventListener('click', () => { page++; render(); });
$('snapshot').textContent = '快照时间 ' + bank.created + ' · ' + bank.home;
render();
updateSelection();
