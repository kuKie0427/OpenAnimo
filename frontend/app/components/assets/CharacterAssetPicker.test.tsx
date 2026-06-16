import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { CharacterAssetPicker } from "./CharacterAssetPicker";

vi.mock("~/utils/runtimeBase", () => ({
	getApiBase: () => "http://localhost:18765",
}));

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

/* ── helpers ──────────────────────────────────────────────── */

function jsonResponse(data: unknown, ok = true, status = 200) {
	return {
		ok,
		status,
		json: () => Promise.resolve(data),
	} as Response;
}

function errorResponse(status = 500) {
	return jsonResponse(null, false, status);
}

/* ── tests ────────────────────────────────────────────────── */

describe("CharacterAssetPicker", () => {
	const fetchSpy = vi.fn<typeof fetch>();

	beforeEach(() => {
		fetchSpy.mockReset();
		vi.stubGlobal("fetch", fetchSpy);
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("renders loading state initially", () => {
		fetchSpy.mockReturnValue(new Promise(() => {}));
		render(<CharacterAssetPicker characterId={1} />);
		expect(screen.getByText("加载中…")).toBeInTheDocument();
	});

	it("renders error state when API fails", async () => {
		fetchSpy.mockResolvedValue(errorResponse(500));
		render(<CharacterAssetPicker characterId={1} />);

		await waitFor(() => {
			expect(screen.getByText(/请求失败/)).toBeInTheDocument();
		});
		expect(screen.getByRole("button", { name: /重试/i })).toBeInTheDocument();
	});

	it("renders empty state when matrix is null", async () => {
		fetchSpy.mockResolvedValue(jsonResponse(null));
		render(<CharacterAssetPicker characterId={1} />);

		await waitFor(() => {
			expect(screen.getByText("暂无资产")).toBeInTheDocument();
		});
	});

	it("renders 4x4 grid with assets", async () => {
		fetchSpy.mockResolvedValue(jsonResponse(FULL_MATRIX));
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
		fetchSpy.mockResolvedValue(jsonResponse(FULL_MATRIX));

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
		fetchSpy.mockResolvedValue(jsonResponse(FULL_MATRIX));

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
		fetchSpy.mockResolvedValue(jsonResponse(FULL_MATRIX));

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
