import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HomePage } from "./HomePage";

const mockMutate = vi.fn();
let mockIsPending = false;

vi.mock("~/services/api", () => ({
  projectsApi: { create: vi.fn() },
}));

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<any>();
  return {
    ...actual,
    useMutation: vi.fn(() => ({
      mutate: mockMutate,
      isPending: mockIsPending,
    })),
    useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
  };
});

vi.mock("~/stores/themeStore", () => ({
  useThemeStore: vi.fn(() => ({ theme: "light", toggleTheme: vi.fn() })),
}));

vi.mock("~/components/layout/DrawerPortal", () => ({
  DrawerPortal: () => null,
}));

vi.mock("~/stores/settingsStore", () => ({
  useSettingsStore: vi.fn(() => ({ openModal: vi.fn() })),
}));

function renderHomePage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("HomePage", () => {
  beforeEach(() => {
    mockMutate.mockClear();
    mockIsPending = false;
  });

  it("renders title and textarea", () => {
    renderHomePage();
    expect(screen.getAllByText("OpenAnimo").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByLabelText("输入你的故事创意")).toBeInTheDocument();
  });

  it("submits story on button click", async () => {
    renderHomePage();
    const textarea = screen.getByLabelText("输入你的故事创意");
    fireEvent.change(textarea, { target: { value: "My story" } });
    fireEvent.click(screen.getByLabelText("开始生成故事"));
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({ story: "My story" })
    );
  });

  it("submits on Enter key", () => {
    renderHomePage();
    const textarea = screen.getByLabelText("输入你的故事创意");
    fireEvent.change(textarea, { target: { value: "story" } });
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(mockMutate).toHaveBeenCalled();
  });

  it("does not submit on Shift+Enter", () => {
    renderHomePage();
    const textarea = screen.getByLabelText("输入你的故事创意");
    fireEvent.change(textarea, { target: { value: "story" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("disables button when empty", () => {
    renderHomePage();
    expect(screen.getByLabelText("开始生成故事")).toBeDisabled();
  });

  it("shows remaining char count near limit", () => {
    renderHomePage();
    const textarea = screen.getByLabelText("输入你的故事创意");
    fireEvent.change(textarea, { target: { value: "a".repeat(4600) } });
    expect(screen.getByText(/400/)).toBeInTheDocument();
  });
});
