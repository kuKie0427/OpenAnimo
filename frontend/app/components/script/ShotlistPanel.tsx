import { clsx } from 'clsx';
import { Button } from '~/components/ui/Button';
import { getStaticUrl } from '~/services/api';

export interface ShotSyncItem {
  shot_id: number;
  paragraph_index: number;
  shot_order: number;
  shot_description: string;
  shot_image_url: string | null;
  is_synced: boolean;
}

export interface ShotlistPanelProps {
  shots: ShotSyncItem[];
  selectedShotId?: number | null;
  onSelectShot?: (shotId: number) => void;
  onSyncParagraph?: () => void;
  isSyncing?: boolean;
}

export function ShotlistPanel({
  shots,
  selectedShotId,
  onSelectShot,
  onSyncParagraph,
  isSyncing = false,
}: ShotlistPanelProps) {
  return (
    <div
      data-testid="shotlist-panel"
      className="w-80 h-full overflow-y-auto bg-base-200 border-l border-base-content/10 flex flex-col"
    >
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-base-content/10">
        <h3 className="font-heading text-sm text-base-content">分镜预览</h3>
        {shots.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            loading={isSyncing}
            onClick={onSyncParagraph}
            data-testid="shotlist-sync-btn"
            className="!px-2.5 !py-1 !min-h-0 !text-sm"
          >
            {isSyncing ? '同步中...' : '🔄 同步'}
          </Button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {shots.length === 0 ? (
          <div
            data-testid="shotlist-empty"
            className="py-8 text-center text-sm text-base-content/40"
          >
            该段落无对应分镜
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {shots.map((shot) => {
              const isSelected = shot.shot_id === selectedShotId;
              const imageUrl = getStaticUrl(shot.shot_image_url);

              return (
                <button
                  key={shot.shot_id}
                  data-testid={`shot-card-${shot.shot_id}`}
                  type="button"
                  onClick={() => onSelectShot?.(shot.shot_id)}
                  className={clsx(
                    'text-left rounded-lg p-2 border transition-all duration-200',
                    'bg-base-300 cursor-pointer',
                    isSelected
                      ? 'border-primary/30 ring-2 ring-primary'
                      : 'border-base-content/10 hover:border-base-content/20',
                  )}
                >
                  <div className="relative aspect-[4/3] rounded overflow-hidden bg-base-200">
                    {imageUrl ? (
                      <img
                        src={imageUrl}
                        alt={shot.shot_description}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-base-content/20 text-xs">
                        无图片
                      </div>
                    )}
                    <span className="absolute top-1 left-1 bg-primary/80 text-primary-content text-xs px-1 rounded">
                      {shot.shot_order}
                    </span>
                  </div>

                  <p className="mt-1.5 text-xs text-base-content/80 line-clamp-2 leading-relaxed">
                    {shot.shot_description || '无描述'}
                  </p>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {isSyncing && (
        <div className="flex items-center justify-center gap-2 py-2 border-t border-base-content/10">
          <span className="w-4 h-4 rounded-full border-2 border-base-content/15 border-t-primary animate-spin" />
          <span className="text-xs text-base-content/60">同步中...</span>
        </div>
      )}
    </div>
  );
}
