import { test, expect } from '@playwright/test';

test.describe('768px viewport layout', () => {
  test.use({ viewport: { width: 768, height: 900 } });

  test('no horizontal overflow on homepage', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check no horizontal overflow
    const hasOverflow = await page.evaluate(() => {
      const html = document.documentElement;
      const body = document.body;
      return {
        htmlScrollWidth: html.scrollWidth,
        htmlClientWidth: html.clientWidth,
        bodyScrollWidth: body.scrollWidth,
        bodyClientWidth: body.clientWidth,
        overflow: html.scrollWidth > html.clientWidth + 10,
      };
    });

    console.log('768px viewport overflow check:', JSON.stringify(hasOverflow, null, 2));
    expect(hasOverflow.overflow).toBe(false);

    // Take screenshot for record
    await page.screenshot({ path: 'e2e-screenshots/viewport-768-homepage.png', fullPage: true });
  });

  test('no horizontal overflow on project page', async ({ page }) => {
    // Navigate to /projects (should load without backend if MSW is active)
    await page.goto('/projects');
    await page.waitForLoadState('networkidle');

    const hasOverflow = await page.evaluate(() => {
      const html = document.documentElement;
      return {
        overflow: html.scrollWidth > html.clientWidth + 10,
        scrollWidth: html.scrollWidth,
        clientWidth: html.clientWidth,
      };
    });

    console.log('Projects page overflow check:', JSON.stringify(hasOverflow, null, 2));
    expect(hasOverflow.overflow).toBe(false);

    await page.screenshot({ path: 'e2e-screenshots/viewport-768-projects.png', fullPage: true });
  });
});
