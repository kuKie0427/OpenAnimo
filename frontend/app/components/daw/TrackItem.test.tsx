import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { TrackItem } from "./TrackItem";

describe("TrackItem", () => {
	it("renders title and status text", () => {
		render(
			<TrackItem
				item={{ id: 1, title: "My Track", status: "completed" }}
				selected={false}
				onClick={vi.fn()}
			/>,
		);

		expect(screen.getByText("My Track")).toBeInTheDocument();
		expect(screen.getByText("completed")).toBeInTheDocument();
	});

	it("renders thumbnail image when provided", () => {
		render(
			<TrackItem
				item={{ id: 1, title: "My Track", thumbnail: "/img/thumb.png", status: "completed" }}
				selected={false}
				onClick={vi.fn()}
			/>,
		);

		const img = screen.getByRole("img", { name: /my track/i });
		expect(img).toHaveAttribute("src", "/img/thumb.png");
	});

	it("renders placeholder div when no thumbnail", () => {
		const { container } = render(
			<TrackItem
				item={{ id: 1, title: "My Track", status: "completed" }}
				selected={false}
				onClick={vi.fn()}
			/>,
		);

		expect(screen.queryByRole("img")).not.toBeInTheDocument();
		const placeholder = container.querySelector(".bg-base-300");
		expect(placeholder).toBeInTheDocument();
	});

	it("applies selected styles when selected", () => {
		render(
			<TrackItem
				item={{ id: 1, title: "My Track", status: "completed" }}
				selected={true}
				onClick={vi.fn()}
			/>,
		);

		const button = screen.getByRole("button", { name: /my track/i });
		expect(button).toHaveClass("bg-primary/10");
		expect(button).toHaveClass("border-primary/20");
	});

	it("applies unselected styles when not selected", () => {
		render(
			<TrackItem
				item={{ id: 1, title: "My Track", status: "completed" }}
				selected={false}
				onClick={vi.fn()}
			/>,
		);

		const button = screen.getByRole("button", { name: /my track/i });
		expect(button).toHaveClass("border-transparent");
	});

	it("shows pulse dot for processing status", () => {
		const { container } = render(
			<TrackItem
				item={{ id: 1, title: "My Track", status: "processing" }}
				selected={false}
				onClick={vi.fn()}
			/>,
		);

		const pulseDot = container.querySelector(".animate-pulse");
		expect(pulseDot).toBeInTheDocument();
		expect(pulseDot).toHaveClass("bg-warning");
	});

	it("shows red dot for error status", () => {
		const { container } = render(
			<TrackItem
				item={{ id: 1, title: "My Track", status: "error" }}
				selected={false}
				onClick={vi.fn()}
			/>,
		);

		const errorDot = container.querySelector(".bg-error");
		expect(errorDot).toBeInTheDocument();
	});

	it("does not show status dot for draft status", () => {
		const { container } = render(
			<TrackItem
				item={{ id: 1, title: "My Track", status: "draft" }}
				selected={false}
				onClick={vi.fn()}
			/>,
		);

		expect(container.querySelector(".animate-pulse")).not.toBeInTheDocument();
		expect(container.querySelector(".bg-error")).not.toBeInTheDocument();
	});

	it("calls onClick when clicked", async () => {
		const user = userEvent.setup();
		const handleClick = vi.fn();
		render(
			<TrackItem
				item={{ id: 1, title: "My Track", status: "completed" }}
				selected={false}
				onClick={handleClick}
			/>,
		);

		await user.click(screen.getByRole("button", { name: /my track/i }));
		expect(handleClick).toHaveBeenCalledTimes(1);
	});
});
