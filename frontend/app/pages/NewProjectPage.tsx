import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { projectsApi } from "~/services/api";
import { ProviderSelectionFields } from "~/components/project/ProviderSelectionFields";
import { StyleTemplateGrid } from "~/components/project/StyleTemplateGrid";
import { CreateStyleModal } from "~/components/project/CreateStyleModal";
import { UniverseSelector } from "~/components/universe/UniverseSelector";
import { Button } from "~/components/ui/Button";
import { Input } from "~/components/ui/Input";
import { Card } from "~/components/ui/Card";
import { AppShell } from "~/components/layout/AppShell";
import {
  CheckCircleIcon,
  DocumentTextIcon,
  GlobeAltIcon,
  PaintBrushIcon,
} from "@heroicons/react/24/outline";
import { toast } from "~/utils/toast";
import { ApiError } from "~/types/errors";

export function NewProjectPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  const [showCreateStyle, setShowCreateStyle] = useState(false);
  const [formData, setFormData] = useState({
    title: "",
    story: "",
    style: "cinematic",
    text_provider_override: null as string | null,
    image_provider_override: null as string | null,
    video_provider_override: null as string | null,
    universe_id: null as number | null,
  });

  const createMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success({
        title: "创建成功",
        message: "项目已创建，正在跳转...",
      });
      navigate(`/project/${project.id}?autoStart=true`);
    },
    onError: (error: Error | ApiError) => {
      const apiError = error instanceof ApiError ? error : null;
      toast.error({
        title: "创建失败",
        message: apiError?.message || error.message || "未知错误",
        actions: [
          {
            label: "重试",
            onClick: () => createMutation.mutate(formData),
          },
        ],
      });
    },
  });

  const handleSubmit = () => {
    if (!formData.title.trim()) return;
    createMutation.mutate(formData);
  };

  return (
    <AppShell
      variant="default"
      onToggleAssets={() => {}}
      onToggleHistory={() => {}}
      onAssetsClose={() => {}}
      onHistoryClose={() => {}}
      chatIsGenerating={false}
      onChatSendFeedback={() => {}}
      onChatConfirm={() => {}}
      onChatEntityConfirm={() => {}}
      onChatGenerate={() => {}}
      onChatCancel={() => {}}
      versionCompareOpen={false}
      versionCompareProjectId={0}
      onVersionCompareClose={() => {}}
    >
      <main className="container mx-auto px-4 py-8 max-w-2xl">
        {/* Progress steps */}
        <ul className="steps steps-horizontal w-full mb-8">
          <li className={`step ${step >= 1 ? "step-primary" : ""}`}>故事</li>
          <li className={`step ${step >= 2 ? "step-primary" : ""}`}>风格</li>
          <li className={`step ${step >= 3 ? "step-primary" : ""}`}>确认</li>
        </ul>

        {/* Step 1: Story */}
        {step === 1 && (
          <Card
            title={
              <span className="inline-flex items-center gap-2">
                <DocumentTextIcon className="w-5 h-5" aria-hidden="true" />
                讲述你的故事
              </span>
            }
          >
            <div className="space-y-4">
              <Input
                label="项目标题"
                placeholder="我的精彩故事"
                value={formData.title}
                onChange={(e) =>
                  setFormData({ ...formData, title: e.target.value })
                }
              />
              <div className="form-control">
                <label className="label" htmlFor="project-story">
                  <span className="label-text">故事内容</span>
                </label>
                <textarea
                  id="project-story"
                  className="textarea textarea-bordered bg-base-200 h-48"
                  placeholder="很久很久以前..."
                  value={formData.story}
                  onChange={(e) =>
                    setFormData({ ...formData, story: e.target.value })
                  }
                />
              </div>
              <div className="form-control">
                <label className="label">
                  <span className="label-text text-sm font-bold">所属宇宙（可选）</span>
                </label>
                <UniverseSelector
                  value={formData.universe_id}
                  onChange={(id) =>
                    setFormData({ ...formData, universe_id: id })
                  }
                />
                <label className="label">
                  <span className="label-text-alt text-xs text-base-content/40">
                    选择宇宙后，角色会自动从共享角色库导入
                  </span>
                </label>
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={() => setStep(2)}
                  disabled={!formData.title.trim()}
                >
                  下一步 →
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Step 2: Style */}
        {step === 2 && (
          <Card
            title={
              <span className="inline-flex items-center gap-2">
                <PaintBrushIcon className="w-5 h-5" aria-hidden="true" />
                选择风格
              </span>
            }
          >
            <div className="mb-6">
              <StyleTemplateGrid
                selectedSlug={formData.style}
                onSelect={(slug) => setFormData({ ...formData, style: slug })}
                onCreateNew={() => setShowCreateStyle(true)}
              />
            </div>
            <div className="mb-6 border-t border-base-300 pt-6">
              <div className="mb-4">
                <h4 className="text-base font-semibold text-base-content">
                  Provider 选择
                </h4>
                <p className="mt-1 text-sm text-base-content/70">
                  为当前项目单独设置 text / image / video provider；不设置时继承系统默认。
                </p>
              </div>
              <ProviderSelectionFields
                value={{
                  text_provider_override: formData.text_provider_override,
                  image_provider_override: formData.image_provider_override,
                  video_provider_override: formData.video_provider_override,
                }}
                onChange={(providers) => setFormData({ ...formData, ...providers })}
              />
            </div>
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep(1)}>
                ← 返回
              </Button>
              <Button onClick={() => setStep(3)}>下一步 →</Button>
            </div>
          </Card>
        )}

        {/* Step 3: Confirm */}
        {step === 3 && (
          <Card
            title={
              <span className="inline-flex items-center gap-2">
                <CheckCircleIcon className="w-5 h-5" aria-hidden="true" />
                确认项目
              </span>
            }
          >
            <div className="space-y-4">
              <div className="bg-base-300 rounded-lg p-4">
                <h3 className="font-semibold text-lg">{formData.title}</h3>
                <div className="badge badge-outline mt-2 flex items-center gap-2 text-base-content">
                  <PaintBrushIcon className="w-5 h-5" aria-hidden="true" />
                  {formData.style}
                </div>
                {formData.universe_id && (
                  <div className="badge badge-primary mt-2 ml-2 inline-flex items-center gap-1">
                    <GlobeAltIcon className="w-3 h-3" aria-hidden="true" />
                    属于宇宙
                  </div>
                )}
                {formData.story && (
                  <p className="text-sm text-base-content/70 mt-3 line-clamp-4">
                    {formData.story}
                  </p>
                )}
              </div>
              <div className="rounded-lg border border-base-300 bg-base-200/60 p-4">
                <h4 className="text-sm font-semibold text-base-content">
                  Provider 选择
                </h4>
                <dl className="mt-3 space-y-2 text-sm text-base-content/80">
                  <div className="flex items-center justify-between gap-4">
                    <dt>文本</dt>
                    <dd>{formData.text_provider_override ?? "继承默认"}</dd>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <dt>图像</dt>
                    <dd>{formData.image_provider_override ?? "继承默认"}</dd>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <dt>视频</dt>
                    <dd>{formData.video_provider_override ?? "继承默认"}</dd>
                  </div>
                </dl>
              </div>
              <div className="flex justify-between">
                <Button variant="ghost" onClick={() => setStep(2)}>
                  ← 返回
                </Button>
                <Button
                  variant="primary"
                  onClick={handleSubmit}
                  loading={createMutation.isPending}
                >
                  创建项目
                </Button>
              </div>
            </div>
          </Card>
        )}

        {createMutation.isError && (
          <div className="alert alert-error mt-4">
            <span>创建项目失败，请重试。</span>
          </div>
        )}
      </main>

      {/* Create Style Modal */}
      <CreateStyleModal
        isOpen={showCreateStyle}
        onClose={() => setShowCreateStyle(false)}
        onCreated={(slug) => {
          setFormData({ ...formData, style: slug });
          setShowCreateStyle(false);
        }}
      />
    </AppShell>
  );
}
