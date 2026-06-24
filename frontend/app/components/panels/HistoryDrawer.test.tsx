import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HistoryDrawer } from "./HistoryDrawer";
import { projectsApi } from "~/services/api";

vi.mock("~/services/api", () => ({
	projectsApi: {
		list: vi.fn(),
		deleteMany: vi.fn(),
		update: vi.fn(),
	},
}));

vi.mock("~/utils/toast", () => ({
	toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("~/features/projects/deleteProject", () => ({
	cleanupDeletedProjectCaches: vi.fn(),
}));

vi.mock("~/components/ui/SvgIcon", () => ({
	SvgIcon: ({ name, size }: any) => <span data-testid={`icon-${name}`} data-size={size} />,
}));

vi.mock("~/components/ui/ConfirmModal", () => ({
	ConfirmModal: ({ isOpen, onConfirm, onClose, confirmText, cancelText }: any) =>
		isOpen ? (
			<div data-testid="confirm-modal">
				<button onClick={onConfirm}>{confirmText}</button>
				<button onClick={onClose}>{cancelText}</button>
			</div>
		) : null,
}));

const mockProjects = [
	{
		id: 1,
		title: "测试项目A",
		status: "completed",
		updated_at: "2026-05-01T10:00:00Z",
		style: "comic",
		target_shot_count: 6,
	},
	{
		id: 2,
		title: "测试项目B",
		status: "draft",
		updated_at: "2026-05-02T10:00:00Z",
		style: null,
		target_shot_count: null,
	},
	{
		id: 3,
		title: "测试项目C",
		status: "processing",
		updated_at: "2026-05-03T10:00:00Z",
		style: "anime",
		target_shot_count: 8,
	},
];

function renderDrawer(props = {} as any) {
	const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	return render(
		<QueryClientProvider client={qc}>
			<HistoryDrawer open onClose={vi.fn()} onNavigate={vi.fn()} {...props} />
		</QueryClientProvider>,
	);
}

describe("HistoryDrawer", () => {
	beforeEach(() => {
		vi.mocked(projectsApi.list).mockResolvedValue(mockProjects as any);
		vi.mocked(projectsApi.deleteMany).mockResolvedValue(undefined as any);
		vi.mocked(projectsApi.update).mockResolvedValue({} as any);
	});

	it("renders project list", async () => {
		renderDrawer();
		expect(await screen.findByText("测试项目A")).toBeInTheDocument();
		expect(screen.getByText("测试项目B")).toBeInTheDocument();
		expect(screen.getByText("测试项目C")).toBeInTheDocument();
	});

	it("shows empty state when no projects", async () => {
		vi.mocked(projectsApi.list).mockResolvedValue([]);
		renderDrawer();
		expect(await screen.findByText("还没有项目")).toBeInTheDocument();
	});

	it("toggles individual selection via checkbox", async () => {
		renderDrawer();
		const checkboxes = await screen.findAllByRole("checkbox");
		expect(checkboxes.length).toBeGreaterThanOrEqual(4);
		fireEvent.click(checkboxes[1]);
		expect(checkboxes[1]).toBeChecked();
	});

	it("selects all projects via 全选 checkbox", async () => {
		renderDrawer();
		const allCheckbox = await screen.findByText("全选");
		fireEvent.click(allCheckbox.closest("label")!.querySelector("input")!);
		const checkboxes = screen.getAllByRole("checkbox");
		checkboxes.forEach((cb) => expect(cb).toBeChecked());
	});

	it("shows batch delete button when items selected", async () => {
		renderDrawer();
		const checkboxes = await screen.findAllByRole("checkbox");
		fireEvent.click(checkboxes[1]);
		expect(screen.getByText(/删除/)).toBeInTheDocument();
	});

	it("opens rename input on pencil click", async () => {
		renderDrawer();
		const pencilButtons = await screen.findAllByTitle("重命名");
		fireEvent.click(pencilButtons[0]);
		expect(screen.getByDisplayValue("测试项目A")).toBeInTheDocument();
	});

	it("confirms rename on Enter key", async () => {
		renderDrawer();
		const pencilButtons = await screen.findAllByTitle("重命名");
		fireEvent.click(pencilButtons[0]);
		const input = screen.getByDisplayValue("测试项目A");
		fireEvent.change(input, { target: { value: "新名称" } });
		fireEvent.keyDown(input, { key: "Enter" });
		await waitFor(() => {
			expect(projectsApi.update).toHaveBeenCalledWith(1, { title: "新名称" });
		});
		await waitFor(() => {
			expect(screen.queryByDisplayValue("新名称")).not.toBeInTheDocument();
		});
	});

	it("cancels rename on Escape key", async () => {
		renderDrawer();
		const pencilButtons = await screen.findAllByTitle("重命名");
		fireEvent.click(pencilButtons[0]);
		const input = screen.getByDisplayValue("测试项目A");
		fireEvent.keyDown(input, { key: "Escape" });
		expect(screen.queryByDisplayValue("测试项目A")).not.toBeInTheDocument();
	});

	it("deletes selected projects via confirm modal", async () => {
		renderDrawer();
		const checkboxes = await screen.findAllByRole("checkbox");
		fireEvent.click(checkboxes[1]);
		fireEvent.click(checkboxes[2]);
		const deleteBtn = screen.getByRole("button", { name: /删除/ });
		fireEvent.click(deleteBtn);
		const modal = await screen.findByTestId("confirm-modal");
		expect(modal).toBeInTheDocument();
		const buttons = screen.getAllByText("删除");
		fireEvent.click(buttons[buttons.length - 1]);
		await waitFor(() => {
			expect(projectsApi.deleteMany).toHaveBeenCalled();
		});
		await waitFor(() => {
			expect(screen.queryByTestId("confirm-modal")).not.toBeInTheDocument();
		});
	});

	it("navigates on project click", async () => {
		const onNavigate = vi.fn();
		const onClose = vi.fn();
		renderDrawer({ onNavigate, onClose });
		const title = await screen.findByText("测试项目A");
		fireEvent.click(title);
		expect(onNavigate).toHaveBeenCalledWith(1);
		expect(onClose).toHaveBeenCalled();
	});
});
