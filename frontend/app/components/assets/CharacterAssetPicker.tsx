import { useCallback, useEffect, useState } from "react";
import { clsx } from "clsx";
import { fetchApi } from "~/services/api";

interface CharacterAssetEntry {
	id: number;
	image_url: string | null;
	is_approved: boolean;
	prompt: string | null;
}

type Emotion = "smile" | "angry" | "crying" | "surprised";
type Angle = "front" | "side" | "back" | "three_quarter";

type AssetMatrix = Record<Angle, Record<Emotion, CharacterAssetEntry | null>>;

interface CharacterAssetPickerProps {
	characterId: number;
	onSelect?: (assetId: number) => void;
	selectedAssetId?: number;
}

const ANGLE_ORDER: Angle[] = ["front", "side", "back", "three_quarter"];
const EMOTION_ORDER: Emotion[] = ["smile", "angry", "crying", "surprised"];

const ANGLE_LABELS: Record<Angle, string> = {
	front: "正面",
	side: "侧面",
	back: "背面",
	three_quarter: "斜侧",
};

const EMOTION_LABELS: Record<Emotion, string> = {
	smile: "微笑",
	angry: "愤怒",
	crying: "哭泣",
	surprised: "惊讶",
};

export function CharacterAssetPicker({
	characterId,
	onSelect,
	selectedAssetId,
}: CharacterAssetPickerProps) {
	const [matrix, setMatrix] = useState<AssetMatrix | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchMatrix = useCallback(async () => {
		setLoading(true);
		setError(null);

		try {
			const data = await fetchApi<AssetMatrix>(
				`/api/v1/characters/${characterId}/assets/matrix`,
			);
			setMatrix(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "加载失败");
		} finally {
			setLoading(false);
		}
	}, [characterId]);

	useEffect(() => {
		fetchMatrix();
	}, [fetchMatrix]);

	if (loading) {
		return (
			<div className="flex flex-col items-center justify-center py-12 gap-3">
				<span className="loading loading-spinner loading-lg text-primary" />
				<p className="text-sm text-base-content/60 font-sans">加载中…</p>
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex flex-col items-center justify-center py-12 gap-3">
				<p className="text-sm text-error font-sans">{error}</p>
				<button
					type="button"
					className="btn-projection text-xs px-4 py-1.5"
					onClick={fetchMatrix}
				>
					重试
				</button>
			</div>
		);
	}

	if (!matrix) {
		return (
			<div className="flex flex-col items-center justify-center py-12 gap-2">
				<p className="text-sm text-base-content/40 font-sans">暂无资产</p>
			</div>
		);
	}

	return (
		<div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
			{ANGLE_ORDER.map((angle) =>
				EMOTION_ORDER.map((emotion) => {
					const entry = matrix[angle]?.[emotion];
					const isSelected = entry != null && entry.id === selectedAssetId;

					return (
						<button
							key={`${angle}-${emotion}`}
							type="button"
							disabled={!entry}
							onClick={() => {
								if (entry && onSelect) {
									onSelect(entry.id);
								}
							}}
							className={clsx(
								"group relative flex flex-col items-center gap-1.5 rounded-lg border transition-all duration-fast",
								entry
									? "cursor-pointer hover:shadow-beam"
									: "cursor-not-allowed opacity-30",
								isSelected
									? "border-primary ring-2 ring-primary shadow-gate-glow"
									: "border-base-content/10 hover:border-primary/40",
							)}
						>
							<div className="w-full aspect-square overflow-hidden rounded-t-lg bg-base-300">
								{entry?.image_url ? (
									<img
										src={entry.image_url}
										alt={`${ANGLE_LABELS[angle]} · ${EMOTION_LABELS[emotion]}`}
										className="w-full h-full object-cover rounded transition-transform duration-fast group-hover:scale-105"
										loading="lazy"
									/>
								) : (
									<div className="w-full h-full flex items-center justify-center text-base-content/20 text-xs">
										—
									</div>
								)}
							</div>

							<span className="text-[11px] text-base-content/50 font-sans pb-1.5 leading-tight">
								{ANGLE_LABELS[angle]} · {EMOTION_LABELS[emotion]}
							</span>
						</button>
					);
				}),
			)}
		</div>
	);
}
