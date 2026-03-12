const { test, expect } = require('playwright/test');

test('overview, local search, and realtime search work', async ({ page }) => {
  const consoleErrors = [];
  page.on('pageerror', err => consoleErrors.push(`PAGEERROR: ${err.message}`));
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(`CONSOLE: ${msg.text()}`);
  });

  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  await expect(page.getByRole('link', { name: '实时检索' })).toBeVisible();
  await expect(page.getByRole('link', { name: '本地检索' })).toBeVisible();

  await page.goto('http://127.0.0.1:8000/search?query_date=2026-03-18', { waitUntil: 'networkidle' });
  await expect(page.getByText('结构化检索')).toBeVisible();
  await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 });

  await page.goto('http://127.0.0.1:8000/realtime', { waitUntil: 'networkidle' });
  await page.getByLabel('日期').fill('2026-03-18');
  await page.getByLabel('出发站').fill('杭州东');
  await page.getByLabel('到达站').fill('上海虹桥');
  await page.getByRole('button', { name: '开始查询' }).click();

  await expect(page.getByText('按天明细 / 聚合摘要')).toBeVisible({ timeout: 20000 });
  await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 20000 });
  await expect(page.locator('text=G2').first()).toBeVisible({ timeout: 20000 });

  if (consoleErrors.length) {
    throw new Error(consoleErrors.join('\n'));
  }
});
