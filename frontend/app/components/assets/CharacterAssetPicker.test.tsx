import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { CharacterAssetPicker } from "./CharacterAssetPicker";
import { fetchApi } from "~/services/api";

vi.mock("~/services/api");

/* ── sample data ──────────────────────────────────────────── */

const ENTRY = (id: number) => ({
	id,
	image_url: `https://img.test/asset-${id}.png`,
	is_approved: true,
	prompt: `prompt-${id}`,
});

const FULL_MATRIX = {
	front: {
		smile: ENTRY(1),
		angry: null,
		crying: null,
		surprised: ENTRY(4),
	},
	side: {
		smile: null,
		angry: ENTRY(6),
		crying: null,
		surprised: null,
	},
	back: {
		smile: null,
		angry: null,
		crying: ENTRY(11),
		surprised: null,
	},
	three_quarter: {
		smile: null,
		angry: null,
		crying: null,
		surprised: ENTRY(16),
	},
};

/* ── tests ────────────────────────────────────────────────── */

describe("CharacterAssetPicker", () => {
	const mockedFetchApi = vi.mocked(fetchApi);

	beforeEach(() => {
		mockedFetchApi.mockReset();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("renders loading state initially", () => {
		mockedFetchApi.mockReturnValue(new Promise(() => {}));
		render(<CharacterAssetPicker characterId={1} />);
		expect(screen.getByText("加载中…")).toBeInTheDocument();
	});

	it("renders error state when API fails", async () => {
		mockedFetchApi.mockRejectedValue(new Error("网络错误"));
		render(<CharacterAssetPicker characterId={1} />);

		await waitFor(() => {
			expect(screen.getByText(/网络错误/)).toBeInTheDocument();
		});
		expect(screen.getByRole("button", { name: /重试/i })).toBeInTheDocument();
	});

	it("renders empty state when matrix is null", async () => {
		mockedFetchApi.mockResolvedValue(null as never);
		render(<CharacterAssetPicker characterId={1} />);

		await waitFor(() => {
			expect(screen.getByText("暂无资产")).toBeInTheDocument();
		});
	});

	it("renders 4x4 grid with assets", async () => {
		mockedFetchApi.mockResolvedValue(FULL_MATRIX as never);
		render(<CharacterAssetPicker characterId={1} />);

		await waitFor(() => {
			expect(screen.getAllByRole("button")).toHaveLength(16);
		});

		expect(screen.getByRole("img", { name: /正面 · 微笑/i })).toHaveAttribute(
			"src",
			"https://img.test/asset-1.png",
		);
		expect(screen.getByRole("img", { name: /侧面 · 愤怒/i })).toHaveAttribute(
			"src",
			"https://img.test/asset-6.png",
		);
	});

	it("calls onSelect when an asset cell is clicked", async () => {
		const user = userEvent.setup();
		const onSelect = vi.fn();
		mockedFetchApi.mockResolvedValue(FULL_MATRIX as never);

		render(
			<CharacterAssetPicker
				characterId={1}
				onSelect={onSelect}
			/>,
		);

		await waitFor(() => {
			expect(screen.getAllByRole("button")).toHaveLength(16);
		});

		const cell = screen.getByRole("img", { name: /正面 · 微笑/i }).closest("button")!;
		await user.click(cell);

		expect(onSelect).toHaveBeenCalledTimes(1);
		expect(onSelect).toHaveBeenCalledWith(1);
	});

	it("does not call onSelect when a null cell is clicked", async () => {
		const user = userEvent.setup();
		const onSelect = vi.fn();
		mockedFetchApi.mockResolvedValue(FULL_MATRIX as never);

		render(
			<CharacterAssetPicker
				characterId={1}
				onSelect={onSelect}
			/>,
		);

		await waitFor(() => {
			expect(screen.getAllByRole("button")).toHaveLength(16);
		});

		const labels = screen.getAllByText("正面 · 愤怒");
		const cell = labels[0].closest("button")!;
		expect(cell).toBeDisabled();

		await user.click(cell);
		expect(onSelect).not.toHaveBeenCalled();
	});

	it("highlights the selected asset", async () => {
		mockedFetchApi.mockResolvedValue(FULL_MATRIX as never);

		render(
			<CharacterAssetPicker
				characterId={1}
				selectedAssetId={1}
			/>,
		);

		await waitFor(() => {
			expect(screen.getAllByRole("button")).toHaveLength(16);
		});

		const cell = screen.getByRole("img", { name: /正面 · 微笑/i }).closest("button")!;
		expect(cell.className).toContain("ring-primary");
		expect(cell.className).toContain("border-primary");
	});
});
