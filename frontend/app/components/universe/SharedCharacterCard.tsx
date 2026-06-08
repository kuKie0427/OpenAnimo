import { Card } from "~/components/ui/Card";
import type { SharedCharacterRead } from "~/types";
import { getStaticUrl } from "~/services/api";
import { UserIcon } from "@heroicons/react/24/outline";

interface SharedCharacterCardProps {
	character: SharedCharacterRead;
	onImport?: (character: SharedCharacterRead) => void;
	showImport?: boolean;
}

export function SharedCharacterCard({
	character,
	onImport,
	showImport = false,
}: SharedCharacterCardProps) {
	const imageUrl = getStaticUrl(character.canonical_image_url);
	const tags = character.character_tags
		? character.character_tags.split(",").map((t) => t.trim())
		: [];

	return (
		<Card className="text-center h-full">
			{/* Avatar */}
			<div className="mb-2">
				{imageUrl ? (
					<div className="w-20 h-20 mx-auto rounded-full overflow-hidden border border-primary/30 shadow-aperture">
						<img
							src={imageUrl}
							alt={character.name}
							className="w-full h-full object-cover"
						/>
					</div>
				) : (
					<div className="w-20 h-20 mx-auto rounded-full bg-base-200 border border-base-content/10 flex items-center justify-center">
						<UserIcon className="w-8 h-8 text-base-content/30" />
					</div>
				)}
			</div>

			{/* Name */}
			<h4 className="font-heading font-bold text-sm">{character.name}</h4>

			{/* Tags */}
			{tags.length > 0 && (
				<div className="flex flex-wrap gap-1 justify-center mt-1 mb-2">
					{tags.slice(0, 3).map((tag) => (
						<span
							key={tag}
							className="px-1.5 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-bold"
						>
							{tag}
						</span>
					))}
				</div>
			)}

			{/* Description */}
			{character.description && (
				<p className="text-xs text-base-content/50 line-clamp-2 mt-1">
					{character.description}
				</p>
			)}

			{/* Version badge */}
			<span className="text-[10px] text-base-content/30 mt-2 inline-block">
				v{character.version}
			</span>

			{/* Import button */}
			{showImport && onImport && (
				<button
					type="button"
					className="btn btn-xs btn-primary mt-2"
					onClick={() => onImport(character)}
				>
					导入
				</button>
			)}
		</Card>
	);
}
