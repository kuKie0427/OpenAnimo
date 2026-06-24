import { test, expect } from '@playwright/test';

test('homepage has title and sidebar works', async ({ page }) => {
  await page.goto('/');

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/OpenAnimo/);

  // Check if sidebar is closed and open it if needed.
  const openSidebarButton = page.getByTitle('展开侧边栏');
  if (await openSidebarButton.isVisible()) {
    await openSidebarButton.click();
  }

  // Find the "New Story" button and click it.
  const newStoryButton = page.getByRole('button', { name: /新建故事/i });
  await newStoryButton.click();

  // Expects the URL to be /.
  await expect(page).toHaveURL('/');
});
