import { test, expect } from "@playwright/test";

test("debug: inspect project page elements", async ({ page }) => {
  await page.addInitScript(() => {
    class MockWebSocket {
      static instances: MockWebSocket[] = [];
      static OPEN = 1;
      static CLOSED = 3;
      url: string;
      readyState = MockWebSocket.OPEN;
      onopen: null | ((event?: Event) => void) = null;
      onmessage: null | ((event: MessageEvent<string>) => void) = null;
      onerror: null | ((event?: Event) => void) = null;
      onclose: null | ((event?: Event) => void) = null;
      constructor(url: string) {
        this.url = url;
        MockWebSocket.instances.push(this);
        queueMicrotask(() => this.onopen?.(new Event("open")));
      }
      send(_data: string) {}
      close() { this.readyState = MockWebSocket.CLOSED; this.onclose?.(new Event("close")); }
    }
    Object.defineProperty(window, "WebSocket", { configurable: true, writable: true, value: MockWebSocket });
    window.__mockWs = {
      count: () => MockWebSocket.instances.length,
      dispatch: (event: Record<string, unknown>) => {
        const activeSocket = MockWebSocket.instances.at(-1);
        if (!activeSocket?.onmessage) throw new Error("No active mock websocket instance");
        activeSocket.onmessage(new MessageEvent("message", { data: JSON.stringify(event) }));
      },
    };
  });

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const path = url.pathname;
    const fulfillJson = async (body: unknown, status = 200) => {
      await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    };
    if (path === "/api/v1/config") return fulfillJson([]);
    if (path === "/api/v1/projects" && method === "GET") return fulfillJson({ items: [], total: 0 });
    if (path === "/api/v1/projects/7" && method === "GET") return fulfillJson({
      id: 7, title: "创意项目", story: "一只小猫的故事", style: "anime",
      summary: "温馨小片段", video_url: null, status: "active",
      target_shot_count: 6, character_hints: [], creation_mode: "story",
      reference_images: [],
      provider_settings: {
        text: { selected_key: "openai", resolved_key: "openai", source: "default", valid: true, status: "valid" },
        image: { selected_key: "fal", resolved_key: "fal", source: "default", valid: true, status: "valid" },
        video: { selected_key: "runway", resolved_key: "runway", source: "default", valid: true, status: "valid" },
      },
      created_at: "2026-05-05T00:00:00Z", updated_at: "2026-05-05T00:00:00Z",
    });
    if (path === "/api/v1/projects/7/characters") return fulfillJson([]);
    if (path === "/api/v1/projects/7/shots") return fulfillJson([]);
    if (path === "/api/v1/projects/7/messages") return fulfillJson([]);
    return fulfillJson({ error: { message: `Unhandled: ${method} ${path}` } }, 404);
  });

  await page.goto("/project/7");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "/tmp/e2e-debug2.png", fullPage: true });

  // Check all text content
  const text = await page.textContent("body");
  console.log("TEXT:", text?.substring(0, 3000));

  // Check buttons
  const buttons = await page.getByRole("button").allInnerTexts();
  console.log("BUTTONS:", JSON.stringify(buttons));

  // Check aria-labels
  const buttonAriaLabels = await page.evaluate(() => {
    return Array.from(document.querySelectorAll("button")).map(b => ({
      text: b.textContent?.trim(),
      ariaLabel: b.getAttribute("aria-label"),
    }));
  });
  console.log("BUTTON DETAILS:", JSON.stringify(buttonAriaLabels));

  // Check specifically for "规划阶段"
  const planStageEl = await page.getByText("规划阶段").count();
  console.log("规划阶段 count:", planStageEl);

  // Check chat panel visibility
  const chatPanelTexts = await page.locator("[class*='chat']").allInnerTexts();
  console.log("CHAT ELEMENTS:", chatPanelTexts.length);

  // Check drawer
  const drawerTexts = await page.locator("[class*='drawer']").allInnerTexts();
  console.log("DRAWER ELEMENTS:", drawerTexts.length);
});
