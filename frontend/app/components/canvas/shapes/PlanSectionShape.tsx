import {
	HTMLContainer,
	Rectangle2d,
	ShapeUtil,
	T,
	type Geometry2d,
	type RecordProps,
} from "tldraw";
import type {
	PlanSectionShape,
	ReviewedCharacter,
	ReviewedShot,
} from "./types";
import { SectionShell } from "./SectionShell";
import {
	getWorkspaceSectionPlaceholderText,
	getWorkspaceSectionStatusLabel,
} from "~/utils/workspaceStatus";
import { useDomSize, getShapeSize } from "~/hooks/useDomSize";

export class PlanSectionShapeUtil extends ShapeUtil<PlanSectionShape> {
	static override type = "plan-section" as const;

	static override props: RecordProps<PlanSectionShape> = {
		w: T.number,
		h: T.number,
		projectId: T.number,
		story: T.string,
		summary: T.string,
		characters: T.any,
		shots: T.any,
		sectionState: T.string,
		placeholder: T.boolean,
		statusLabel: T.string,
		placeholderText: T.string,
	};

	getDefaultProps(): PlanSectionShape["props"] {
		return {
			w: 920,
			h: 200,
			projectId: 0,
			story: "",
			summary: "",
			characters: [],
			shots: [],
			sectionState: "draft",
			placeholder: true,
			statusLabel: getWorkspaceSectionStatusLabel("draft"),
			placeholderText: getWorkspaceSectionPlaceholderText("plan"),
		};
	}

	override canEdit() {
		return true;
	}
	override canResize() {
		return false;
	}
	override canCull() {
		return false;
	}

	getGeometry(shape: PlanSectionShape): Geometry2d {
		const size = this.editor ? getShapeSize(this.editor, shape.id) : undefined;
		return new Rectangle2d({
			width: shape.props.w,
			height: size?.height ?? shape.props.h,
			isFilled: true,
		});
	}

	component(shape: PlanSectionShape) {
		const {
			w,
			story,
			summary,
			characters,
			shots,
			placeholder,
			placeholderText,
			statusLabel,
		} = shape.props;
		const ref = useDomSize(shape, this.editor ?? null);
		const typedCharacters = characters as ReviewedCharacter[];
		const typedShots = shots as ReviewedShot[];

		return (
			<HTMLContainer
				style={{ width: w, pointerEvents: "all", overflow: "visible" }}
			>
				<div ref={ref} style={{ width: w }}>
					<SectionShell
						sectionKey="plan"
						sectionTitle="编剧规划"
						statusLabel={statusLabel}
						placeholder={placeholder}
						placeholderText={placeholderText}
					>
						<div className="space-y-4">
							{(story || summary) && (
								<div className="rounded-xl bg-secondary/10 p-4">
									{story && (
										<p className="m-0 whitespace-pre-wrap text-sm leading-relaxed text-base-content/80">
											{story}
										</p>
									)}
									{summary && (
										<p className="mt-3 border-t border-base-content/10 pt-3 text-xs leading-relaxed text-base-content/55">
											{summary}
										</p>
									)}
								</div>
							)}
							{typedShots.length > 0 && (
								<div className="overflow-hidden rounded-xl border border-base-content/10">
									<table className="w-full text-xs">
										<thead className="bg-base-200/80">
											<tr>
												<th className="w-10 px-3 py-2 text-left font-semibold">
													#
												</th>
												<th className="px-3 py-2 text-left font-semibold">
													描述
												</th>
												<th className="w-20 px-3 py-2 text-left font-semibold">
													运镜
												</th>
												<th className="w-16 px-3 py-2 text-left font-semibold">
													时长
												</th>
												<th className="w-28 px-3 py-2 text-left font-semibold">
													角色
												</th>
											</tr>
										</thead>
										<tbody>
											{typedShots.map((shot, i) => {
												const characterNames = shot.character_ids
													?.map(
														(id) =>
															typedCharacters.find((c) => c.id === id)?.name,
													)
													.filter(Boolean);
												return (
													<tr
														key={shot.id}
														className={
															i % 2 === 0 ? "bg-base-100" : "bg-base-200/30"
														}
													>
<td className="px-3 py-2 font-mono text-base-content/60 truncate max-w-0">
  {shot.order}
</td>
<td className="px-3 py-2 text-base-content/80 truncate max-w-0">
  {shot.description}
</td>
<td className="px-3 py-2 text-base-content/60 truncate max-w-0">
  {shot.camera || "-"}
</td>
<td className="px-3 py-2 text-base-content/60 truncate max-w-0">
  {shot.duration ? `${shot.duration}s` : "-"}
</td>
<td className="px-3 py-2 text-base-content/60 truncate max-w-0">
  {characterNames?.length
																? characterNames.join("、")
																: "-"}
														</td>
													</tr>
												);
											})}
										</tbody>
									</table>
								</div>
							)}
						</div>
					</SectionShell>
				</div>
			</HTMLContainer>
		);
	}

	indicator(shape: PlanSectionShape) {
		const size = this.editor ? getShapeSize(this.editor, shape.id) : undefined;
		return (
			<rect
				width={shape.props.w}
				height={size?.height ?? shape.props.h}
				rx={24}
			/>
		);
	}
}
