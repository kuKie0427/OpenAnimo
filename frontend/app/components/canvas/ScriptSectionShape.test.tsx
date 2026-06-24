import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ScriptSectionShapeUtil } from "./shapes/ScriptSectionShape";
import type { ScriptSectionShape, ReviewedCharacter, ReviewedShot } from "./shapes/types";

vi.mock("~/services/api", () => ({
  getStaticUrl: (path: string | null | undefined) => path,
}));

vi.mock("~/hooks/useDomSize", () => ({
  useDomSize: () => ({ current: null }),
  getShapeSize: () => undefined,
}));

describe("ScriptSectionShape", () => {
  const shapeUtil = new ScriptSectionShapeUtil({} as never);

  const createShape = (props: Partial<ScriptSectionShape["props"]> = {}) =>
    ({
      id: "script-shape",
      type: "script-section",
      x: 0,
      y: 0,
      props: {
        w: 800,
        h: 600,
        story: "阿宁走进雨夜的街道，霓虹灯映在积水中。",
        summary: "侦探在雨夜调查案件",
        characters: [],
        shots: [],
        sectionState: "complete",
        placeholder: false,
        statusLabel: "已完成",
        placeholderText: "等待编剧生成...",
        ...props,
      },
    }) as ScriptSectionShape;

  it("renders story text when present", () => {
    render(shapeUtil.component(createShape()));
    expect(screen.getByText(/阿宁走进雨夜的街道/)).toBeInTheDocument();
  });

  it("renders summary below story when both present", () => {
    render(shapeUtil.component(createShape()));
    expect(screen.getByText("侦探在雨夜调查案件")).toBeInTheDocument();
  });

  it("renders summary alone when story is empty", () => {
    const { container } = render(shapeUtil.component(createShape({ story: "", summary: "仅摘要" })));
    expect(container.textContent).toContain("仅摘要");
  });

  it("renders shot table when shots present", () => {
    const chars = [{ id: 1, name: "阿宁" }] as unknown as ReviewedCharacter[];
    const shotsList = [
      { id: 1, order: 1, description: "开场镜头", camera: "wide", duration: 5, character_ids: [1] },
      { id: 2, order: 2, description: "特写镜头", camera: "close", duration: 3, character_ids: [] },
      { id: 3, order: 3, description: "全景镜头", camera: null, duration: null, character_ids: [1] },
    ] as unknown as ReviewedShot[];
    render(
      shapeUtil.component(
        createShape({
          characters: chars,
          shots: shotsList,
        })
      )
    );
    expect(screen.getByText("开场镜头")).toBeInTheDocument();
    expect(screen.getByText("特写镜头")).toBeInTheDocument();
    expect(screen.getByText("wide")).toBeInTheDocument();
    expect(screen.getByText(/5s/)).toBeInTheDocument();
  });

  it("renders placeholder when no content", () => {
    render(
      shapeUtil.component(
        createShape({
          story: "",
          summary: "",
          placeholder: true,
          placeholderText: "等待编剧生成...",
        })
      )
    );
    expect(screen.getByText("等待编剧生成...")).toBeInTheDocument();
  });

  it("returns null indicator", () => {
    expect(shapeUtil.indicator()).toBeNull();
  });

  it("has correct static type", () => {
    expect(ScriptSectionShapeUtil.type).toBe("script-section");
  });

  it("can select but cannot resize", () => {
    expect(shapeUtil.canEdit()).toBe(true);
    expect(shapeUtil.canResize()).toBe(false);
  });
});
