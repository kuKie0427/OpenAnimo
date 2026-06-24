import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ViewSwitcher } from "./ViewSwitcher";

describe("ViewSwitcher", () => {
	it("renders all three view buttons", () => {
		render(
			<ViewSwitcher currentView="list" onViewChange={vi.fn()} />,
		);

		expect(screen.getByRole("button", { name: /列表/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /时间线/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /画布/i })).toBeInTheDocument();
	});

	it("applies selected styles to the current view", () => {
		render(
			<ViewSwitcher currentView="timeline" onViewChange={vi.fn()} />,
		);

		const timelineButton = screen.getByRole("button", { name: /时间线/i });
		expect(timelineButton).toHaveClass("bg-primary");

		const listButton = screen.getByRole("button", { name: /列表/i });
		expect(listButton).not.toHaveClass("bg-primary");
	});

	it("applies unselected styles to non-selected views", () => {
		render(
			<ViewSwitcher currentView="list" onViewChange={vi.fn()} />,
		);

		const timelineButton = screen.getByRole("button", { name: /时间线/i });
		expect(timelineButton).toHaveClass("text-base-content/60");

		const canvasButton = screen.getByRole("button", { name: /画布/i });
		expect(canvasButton).toHaveClass("text-base-content/60");
	});

	it("calls onViewChange when a view button is clicked", async () => {
		const user = userEvent.setup();
		const onViewChange = vi.fn();
		render(
			<ViewSwitcher currentView="list" onViewChange={onViewChange} />,
		);

		await user.click(screen.getByRole("button", { name: /画布/i }));
		expect(onViewChange).toHaveBeenCalledWith("canvas");
	});

	it("calls onViewChange with correct view for each button", async () => {
		const user = userEvent.setup();
		const onViewChange = vi.fn();
		render(
			<ViewSwitcher currentView="list" onViewChange={onViewChange} />,
		);

		await user.click(screen.getByRole("button", { name: /列表/i }));
		expect(onViewChange).toHaveBeenCalledWith("list");

		await user.click(screen.getByRole("button", { name: /时间线/i }));
		expect(onViewChange).toHaveBeenCalledWith("timeline");

		await user.click(screen.getByRole("button", { name: /画布/i }));
		expect(onViewChange).toHaveBeenCalledWith("canvas");
	});

	it("sets title attribute on each button", () => {
		render(
			<ViewSwitcher currentView="list" onViewChange={vi.fn()} />,
		);

		expect(screen.getByTitle("列表")).toBeInTheDocument();
		expect(screen.getByTitle("时间线")).toBeInTheDocument();
		expect(screen.getByTitle("画布")).toBeInTheDocument();
	});

	it("renders selected button with shadow-aperture class", () => {
		render(
			<ViewSwitcher currentView="canvas" onViewChange={vi.fn()} />,
		);

		const canvasButton = screen.getByRole("button", { name: /画布/i });
		expect(canvasButton).toHaveClass("shadow-aperture");
	});

	it("does not apply shadow-aperture to unselected buttons", () => {
		render(
			<ViewSwitcher currentView="canvas" onViewChange={vi.fn()} />,
		);

		const listButton = screen.getByRole("button", { name: /列表/i });
		expect(listButton).not.toHaveClass("shadow-aperture");
	});
});
