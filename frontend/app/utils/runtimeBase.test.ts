import { describe, expect, it } from "vitest";

import { resolveBackendBase } from "./runtimeBase";

describe("resolveBackendBase", () => {
  it("prefers explicit non-loopback env URL when provided", () => {
    expect(
      resolveBackendBase({
        envUrl: "http://api.example.com:29999",
        pageUrl: "http://127.0.0.1:15173/project/1",
        transport: "http",
        dev: true,
      })
    ).toBe("http://api.example.com:29999");
  });

  it("aligns loopback env HTTP URL to the current page hostname in dev", () => {
    expect(
      resolveBackendBase({
        envUrl: "http://localhost:18765",
        pageUrl: "http://127.0.0.1:15173/project/1",
        transport: "http",
        dev: true,
      })
    ).toBe("http://127.0.0.1:18765");
  });

  it("aligns loopback env WS URL to the current page hostname in dev", () => {
    expect(
      resolveBackendBase({
        envUrl: "ws://127.0.0.1:18765",
        pageUrl: "http://localhost:15173/project/1",
        transport: "ws",
        dev: true,
      })
    ).toBe("ws://localhost:18765");
  });

  it("uses current page hostname for dev HTTP requests", () => {
    expect(
      resolveBackendBase({
        pageUrl: "http://127.0.0.1:15173/project/1",
        transport: "http",
        dev: true,
      })
    ).toBe("http://127.0.0.1:18765");
  });

  it("uses secure websocket protocol when page runs over https", () => {
    expect(
      resolveBackendBase({
        pageUrl: "https://localhost:15173/project/1",
        transport: "ws",
        dev: true,
      })
    ).toBe("wss://localhost:18765");
  });

  it("falls back to localhost when no page URL is available", () => {
    expect(
      resolveBackendBase({
        transport: "ws",
        dev: true,
      })
    ).toBe("ws://localhost:18765");
  });
});
