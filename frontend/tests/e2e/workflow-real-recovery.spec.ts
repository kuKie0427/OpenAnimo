import { expect, test } from "@playwright/test";
import { BACKEND_PORT, SEED_PROJECT_ID } from "./conftest";

async function preopenChatPanel(page: import("@playwright/test").Page) {
	await page.addInitScript(() => {
		localStorage.setItem(
			"openanimo-chat-panel",
			JSON.stringify({ state: { isOpen: true }, version: 0 }),
		);
	});
}

async function clickConfirmButton(page: import("@playwright/test").Page) {
	const passButton = page.getByRole("button", { name: /通过/ });
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

test.describe("Recovery Flow — Real Backend", () => {
	test.describe.configure({ mode: "serial" });

	test("409 recoverable triggers resume UI", async ({ page }) => {
		test.setTimeout(90_000);

		// Step 1: Start generation and reach first confirm gate
		await preopenChatPanel(page);
		await page.goto(`/project/${SEED_PROJECT_ID}`);
		await page.waitForLoadState("networkidle");

		const generateButton = page.getByRole("button", {
			name: "开始生成漫剧",
		});
		await expect(generateButton).toBeVisible({ timeout: 15_000 });
		await generateButton.click();

		// Wait for loading and first confirm gate
		await expect(page.locator(".loading-dots")).toBeVisible({ timeout: 15_000 });
		await waitForConfirmButton(page);

		// Step 2: Cancel the run via backend API
		// The UI stop button is hidden during awaitingConfirm, so use direct API
		const cancelResp = await page.request.post(
			`http://localhost:${BACKEND_PORT}/api/v1/projects/${SEED_PROJECT_ID}/cancel`,
		);
		expect(cancelResp.ok()).toBe(true);

		// Wait for cancellation to propagate to DB
		await page.waitForTimeout(2000);

		// Step 3: Reload page with autoStart=true
		// The run is now "cancelled" → backend returns 409 recoverable
		await preopenChatPanel(page);
		await page.goto(`/project/${SEED_PROJECT_ID}?autoStart=true`);
		await page.waitForLoadState("networkidle");

		// Step 4: Verify recovery UI — "恢复" button and warning indicator
		const resumeButton = page.getByRole("button", { name: /恢复/ });
		await expect(resumeButton).toBeVisible({ timeout: 15_000 });

		// The ExclamationTriangleIcon renders within the StagePipeline with text-warning class
		await expect(page.locator(".text-warning")).toBeVisible({ timeout: 5_000 });

		// The pipeline nav with aria-label should be visible
		await expect(
			page.locator("nav[aria-label='Pipeline stages']"),
		).toBeVisible();

		// Generate button should NOT be visible — recovery state is active
		await expect(
			page.getByRole("button", { name: "开始生成漫剧" }),
		).not.toBeVisible({ timeout: 5_000 });
	});

	test("resume continues from checkpoint", async ({ page }) => {
		test.setTimeout(90_000);

		// Step 1: Navigate — run is still cancelled from test 1
		// autoStart triggers generate → 409 recoverable → recovery UI
		await preopenChatPanel(page);
		await page.goto(`/project/${SEED_PROJECT_ID}?autoStart=true`);
		await page.waitForLoadState("networkidle");

		// Step 2: Recovery UI should appear
		const resumeButton = page.getByRole("button", { name: /恢复/ });
		await expect(resumeButton).toBeVisible({ timeout: 15_000 });

		// Step 3: Click "恢复" → triggers POST /api/v1/projects/{id}/resume
		await resumeButton.click();

		// The resume button should disappear after clicking
		await expect(resumeButton).not.toBeVisible({ timeout: 10_000 });

		// Step 4: Wait for loading state (generation resumes)
		await expect(page.locator(".loading-dots")).toBeVisible({ timeout: 15_000 });

		// Step 5: Wait for confirm gate (resumed run reaches next approval)
		const firstConfirm = await waitForConfirmButton(page, 60_000);

		if (firstConfirm === "outline") {
			await expect(page.getByText("故事大纲待确认")).toBeVisible();
		} else {
			await expect(page.getByText("确认继续？")).toBeVisible();
		}

		// Step 6: Confirm first gate
		await clickConfirmButton(page);

		// Step 7: Confirm button disappears, loading reappears
		await expect(
			page
				.getByRole("button", { name: /通过/ })
				.or(page.getByRole("button", { name: "确认大纲" })),
		).not.toBeVisible({ timeout: 10_000 });

		// Step 8: Wait for next confirm gate (if any) and confirm
		const secondConfirm = await waitForConfirmButton(page, 30_000).catch(
			() => null,
		);
		if (secondConfirm) {
			await clickConfirmButton(page);
		}

		// Step 9: Wait for running completion
		await expect(page.locator(".loading.loading-dots")).not.toBeVisible({
			timeout: 60_000,
		});
		await expect(
			page.getByRole("button", { name: "停止生成" }),
		).not.toBeVisible({ timeout: 10_000 });

		// Step 10: Verify project completed via real API
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
});
