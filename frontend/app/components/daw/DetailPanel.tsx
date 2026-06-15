import { DocumentTextIcon } from "@heroicons/react/24/outline";
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
}

export function DetailPanel({ item, onEdit, onRegenerate }: DetailPanelProps) {
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
    </div>
  );
}
