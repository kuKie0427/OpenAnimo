import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EntityApprovalCard } from "./EntityApprovalCard";
import type { EntitySummary, EntityDecision } from "~/types";

const mockEntities: EntitySummary[] = [
	{ entity_id: 1, entity_name: "亚瑟", description: "战士，30岁", image_url: "/arthur.jpg", approval_state: "draft" },
	{ entity_id: 2, entity_name: "梅林", description: "法师，白发", image_url: null, approval_state: "draft" },
	{ entity_id: 3, entity_name: "兰斯", description: "骑士，金发", image_url: "/lance.jpg", approval_state: "draft" },
	{ entity_id: 4, entity_name: "女巫", description: "暗影，黑发", image_url: null, approval_state: "draft" },
	{ entity_id: 5, entity_name: "国王", description: "统治者，...", image_url: "/king.jpg", approval_state: "draft" },
];

describe("EntityApprovalCard", () => {
	it("renders 5 entity rows with correct title", () => {
		render(
			<EntityApprovalCard
				entityType="character"
				entityLabel="角色"
				entities={mockEntities}
				onConfirm={vi.fn()}
				onRegenerate={vi.fn()}
			/>
		);

		expect(screen.getByText(/角色审批.*5.*5.*已确认/)).toBeInTheDocument();

		mockEntities.forEach((e) => {
			expect(screen.getByText(e.entity_name)).toBeInTheDocument();
		});
	});

	it("rejecting one entity changes count to 4/5", () => {
		render(
			<EntityApprovalCard
				entityType="character"
				entityLabel="角色"
				entities={mockEntities}
				onConfirm={vi.fn()}
				onRegenerate={vi.fn()}
			/>
		);

		expect(screen.getByText(/角色审批.*5.*5.*已确认/)).toBeInTheDocument();

		const rejectButtons = screen.getAllByLabelText("拒绝");
		fireEvent.click(rejectButtons[0]);

		expect(screen.getByText(/角色审批.*4.*5.*已确认/)).toBeInTheDocument();
	});

	it("'全部通过' sets all approved", () => {
		render(
			<EntityApprovalCard
				entityType="character"
				entityLabel="角色"
				entities={mockEntities}
				onConfirm={vi.fn()}
				onRegenerate={vi.fn()}
			/>
		);

		const rejectButtons = screen.getAllByLabelText("拒绝");
		fireEvent.click(rejectButtons[0]);
		expect(screen.getByText(/角色审批.*4.*5.*已确认/)).toBeInTheDocument();

		fireEvent.click(screen.getByText("全部通过"));

		expect(screen.getByText(/角色审批.*5.*5.*已确认/)).toBeInTheDocument();
	});

	it("'全部拒绝' sets all rejected", () => {
		render(
			<EntityApprovalCard
				entityType="character"
				entityLabel="角色"
				entities={mockEntities}
				onConfirm={vi.fn()}
				onRegenerate={vi.fn()}
			/>
		);

		fireEvent.click(screen.getByText("全部拒绝"));

		expect(screen.getByText(/角色审批.*0.*5.*已确认/)).toBeInTheDocument();
	});

	it("calls onConfirm with all decisions when confirm is clicked", () => {
		const onConfirm = vi.fn();
		render(
			<EntityApprovalCard
				entityType="character"
				entityLabel="角色"
				entities={mockEntities}
				onConfirm={onConfirm}
				onRegenerate={vi.fn()}
			/>
		);

		fireEvent.click(screen.getByText("确认并继续 →"));

		expect(onConfirm).toHaveBeenCalledTimes(1);
		const decisions = onConfirm.mock.calls[0][0] as EntityDecision[];
		expect(decisions).toHaveLength(5);
		expect(decisions[0]).toMatchObject({ entity_id: 1, approved: true });
		expect(decisions[1]).toMatchObject({ entity_id: 2, approved: true });
	});

	it("expand feedback shows textarea", () => {
		render(
			<EntityApprovalCard
				entityType="character"
				entityLabel="角色"
				entities={mockEntities}
				onConfirm={vi.fn()}
				onRegenerate={vi.fn()}
			/>
		);

		expect(screen.queryByPlaceholderText("对此实体的修改意见...")).not.toBeInTheDocument();

		const addFeedbackButtons = screen.getAllByText("添加反馈");
		fireEvent.click(addFeedbackButtons[0]);

		const textarea = screen.getByPlaceholderText("对此实体的修改意见...");
		expect(textarea).toBeInTheDocument();

		fireEvent.change(textarea, { target: { value: "需要更详细描述" } });

		const collapseButtons = screen.getAllByText("收起反馈");
		fireEvent.click(collapseButtons[0]);

		expect(screen.queryByPlaceholderText("对此实体的修改意见...")).not.toBeInTheDocument();
	});
});
