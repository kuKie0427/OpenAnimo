import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { TrackList } from "./TrackList";

const items = [
	{ id: 1, title: "Track One", status: "completed" as const },
	{ id: 2, title: "Track Two", status: "processing" as const },
	{ id: 3, title: "Track Three", status: "error" as const },
];

describe("TrackList", () => {
	it("renders all items", () => {
		render(
			<TrackList items={items} selectedId={null} onSelect={vi.fn()} />,
		);

		expect(screen.getByText("Track One")).toBeInTheDocument();
		expect(screen.getByText("Track Two")).toBeInTheDocument();
		expect(screen.getByText("Track Three")).toBeInTheDocument();
	});

	it("displays item count in header", () => {
		render(
			<TrackList items={items} selectedId={null} onSelect={vi.fn()} />,
		);

		expect(screen.getByText("3 items")).toBeInTheDocument();
	});

	it("shows empty state when no items", () => {
		render(
			<TrackList items={[]} selectedId={null} onSelect={vi.fn()} />,
		);

		expect(screen.getByText("No tracks yet")).toBeInTheDocument();
	});

	it("shows zero items in header when empty", () => {
		render(
			<TrackList items={[]} selectedId={null} onSelect={vi.fn()} />,
		);

		expect(screen.getByText("0 items")).toBeInTheDocument();
	});

	it("calls onSelect when an item is clicked", async () => {
		const user = userEvent.setup();
		const handleSelect = vi.fn();
		render(
			<TrackList items={items} selectedId={null} onSelect={handleSelect} />,
		);

		await user.click(screen.getByText("Track Two"));
		expect(handleSelect).toHaveBeenCalledWith(2);
	});

	it("marks selected item with aria-selected", () => {
		render(
			<TrackList items={items} selectedId={2} onSelect={vi.fn()} />,
		);

		const options = screen.getAllByRole("option");
		expect(options[1]).toHaveAttribute("aria-selected", "true");
		expect(options[0]).toHaveAttribute("aria-selected", "false");
	});

	it("navigates down with ArrowDown", async () => {
		const user = userEvent.setup();
		const handleSelect = vi.fn();
		render(
			<TrackList items={items} selectedId={1} onSelect={handleSelect} />,
		);

		const listbox = screen.getByRole("listbox");
		await user.click(listbox);
		await user.keyboard("{ArrowDown}");

		expect(handleSelect).toHaveBeenCalledWith(2);
	});

	it("navigates up with ArrowUp and wraps to last", async () => {
		const user = userEvent.setup();
		const handleSelect = vi.fn();
		render(
			<TrackList items={items} selectedId={1} onSelect={handleSelect} />,
		);

		const listbox = screen.getByRole("listbox");
		await user.click(listbox);
		await user.keyboard("{ArrowUp}");

		expect(handleSelect).toHaveBeenCalledWith(3);
	});

	it("wraps ArrowDown from last item to first", async () => {
		const user = userEvent.setup();
		const handleSelect = vi.fn();
		render(
			<TrackList items={items} selectedId={3} onSelect={handleSelect} />,
		);

		const listbox = screen.getByRole("listbox");
		await user.click(listbox);
		await user.keyboard("{ArrowDown}");

		expect(handleSelect).toHaveBeenCalledWith(1);
	});

	it("has correct listbox label", () => {
		render(
			<TrackList items={items} selectedId={null} onSelect={vi.fn()} />,
		);

		expect(screen.getByRole("listbox", { name: /track list/i })).toBeInTheDocument();
	});

	it("renders add track button", () => {
		render(
			<TrackList items={items} selectedId={null} onSelect={vi.fn()} />,
		);

		expect(screen.getByRole("button", { name: /add track/i })).toBeInTheDocument();
	});
});
