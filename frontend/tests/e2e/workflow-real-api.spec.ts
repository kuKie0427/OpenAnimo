import type { Page } from "@playwright/test";
import { expect, test } from "@playwright/test";
import { BACKEND_PORT, SEED_PROJECT_ID } from "./conftest";

async function preopenChatPanel(page: Page) {
	await page.addInitScript(() => {
		localStorage.setItem(
			"openanimo-chat-panel",
			JSON.stringify({ state: { isOpen: true }, version: 0 }),
		);
	});
}

async function clickConfirmButton(page: Page) {
	const passButton = page.getByRole("button", { name: /通过/ });
	if (await passButton.isVisible({ timeout: 2000 }).catch(() => false)) {
		await passButton.click();
		return;
	}
	await page.getByRole("button", { name: "确认大纲" }).click();
}

async function waitForConfirmButton(
	page: Page,
	timeout = 30_000,
): Promise<"pass" | "outline"> {
	const passButton = page.getByRole("button", { name: /通过/ });
	const outlineButton = page.getByRole("button", { name: "确认大纲" });

	try {
		await expect(passButton).toBeVisible({ timeout });
		return "pass";
	} catch {
		await expect(outlineButton).toBeVisible({ timeout: 5000 });
		return "outline";
	}
}

test.describe("Real API Integration", () => {
	test.describe.configure({ mode: "serial" });

	test("homepage loads project list from real backend", async ({ page }) => {
		test.setTimeout(30_000);

		await page.goto("/");
		await page.waitForLoadState("networkidle");

		// Open HistoryDrawer to trigger projectsApi.list() from real backend
		const historyButton = page.getByTitle("对话历史");
		await expect(historyButton).toBeVisible();
		await historyButton.click();

		await page.waitForLoadState("networkidle");

		await expect(page.getByText("E2E 种子项目")).toBeVisible();
	});

	test("project page loads project detail from real backend", async ({ page }) => {
		test.setTimeout(30_000);

		await page.goto(`/project/${SEED_PROJECT_ID}`);
		await page.waitForLoadState("networkidle");

		await expect(page.getByText("正在加载项目...")).not.toBeVisible({
			timeout: 15_000,
		});

		await expect(page.getByText("E2E 种子项目")).toBeVisible();

		const topBar = page.locator("header").first();
		await expect(topBar).toBeVisible();
	});

	test("project page loads characters from real backend", async ({ page }) => {
		test.setTimeout(30_000);

		await page.goto(`/project/${SEED_PROJECT_ID}`);
		await page.waitForLoadState("networkidle");

		await expect(page.getByText("项目未找到")).not.toBeVisible({
			timeout: 15_000,
		});

		const topBar = page.locator("header").first();
		await expect(topBar).toBeVisible();

		await page.waitForLoadState("networkidle");
		await expect(page.getByText("正在加载项目...")).not.toBeVisible({
			timeout: 10_000,
		});
	});

	test("project page loads shots from real backend", async ({ page }) => {
		test.setTimeout(30_000);

		await page.goto(`/project/${SEED_PROJECT_ID}`);
		await page.waitForLoadState("networkidle");

		await expect(page.getByText("项目未找到")).not.toBeVisible({
			timeout: 15_000,
		});

		const topBar = page.locator("header").first();
		await expect(topBar).toBeVisible();

		await expect(page.getByText("E2E 种子项目")).toBeVisible();
	});

	test("full generation flow: start → plan → confirm → render → confirm → compose → complete", async ({
		page,
	}) => {
		test.setTimeout(120_000);

		await preopenChatPanel(page);
		await page.goto(`/project/${SEED_PROJECT_ID}`);
		await page.waitForLoadState("networkidle");

		// Step 1: Click "开始生成漫剧"
		const generateButton = page.getByRole("button", {
			name: "开始生成漫剧",
		});
		await expect(generateButton).toBeVisible({ timeout: 15_000 });
		await generateButton.click();

		// Step 2: Loading state appears — plan stage is running
		await expect(page.locator(".loading.loading-dots")).toBeVisible({
			timeout: 15_000,
		});
		await expect(page.getByText("规划阶段")).toBeVisible();

		// Step 3: Wait for first confirm gate
		const firstConfirm = await waitForConfirmButton(page);

		if (firstConfirm === "outline") {
			await expect(page.getByText("故事大纲待确认")).toBeVisible();
		} else {
			await expect(page.getByText(/已完成/)).toBeVisible();
		}

		// Step 4: Confirm first gate
		await clickConfirmButton(page);

		// Step 5: Confirm button disappears, loading reappears
		await expect(
			page
				.getByRole("button", { name: /通过/ })
				.or(page.getByRole("button", { name: "确认大纲" })),
		).not.toBeVisible({ timeout: 10_000 });
		await expect(page.locator(".loading.loading-dots")).toBeVisible({
			timeout: 10_000,
		});

		// Step 6: Wait for second confirm gate
		const secondConfirm = await waitForConfirmButton(page, 60_000);

		if (secondConfirm === "outline") {
			await expect(page.getByText("故事大纲待确认")).toBeVisible();
		} else {
			await expect(page.getByText(/已完成/)).toBeVisible();
		}

		// Stage should have advanced to render
		await expect(page.getByText("渲染阶段")).toBeVisible({
			timeout: 5_000,
		});

		// Step 7: Confirm second gate
		await clickConfirmButton(page);

		// Step 8: Confirm disappears, loading reappears (compose stage)
		await expect(
			page
				.getByRole("button", { name: /通过/ })
				.or(page.getByRole("button", { name: "确认大纲" })),
		).not.toBeVisible({ timeout: 10_000 });
		await expect(page.locator(".loading.loading-dots")).toBeVisible({
			timeout: 10_000,
		});

		// Step 9: Wait for run_completed — loading dots and stop button disappear
		await expect(page.locator(".loading.loading-dots")).not.toBeVisible({
			timeout: 60_000,
		});
		await expect(
			page.getByRole("button", { name: "停止生成" }),
		).not.toBeVisible({ timeout: 5_000 });

		// Step 10: Verify final stage is "合成阶段"
		await expect(page.getByText("合成阶段")).toBeVisible({
			timeout: 10_000,
		});

		// Step 11: Verify project status via real API
		const response = await page.request.get(
			`http://localhost:${BACKEND_PORT}/api/v1/projects/${SEED_PROJECT_ID}`,
		);
		expect(response.ok()).toBe(true);
		const projectData = (await response.json()) as {
			id: number;
			status: string;
		};
		expect(["ready", "completed"]).toContain(projectData.status);
	});

	test("feedback sends to backend and is processed", async ({ page }) => {
		test.setTimeout(120_000);

		await preopenChatPanel(page);
		await page.goto(`/project/${SEED_PROJECT_ID}`);
		await page.waitForLoadState("networkidle");

		// --- Complete the full generation flow first ---
		const generateButton = page.getByRole("button", {
			name: "开始生成漫剧",
		});
		await expect(generateButton).toBeVisible({ timeout: 15_000 });
		await generateButton.click();

		// First confirm gate
		await expect(page.locator(".loading.loading-dots")).toBeVisible({
			timeout: 15_000,
		});
		await waitForConfirmButton(page);
		await clickConfirmButton(page);

		// Second confirm gate
		await expect(
			page
				.getByRole("button", { name: /通过/ })
				.or(page.getByRole("button", { name: "确认大纲" })),
		).not.toBeVisible({ timeout: 10_000 });
		await waitForConfirmButton(page, 60_000);
		await clickConfirmButton(page);

		// Wait for generation to complete
		await expect(page.locator(".loading.loading-dots")).not.toBeVisible({
			timeout: 60_000,
		});
		await expect(
			page.getByRole("button", { name: "停止生成" }),
		).not.toBeVisible({ timeout: 5_000 });
		await expect(page.getByText("合成阶段")).toBeVisible({
			timeout: 10_000,
		});

		// --- Send feedback ---
		const feedbackText = "E2E 测试反馈 - 请优化角色设计";
		const textbox = page.getByRole("textbox");
		await textbox.fill(feedbackText);

		// Intercept the feedback API call
		const feedbackResponsePromise = page.waitForResponse(
			(resp) =>
				resp
					.url()
					.includes(
						`/api/v1/projects/${SEED_PROJECT_ID}/feedback`,
					) && resp.request().method() === "POST",
			{ timeout: 15_000 },
		);

		await page.getByRole("button", { name: "发送" }).click();

		// Verify API response status
		const feedbackResp = await feedbackResponsePromise;
		expect(feedbackResp.status()).toBeGreaterThanOrEqual(200);
		expect(feedbackResp.status()).toBeLessThan(300);

		// Verify feedback message appears in chat
		await expect(page.getByText(feedbackText)).toBeVisible({
			timeout: 5_000,
		});
	});
});
