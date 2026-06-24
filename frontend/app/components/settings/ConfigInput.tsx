import { useState } from "react";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { configApi } from "~/services/api";
import type { ConfigItem } from "~/types";
import { SvgIcon } from "~/components/ui/SvgIcon";

interface ConfigInputProps {
	item: ConfigItem;
	value: string;
	onChange: (
		e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
	) => void;
}

export function ConfigInput({ item, value, onChange }: ConfigInputProps) {
	const [isRevealed, setIsRevealed] = useState(false);
	const [isRevealing, setIsRevealing] = useState(false);

	const isSensitive = item.is_sensitive;
	const isMasked = item.is_masked;

	// 切换显示/隐藏
	const handleToggleReveal = async () => {
		if (isRevealed) {
			// 当前是显示状态，切换为隐藏
			setIsRevealed(false);
		} else {
			// 当前是隐藏状态，调用 API 获取真实值
			setIsRevealing(true);
			try {
				const result = await configApi.revealValue(item.key);
				setIsRevealed(true);
				// 同步真实值到 formState，使后续编辑生效
				if (result.value !== null) {
					onChange({
						target: { name: item.key, value: result.value },
					} as React.ChangeEvent<HTMLInputElement>);
				}
			} catch (error) {
				console.error("Failed to reveal value:", error);
				alert("获取真实值失败，请检查网络连接");
			} finally {
				setIsRevealing(false);
			}
		}
	};

	// 敏感字段特殊处理
	if (isSensitive) {
		// 揭示后用 formState 的 value（可编辑），未揭示时显示脱敏值
		const displayValue = isRevealed ? value : isMasked ? value : "••••••••";

		return (
			<div className="space-y-2">
				<div className="relative">
					<input
						id={item.key}
						name={item.key}
						type="text"
						value={displayValue}
						onChange={onChange}
						className="input input-bordered w-full border border-base-content/30 font-mono pr-12"
						autoComplete="off"
						placeholder={isRevealed ? "输入新值..." : ""}
					/>
					<button
						type="button"
						onClick={handleToggleReveal}
						disabled={isRevealing}
						className="absolute inset-y-0 right-0 flex items-center pr-3 text-base-content/60 hover:text-accent transition-colors"
						title={isRevealed ? "隐藏真实值" : "显示真实值"}
					>
						{isRevealing ? (
							<span className="loading loading-spinner loading-xs"></span>
						) : isRevealed ? (
							<EyeSlashIcon className="w-5 h-5" />
						) : (
							<EyeIcon className="w-5 h-5" />
						)}
					</button>
				</div>
				{!isRevealed && isMasked && (
					<p className="text-xs text-base-content/50">
						已配置（显示脱敏值），点击眼睛图标可查看真实值
					</p>
				)}
				{isRevealed && (
					<p className="text-xs text-warning inline-flex items-center gap-1">
						<SvgIcon name="triangle-alert" size={12} />
						真实值已显示，请注意保护隐私
					</p>
				)}
			</div>
		);
	}

	// 普通文本输入框
	return (
		<input
			id={item.key}
			name={item.key}
			type="text"
			value={value}
			onChange={onChange}
			className="input input-bordered w-full border border-base-content/30 font-mono"
			autoComplete="off"
		/>
	);
}
