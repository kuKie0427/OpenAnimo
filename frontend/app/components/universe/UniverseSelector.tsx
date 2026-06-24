import { useState, useEffect } from "react";
import { universesApi } from "~/services/api";
import type { Universe } from "~/types";

interface UniverseSelectorProps {
	value: number | null;
	onChange: (universeId: number | null) => void;
	className?: string;
}

export function UniverseSelector({
	value,
	onChange,
	className = "",
}: UniverseSelectorProps) {
	const [universes, setUniverses] = useState<Universe[]>([]);
	const [loading, setLoading] = useState(false);

	useEffect(() => {
		let cancelled = false;
		setLoading(true);
		universesApi
			.list()
			.then((data) => {
				if (!cancelled) setUniverses(data);
			})
			.catch(() => {})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});
		return () => {
			cancelled = true;
		};
	}, []);

	if (loading) {
		return (
			<select className="select select-bordered select-sm bg-base-200" disabled>
				<option>加载中...</option>
			</select>
		);
	}

	if (universes.length === 0) {
		return (
			<p className="text-xs text-base-content/40">暂无 IP 宇宙</p>
		);
	}

	return (
		<select
			className={`select select-bordered select-sm bg-base-200 ${className}`}
			value={value ?? ""}
			onChange={(e) => {
				const val = e.target.value;
				onChange(val ? Number(val) : null);
			}}
		>
			<option value="">不关联宇宙</option>
			{universes.map((u) => (
				<option key={u.id} value={u.id}>
					{u.name}（{u.projects_count} 章 / {u.shared_characters_count} 角色）
				</option>
			))}
		</select>
	);
}
