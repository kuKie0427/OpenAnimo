import { render, screen, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CritiqueResultCard } from "./CritiqueResultCard";
import type { CritiqueReviewEventData } from "~/types";

const mockSetCritiqueOverride = vi.fn();
const mockClearCritiqueReview = vi.fn();
const mockOnConfirm = vi.fn();
const mockOnCancel = vi.fn();

const mockCritiqueOverrides: Record<number, boolean> = {};

vi.mock("~/stores/editorStore", () => ({
	useEditorStore: (selector: any) => {
		const state = {
			critiqueOverrides: mockCritiqueOverrides,
			setCritiqueOverride: mockSetCritiqueOverride,
			clearCritiqueReview: mockClearCritiqueReview,
		};
		return selector ? selector(state) : state;
	},
}));

vi.mock("recharts", async () => {
	const actual = await vi.importActual("recharts");
	return {
		...actual,
		ResponsiveContainer: ({ children }: any) => (
			<div data-testid="responsive-container">{children}</div>
		),
	};
});

const characterResults: CritiqueReviewEventData = {
	entity_type: "character",
	total: 3,
	results: [
		{
			entity_id: 1,
			entity_name: "Alice",
			score: 8.5,
			dimensions: { consistency: 8, quality: 9, composition: 8 },
			issues: [],
			suggestions: ["增加表情变化"],
			will_regenerate: false,
			failed_checks: [],
			image_url: "/img/alice.png",
		},
		{
			entity_id: 2,
			entity_name: "Bob",
			score: 4.0,
			dimensions: { consistency: 3, quality: 4, composition: 5 },
			issues: ["面部不一致"],
			suggestions: ["参考角色描述"],
			will_regenerate: true,
			failed_checks: ["consistency"],
			image_url: null,
		},
		{
			entity_id: 3,
			entity_name: "Charlie",
			score: 6.5,
			dimensions: { consistency: 6, quality: 7, composition: 6 },
			issues: [],
			suggestions: [],
			will_regenerate: false,
			failed_checks: [],
			image_url: "/img/charlie.png",
		},
	],
};

describe("CritiqueResultCard", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		Object.keys(mockCritiqueOverrides).forEach(
			(key) => delete mockCritiqueOverrides[Number(key)],
		);
	});

	it("renders 3 character review results", () => {
		render(
			<CritiqueResultCard
				data={characterResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		expect(screen.getByText("审查完成 — 3 个角色")).toBeInTheDocument();
		expect(screen.getByText("Alice")).toBeInTheDocument();
		expect(screen.getByText("Bob")).toBeInTheDocument();
		expect(screen.getByText("Charlie")).toBeInTheDocument();
	});

	it("renders 5 shot results with scrolling", () => {
		const shotResults: CritiqueReviewEventData = {
			entity_type: "shot",
			total: 5,
			results: Array.from({ length: 5 }, (_, i) => ({
				entity_id: i + 1,
				entity_name: `分镜 ${i + 1}`,
				score: 7.0,
				dimensions: { consistency: 7, quality: 7, composition: 7 },
				issues: [],
				suggestions: [],
				will_regenerate: false,
				failed_checks: [],
				image_url: null,
			})),
		};

		render(
			<CritiqueResultCard
				data={shotResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		expect(screen.getByText("审查完成 — 5 个分镜")).toBeInTheDocument();
		// All 5 shots visible
		expect(screen.getByText("分镜 1")).toBeInTheDocument();
		expect(screen.getByText("分镜 5")).toBeInTheDocument();

		// Scrolling container exists
		const scrollContainer = document.querySelector(".max-h-80.overflow-y-auto");
		expect(scrollContainer).toBeInTheDocument();
	});

	it("toggle sets override via setCritiqueOverride", () => {
		render(
			<CritiqueResultCard
				data={characterResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		// Find Alice's toggle and click it
		const toggles = screen.getAllByRole("checkbox") as HTMLInputElement[];
		const aliceToggle = toggles[0]; // First entity is Alice
		fireEvent.click(aliceToggle);

		expect(mockSetCritiqueOverride).toHaveBeenCalledWith(1, true);
	});

	it("batch accept all sets ALL entities to pass", () => {
		mockCritiqueOverrides[1] = true;
		mockCritiqueOverrides[2] = true;

		render(
			<CritiqueResultCard
				data={characterResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		fireEvent.click(screen.getByText("全部通过"));

		expect(mockSetCritiqueOverride).toHaveBeenCalledWith(1, false);
		expect(mockSetCritiqueOverride).toHaveBeenCalledWith(2, false);
		expect(mockSetCritiqueOverride).toHaveBeenCalledWith(3, false);
	});

	it("batch accept overrides AI-regenerate entity without prior manual toggle", () => {
		render(
			<CritiqueResultCard
				data={characterResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		fireEvent.click(screen.getByText("全部通过"));

		expect(mockSetCritiqueOverride).toHaveBeenCalledWith(2, false);
	});

	it("batch regenerate all sets all to true", () => {
		render(
			<CritiqueResultCard
				data={characterResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		fireEvent.click(screen.getByText("全部重生成"));

		// setCritiqueOverride called with true for ALL entities
		expect(mockSetCritiqueOverride).toHaveBeenCalledWith(1, true);
		expect(mockSetCritiqueOverride).toHaveBeenCalledWith(2, true);
		expect(mockSetCritiqueOverride).toHaveBeenCalledWith(3, true);
	});

	it("score colors mapped correctly", () => {
		render(
			<CritiqueResultCard
				data={characterResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		// Alice: 8.5 → badge-success (green)
		expect(screen.getByText("8.5")).toHaveClass("badge-success");

		// Bob: 4.0 → badge-error (red)
		expect(screen.getByText("4.0")).toHaveClass("badge-error");

		// Charlie: 6.5 → badge-warning (amber)
		expect(screen.getByText("6.5")).toHaveClass("badge-warning");
	});

	it("image fallback on load error", () => {
		render(
			<CritiqueResultCard
				data={characterResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		// Bob has null image_url → shows fallback with first letter
		expect(screen.getByText("B")).toBeInTheDocument();

		// Alice has image_url → img tag exists
		const aliceImg = document.querySelector(
			'img[alt="Alice"]',
		) as HTMLImageElement;
		expect(aliceImg).toBeInTheDocument();
		expect(aliceImg.src).toContain("/img/alice.png");
	});

	it("confirm button calls onConfirm with overrides", () => {
		mockCritiqueOverrides[1] = true;
		mockCritiqueOverrides[2] = false;

		render(
			<CritiqueResultCard
				data={characterResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		fireEvent.click(screen.getByText("确认并重生成"));

		expect(mockOnConfirm).toHaveBeenCalledWith({ 1: true, 2: false });
	});

	it("empty results shows no-review message", () => {
		const emptyData: CritiqueReviewEventData = {
			entity_type: "character",
			total: 0,
			results: [],
		};

		render(
			<CritiqueResultCard
				data={emptyData}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		expect(screen.getByText(/无需审查/)).toBeInTheDocument();
	});

	it("failed_checks entity shows warning", () => {
		render(
			<CritiqueResultCard
				data={characterResults}
				onConfirm={mockOnConfirm}
				onCancel={mockOnCancel}
			/>,
		);

		// Bob has failed_checks=["consistency"] — need to expand to see details
		// Click "查看问题与建议" button for Bob
		const expandButtons = screen.getAllByText("查看问题与建议");
		// Bob is the second entity
		fireEvent.click(expandButtons[1]);

		// Now check for failed checks badge
		expect(screen.getByText("consistency")).toBeInTheDocument();
		expect(screen.getByText("未通过检查")).toBeInTheDocument();
	});
});
