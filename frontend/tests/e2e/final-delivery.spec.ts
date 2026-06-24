import { expect, test } from "@playwright/test";

test("final delivery surface keeps preview, download, and retry together", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const jsonResponse = (data: unknown) =>
      new Response(JSON.stringify(data), {
        headers: { "Content-Type": "application/json" },
      });

    const textResponse = (body: string, contentType: string) =>
      new Response(body, {
        headers: { "Content-Type": contentType },
      });

    const originalFetch = window.fetch.bind(window);

    window.fetch = async (input, init) => {
      const url = typeof input === "string" ? input : input.url;

      if (url.includes("/api/v1/projects/7/final-video")) {
        return textResponse("final video bytes", "video/mp4");
      }

      if (url.includes("/api/v1/projects/7/characters")) {
        return jsonResponse([]);
      }

      if (url.includes("/api/v1/projects/7/shots")) {
        return jsonResponse([]);
      }

      if (url.includes("/api/v1/projects/7/messages")) {
        return jsonResponse([]);
      }

      if (url.includes("/api/v1/projects/7")) {
        return jsonResponse({
          id: 7,
          title: "创意项目",
          story: "一只小猫的故事",
          style: "anime",
          summary: "温馨小片段",
          video_url: "/static/videos/final-current.mp4",
          status: "active",
          target_shot_count: 6,
          character_hints: [],
          creation_mode: "story",
          reference_images: [],
          provider_settings: {
            text: { selected_key: "openai", resolved_key: "openai", source: "default", valid: true, status: "valid" },
            image: { selected_key: "fal", resolved_key: "fal", source: "default", valid: true, status: "valid" },
            video: { selected_key: "runway", resolved_key: "runway", source: "default", valid: true, status: "valid" },
          },
          created_at: "2026-05-05T00:00:00Z",
          updated_at: "2026-05-05T00:00:00Z",
        });
      }

      return originalFetch(input, init);
    };
  });

  await page.goto("/project/7");

  await expect(page.getByText("来源：当前成片")).toBeVisible();
  await expect(page.getByRole("button", { name: "预览最终视频" })).toBeVisible();
  await expect(page.getByRole("button", { name: "下载最终视频" })).toBeVisible();
  await expect(page.getByRole("button", { name: "重试合成" })).toBeVisible();
});
