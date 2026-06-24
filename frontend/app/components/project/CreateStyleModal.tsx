import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { styleTemplatesApi } from "~/services/api";
import { Modal } from "~/components/ui/Modal";
import { Button } from "~/components/ui/Button";
import { Input } from "~/components/ui/Input";
import { toast } from "~/utils/toast";
import type { StyleTemplateCreatePayload } from "~/types";

interface CreateStyleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated?: (slug: string) => void;
}

export function CreateStyleModal({ isOpen, onClose, onCreated }: CreateStyleModalProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<StyleTemplateCreatePayload>({
    name: "",
    slug: "",
    style_prompt: "",
    description: "",
    color_palette: [],
    negative_prompt: "",
  });
  const [tagInput, setTagInput] = useState("");

  const slugify = (name: string) =>
    name
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 40);

  const createMutation = useMutation({
    mutationFn: styleTemplatesApi.create,
    onSuccess: (template) => {
      queryClient.invalidateQueries({ queryKey: ["style-templates"] });
      toast.success({ title: "风格创建成功", message: template.name });
      onCreated?.(template.slug);
      // Reset form
      setForm({ name: "", slug: "", style_prompt: "", description: "", color_palette: [], negative_prompt: "" });
      setTagInput("");
      onClose();
    },
    onError: (error: Error) => {
      toast.error({ title: "创建失败", message: error.message || "未知错误" });
    },
  });

  const addTag = () => {
    const tag = tagInput.trim();
    if (tag && !(form.color_palette ?? []).includes(tag)) {
      setForm({ ...form, color_palette: [...(form.color_palette ?? []), tag] });
      setTagInput("");
    }
  };

  const removeTag = (tag: string) => {
    setForm({ ...form, color_palette: (form.color_palette ?? []).filter((t) => t !== tag) });
  };

  const handleNameChange = (name: string) => {
    setForm({ ...form, name, slug: slugify(name) });
  };

  const handleSubmit = () => {
    if (!form.name.trim() || !form.slug.trim() || !form.style_prompt.trim()) return;
    createMutation.mutate(form);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="创建自定义风格"
      actions={
        <Button
          variant="primary"
          onClick={handleSubmit}
          loading={createMutation.isPending}
          disabled={!form.name.trim() || !form.slug.trim() || !form.style_prompt.trim()}
        >
          创建
        </Button>
      }
    >
      <div className="space-y-4">
        <Input
          label="风格名称"
          placeholder="如：赛博朋克"
          value={form.name}
          onChange={(e) => handleNameChange(e.target.value)}
        />
        <Input
          label="Slug（URL标识）"
          placeholder="auto-generated"
          value={form.slug}
          onChange={(e) => setForm({ ...form, slug: e.target.value })}
        />
        <div className="form-control">
          <label className="label">
            <span className="label-text font-heading font-medium">描述</span>
          </label>
          <textarea
            className="textarea textarea-bordered bg-base-200 h-20"
            placeholder="简要描述风格特点..."
            value={form.description ?? ""}
            onChange={(e) => setForm({ ...form, description: e.target.value || null })}
          />
        </div>
        <Input
          label="风格提示词 (Style Prompt)"
          placeholder="如：cyberpunk, neon lights, dark urban..."
          value={form.style_prompt}
          onChange={(e) => setForm({ ...form, style_prompt: e.target.value })}
        />
        <Input
          label="负面提示词 (Negative Prompt)"
          placeholder="如：bright, sunny, cheerful（可选）"
          value={form.negative_prompt ?? ""}
          onChange={(e) => setForm({ ...form, negative_prompt: e.target.value || null })}
        />
        {/* Color palette tags */}
        <div className="form-control">
          <label className="label">
            <span className="label-text font-heading font-medium">色调关键词</span>
          </label>
          <div className="flex gap-2">
            <input
              className="input input-bordered bg-base-200 flex-1"
              placeholder="如：neon, dark, futuristic"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addTag();
                }
              }}
            />
            <Button variant="ghost" size="sm" onClick={addTag} type="button">
              添加
            </Button>
          </div>
          {(form.color_palette ?? []).length > 0 && (
            <div className="flex gap-1 mt-2 flex-wrap">
              {(form.color_palette ?? []).map((tag) => (
                <span key={tag} className="badge badge-sm badge-outline gap-1">
                  {tag}
                  <button
                    type="button"
                    className="hover:text-error"
                    onClick={() => removeTag(tag)}
                    aria-label={`移除 ${tag}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
