export const STAGE_PIPELINE = [
  { key: "plan", label: "规划", icon: "bulb" as const },
  { key: "render", label: "渲染", icon: "palette" as const },
  { key: "compose", label: "合成", icon: "cube" as const },
] as const;

export type PipelineStageKey = (typeof STAGE_PIPELINE)[number]["key"];

const APPROVAL_STAGE_MAP: Record<string, string> = {
  plan_approval: "plan",
  render_approval: "render",
};

export function getPipelineStageIndex(stage: string): number {
  const mappedStage = APPROVAL_STAGE_MAP[stage] ?? stage;
  return STAGE_PIPELINE.findIndex((s) => s.key === mappedStage);
}

export function isPipelineStage(stage: string): stage is PipelineStageKey {
  return STAGE_PIPELINE.some((s) => s.key === stage);
}
