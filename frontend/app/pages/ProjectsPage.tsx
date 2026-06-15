import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectsApi } from "~/services/api";
import { Card } from "~/components/ui/Card";
import { ConfirmModal } from "~/components/ui/ConfirmModal";
import { AppShell } from "~/components/layout/AppShell";
import {
	DocumentTextIcon,
	FaceFrownIcon,
	PencilIcon,
	TrashIcon,
} from "@heroicons/react/24/outline";
import { toast } from "~/utils/toast";
import { ApiError } from "~/types/errors";
import { cleanupDeletedProjectCaches } from "~/features/projects/deleteProject";

export function ProjectsPage() {
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<number[] | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const {
    data: projects,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["projects"],
    queryFn: projectsApi.list,
    retry: 1,
  });

  // 显示加载错误
  useEffect(() => {
    if (error) {
      const apiError = error instanceof ApiError ? error : null;
      toast.error({
        title: "加载项目列表失败",
        message: apiError?.message || "无法获取项目列表",
        actions: [
          {
            label: "重试",
            onClick: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
          },
        ],
      });
    }
  }, [error, queryClient]);

  const deleteMutation = useMutation({
    mutationFn: (ids: number[]) => projectsApi.deleteMany(ids),
    onSuccess: (_, deletedIds) => {
      cleanupDeletedProjectCaches(queryClient, deletedIds);
      setSelectedIds((prev) => prev.filter((id) => !deletedIds.includes(id)));
      setDeleteTarget(null);
      toast.success({
        title: "删除成功",
        message: deletedIds.length > 1 ? "项目已批量删除" : "项目已删除",
      });
    },
    onError: (error: Error | ApiError) => {
      const apiError = error instanceof ApiError ? error : null;
      toast.error({
        title: "删除失败",
        message: apiError?.message || error.message || "未知错误",
      });
    },
  });

  const handleDeleteClick = (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (deleteMutation.isPending) return;
    setDeleteTarget([id]);
  };

  const handleBatchDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    if (deleteMutation.isPending || selectedIds.length === 0) return;
    setDeleteTarget([...selectedIds]);
  };

  const handleToggleSelect = (projectId: number, checked: boolean) => {
    setSelectedIds((prev) =>
      checked ? [...prev, projectId] : prev.filter((id) => id !== projectId)
    );
  };

  const handleToggleSelectAll = (checked: boolean) => {
    if (!projects) return;
    setSelectedIds(checked ? projects.map((project) => project.id) : []);
  };

  const allSelected = projects && projects.length > 0 && selectedIds.length === projects.length;

  const handleConfirmDelete = () => {
    if (deleteTarget !== null && deleteTarget.length > 0) {
      deleteMutation.mutate(deleteTarget);
    }
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
      <div className="flex flex-col min-h-[calc(100vh-40px)]">
        <header className="bg-base-100 border-b-3 border-base-content/30 px-6 py-4">
          <h1 className="text-2xl font-heading font-bold">
            全部项目
          </h1>
          <div className="mt-3 flex items-center gap-3">
            <label className="cursor-pointer select-none">
              <input
                type="checkbox"
                checked={Boolean(allSelected)}
                onChange={(e) => handleToggleSelectAll(e.target.checked)}
                disabled={!projects || projects.length === 0}
                className="mr-2 align-middle"
              />
              全选
            </label>
            <button
              type="button"
              className="btn btn-sm btn-error"
              onClick={handleBatchDeleteClick}
              disabled={selectedIds.length === 0}
            >
              批量删除（{selectedIds.length}）
            </button>
          </div>
        </header>

        <main className="flex-1 px-6 py-8">
          <div className="max-w-3xl mx-auto">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12 gap-4">
                <PencilIcon className="w-6 h-6 animate-pulse" aria-hidden="true" />
                <p className="font-heading text-lg text-base-content/70">加载中...</p>
              </div>
            ) : error ? (
              <Card className="text-center py-8">
                <FaceFrownIcon className="w-6 h-6 mx-auto mb-4" aria-hidden="true" />
                <p className="text-error font-bold">加载项目失败，请重试。</p>
              </Card>
            ) : !projects || projects.length === 0 ? (
              <Card className="text-center py-12">
                <DocumentTextIcon className="w-6 h-6 mx-auto mb-4" aria-hidden="true" />
                <p className="text-lg font-heading font-bold mb-2">暂无项目</p>
                <p className="text-base-content/60">开始创作你的第一个故事吧！</p>
              </Card>
            ) : (
              <div className="grid gap-3">
                {projects.map((project) => (
                  <Link
                    key={project.id}
                    to={`/project/${project.id}`}
                    className="block"
                  >
                    <Card className="group transition-transform duration-200 hover:-translate-y-1 cursor-pointer">
                      <div className="flex items-center justify-between">
                        <label
                          className="mr-2 cursor-pointer"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(project.id)}
                            onChange={(e) => handleToggleSelect(project.id, e.target.checked)}
                            onClick={(e) => e.stopPropagation()}
                            onMouseDown={(e) => e.stopPropagation()}
                          />
                        </label>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-heading font-bold truncate">
                              {project.title}
                            </span>
                            <span
                              className={`badge badge-sm font-bold ${
                                project.status === "ready"
                                  ? "bg-success/20 text-success-content"
                                  : project.status === "processing"
                                    ? "bg-warning/20 text-warning-content animate-pulse"
                                    : "bg-neutral/20"
                              }`}
                            >
                              {project.status}
                            </span>
                          </div>
                          {project.story && (
                            <p className="text-sm text-base-content/60 truncate mt-1">
                              {project.story}
                            </p>
                          )}
                        </div>
                        <button
                          className="p-2 opacity-0 group-hover:opacity-100 hover:bg-error/20 rounded-lg transition-all cursor-pointer"
                          onClick={(e) => handleDeleteClick(project.id, e)}
                          title="删除"
                        >
                          <TrashIcon className="w-5 h-5 text-error" />
                        </button>
                      </div>
                    </Card>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* 删除确认弹窗 */}
      <ConfirmModal
        isOpen={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleConfirmDelete}
        title="删除项目"
        message={`确定要删除选中的${deleteTarget ? deleteTarget.length : 0}个项目吗？删除后将无法恢复。`}
        confirmText="删除"
        cancelText="取消"
        variant="danger"
        isLoading={deleteMutation.isPending}
      />
    </AppShell>
  );
}
