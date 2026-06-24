import { useState } from "react";
import { DocumentTextIcon } from "@heroicons/react/24/outline";
import { CharacterAssetPicker } from "~/components/assets";
import { Button } from "~/components/ui/Button";

interface DetailPanelProps {
  item: {
    id: number;
    title: string;
    content: string;
    images?: string[];
    videos?: string[];
    metadata?: Record<string, unknown>;
  } | null;
  onEdit?: (id: number) => void;
  onRegenerate?: (id: number) => void;
  characterIds?: number[];
  characterNames?: Record<number, string>;
}

export function DetailPanel({
  item,
  onEdit,
  onRegenerate,
  characterIds,
  characterNames,
}: DetailPanelProps) {
  const [assetOverlayOpen, setAssetOverlayOpen] = useState(false);
  const [selectedCharacterId, setSelectedCharacterId] = useState<
    number | null
  >(null);

  const hasCharacters = characterIds && characterIds.length > 0;

  if (!item) {
    return (
      <div className="flex-1 flex items-center justify-center text-base-content/30">
        <div className="text-center">
          <DocumentTextIcon className="w-12 h-12 mx-auto mb-2" />
          <p className="text-sm">选择一个项目查看详情</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header with title and actions */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-heading">{item.title}</h2>
          <div className="flex gap-2">
            {hasCharacters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSelectedCharacterId(
                    characterIds.length === 1 ? characterIds[0] : null,
                  );
                  setAssetOverlayOpen(true);
                }}
              >
                查看角色资产
              </Button>
            )}
            {onEdit && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onEdit(item.id)}
              >
                编辑
              </Button>
            )}
            {onRegenerate && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => onRegenerate(item.id)}
              >
                重新生成
              </Button>
            )}
          </div>
        </div>

        {/* Content area */}
        <div className="card-screen p-4 mb-4">
          <p className="text-sm whitespace-pre-wrap">{item.content}</p>
        </div>

        {/* Images section */}
        {item.images && item.images.length > 0 && (
          <div className="grid grid-cols-2 gap-2 mb-4">
            {item.images.map((image, index) => (
              <img
                key={index}
                src={image}
                alt={`${item.title} - 图片 ${index + 1}`}
                className="rounded-lg w-full h-auto object-cover"
              />
            ))}
          </div>
        )}

        {/* Videos section */}
        {item.videos && item.videos.length > 0 && (
          <div className="space-y-2 mb-4">
            {item.videos.map((video, index) => (
              <video
                key={index}
                src={video}
                controls
                className="w-full rounded-lg"
              >
                <track kind="captions" />
              </video>
            ))}
          </div>
        )}

        {/* Metadata section */}
        {item.metadata && Object.keys(item.metadata).length > 0 && (
          <div className="card-screen p-4">
            <h3 className="text-sm font-heading mb-2">元数据</h3>
            <dl className="space-y-1">
              {Object.entries(item.metadata).map(([key, value]) => (
                <div key={key} className="flex gap-2 text-sm">
                  <dt className="text-base-content/60">{key}:</dt>
                  <dd className="text-base-content">
                    {typeof value === "string" ? value : JSON.stringify(value)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>

      {assetOverlayOpen && hasCharacters && (
        <div
          className="fixed inset-0 z-[var(--z-modal-backdrop)] flex items-center justify-center"
          role="dialog"
          aria-label="角色资产查看器"
        >
          <div
            className="absolute inset-0 bg-base-content/40 backdrop-blur-sm"
            onClick={() => setAssetOverlayOpen(false)}
          />

          <div className="relative z-10 w-full max-w-4xl max-h-[85vh] mx-4 bg-screen-surface rounded-xl shadow-2xl border border-base-content/10 flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-base-content/10">
              <h3 className="font-heading text-lg">角色资产</h3>
              <button
                type="button"
                className="btn-projection text-base-content/50 hover:text-base-content p-1 rounded-lg hover:bg-base-200 transition-colors cursor-pointer"
                onClick={() => setAssetOverlayOpen(false)}
                aria-label="关闭"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {characterIds.length > 1 && (
              <div className="flex gap-1 px-6 pt-3 pb-0 overflow-x-auto">
                {characterIds.map((charId) => (
                  <button
                    key={charId}
                    type="button"
                    className={`px-3 py-1.5 text-sm font-sans rounded-lg whitespace-nowrap transition-colors cursor-pointer ${
                      selectedCharacterId === charId
                        ? "bg-primary text-primary-content"
                        : "text-base-content/60 hover:bg-base-200 hover:text-base-content"
                    }`}
                    onClick={() => setSelectedCharacterId(charId)}
                  >
                    {characterNames?.[charId] ?? `角色 ${charId}`}
                  </button>
                ))}
              </div>
            )}

            <div className="flex-1 overflow-y-auto px-6 py-4">
              {selectedCharacterId != null ? (
                <CharacterAssetPicker
                  characterId={selectedCharacterId}
                />
              ) : (
                <div className="flex items-center justify-center py-12 text-sm text-base-content/40">
                  选择一个角色查看资产
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
