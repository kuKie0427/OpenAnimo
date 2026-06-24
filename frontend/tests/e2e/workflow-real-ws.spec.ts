import { expect, test } from "@playwright/test";
import { SEED_PROJECT_ID } from "./conftest";

async function preopenChatPanel(page: import("@playwright/test").Page) {
	await page.addInitScript(() => {
		localStorage.setItem(
			"openanimo-chat-panel",
			JSON.stringify({ state: { isOpen: true }, version: 0 }),
		);
	});
}

async function clickConfirmButton(page: import("@playwright/test").Page) {
	const passButton = page.getByRole("button", { name: "通过" });
	if (await passButton.isVisible({ timeout: 2000 }).catch(() => false)) {
		await passButton.click();
		return;
	}
	await page.getByRole("button", { name: "确认大纲" }).click();
}

async function waitForConfirmButton(
	page: import("@playwright/test").Page,
	timeout = 30_000,
): Promise<"pass" | "outline"> {
	const passButton = page.getByRole("button", { name: "通过" });
	const outlineButton = page.getByRole("button", { name: "确认大纲" });

	try {
		await expect(passButton).toBeVisible({ timeout });
		return "pass";
	} catch {
		await expect(outlineButton).toBeVisible({ timeout: 5000 });
		return "outline";
	}
}

test.describe("Real WebSocket Integration", () => {
	test.describe.configure({ mode: "serial" });

	test("WebSocket connects and receives connected event", async ({ page }) => {
		test.setTimeout(60_000);

		await preopenChatPanel(page);
		await page.goto(`/project/${SEED_PROJECT_ID}`);
		await page.waitForLoadState("networkidle");

		// The "connected" WS event has no visible UI effect (useWebSocket.ts:280).
		// Verify implicitly: page loads, project data arrives, no error states.
		await expect(page.getByText("E2E 种子项目")).toBeVisible({ timeout: 15_000 });
		await expect(page.getByText("正在加载项目...")).not.toBeVisible({ timeout: 10_000 });
		await expect(page.getByText("规划阶段")).toBeVisible();
		await expect(
			page.getByRole("button", { name: "开始生成漫剧" }),
		).toBeVisible({ timeout: 15_000 });
	});

	test("generation flow emits run_progress and run_awaiting_confirm events", async ({
		page,
	}) => {
		test.setTimeout(60_000);

		await preopenChatPanel(page);
		await page.goto(`/project/${SEED_PROJECT_ID}`);
		await page.waitForLoadState("networkidle");

		const generateButton = page.getByRole("button", { name: "开始生成漫剧" });
		await expect(generateButton).toBeVisible({ timeout: 15_000 });
		await generateButton.click();

		// run_progress (or run_started) sets isGenerating=true → loading dots appear
		await expect(page.locator(".loading-dots")).toBeVisible({ timeout: 15_000 });
		await expect(generateButton).not.toBeVisible({ timeout: 5000 });

		const confirmType = await waitForConfirmButton(page);

		if (confirmType === "outline") {
			await expect(page.getByText("故事大纲待确认")).toBeVisible();
		} else {
			await expect(page.getByText("确认继续？")).toBeVisible();
		}

		await expect(page.getByText("规划阶段")).toBeVisible();
	});

	test("confirm triggers run_confirmed and next stage progress", async ({
		page,
	}) => {
		test.setTimeout(60_000);

		await preopenChatPanel(page);
		await page.goto(`/project/${SEED_PROJECT_ID}`);
		await page.waitForLoadState("networkidle");

		const generateButton = page.getByRole("button", { name: "开始生成漫剧" });
		await expect(generateButton).toBeVisible({ timeout: 15_000 });
		await generateButton.click();

		await waitForConfirmButton(page);
		await clickConfirmButton(page);

		// run_confirmed sets awaitingConfirm=false → confirm UI disappears
		const passButton = page.getByRole("button", { name: "通过" });
		const outlineButton = page.getByRole("button", { name: "确认大纲" });
		await expect(passButton.or(outlineButton)).not.toBeVisible({ timeout: 10_000 });
		await expect(page.locator(".loading-dots")).toBeVisible({ timeout: 10_000 });

		// Next sub-stage reaches its own approval gate → second run_awaiting_confirm
		const nextConfirmType = await waitForConfirmButton(page);

		if (nextConfirmType === "outline") {
			await expect(page.getByText("故事大纲待确认")).toBeVisible();
		} else {
			await expect(page.getByText("确认继续？")).toBeVisible();
		}

		await expect(page.getByText("规划阶段")).toBeVisible();
	});
});
