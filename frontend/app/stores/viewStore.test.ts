import { describe, expect, it, beforeEach, vi } from "vitest";

vi.mock("zustand/middleware", () => ({
	persist: (fn: any) => fn,
}));

// Dynamic import after mock so persist is a no-op
const { useViewStore } = await import("./viewStore");

describe("viewStore", () => {
	beforeEach(() => {
		useViewStore.setState({
			viewMode: "canvas",
			isSearchOpen: false,
			isMinimapVisible: true,
			selectedShapeIds: [],
			searchQuery: "",
			searchResults: [],
			currentSearchIndex: 0,
		});
	});

	it("initializes with default state", () => {
		const state = useViewStore.getState();
		expect(state.viewMode).toBe("canvas");
		expect(state.isSearchOpen).toBe(false);
		expect(state.isMinimapVisible).toBe(true);
		expect(state.selectedShapeIds).toEqual([]);
		expect(state.searchQuery).toBe("");
		expect(state.searchResults).toEqual([]);
		expect(state.currentSearchIndex).toBe(0);
	});

	it("sets view mode", () => {
		useViewStore.getState().setViewMode("timeline");
		expect(useViewStore.getState().viewMode).toBe("timeline");
	});

	it("sets search open state", () => {
		useViewStore.getState().setSearchOpen(true);
		expect(useViewStore.getState().isSearchOpen).toBe(true);
		useViewStore.getState().setSearchOpen(false);
		expect(useViewStore.getState().isSearchOpen).toBe(false);
	});

	it("sets minimap visibility", () => {
		useViewStore.getState().setMinimapVisible(false);
		expect(useViewStore.getState().isMinimapVisible).toBe(false);
	});

	it("sets selected shape IDs", () => {
		useViewStore.getState().setSelectedShapeIds(["shape:1", "shape:2"]);
		expect(useViewStore.getState().selectedShapeIds).toEqual(["shape:1", "shape:2"]);
	});

	it("sets search query", () => {
		useViewStore.getState().setSearchQuery("test query");
		expect(useViewStore.getState().searchQuery).toBe("test query");
	});

	it("sets search results", () => {
		useViewStore.getState().setSearchResults(["shape:1", "shape:3"]);
		expect(useViewStore.getState().searchResults).toEqual(["shape:1", "shape:3"]);
	});

	it("sets current search index", () => {
		useViewStore.getState().setCurrentSearchIndex(2);
		expect(useViewStore.getState().currentSearchIndex).toBe(2);
	});

	it("persist partialize only includes viewMode and isMinimapVisible", () => {
		const state = useViewStore.getState();
		expect(state).toHaveProperty("viewMode");
		expect(state).toHaveProperty("isMinimapVisible");
		expect(state).toHaveProperty("isSearchOpen");
		expect(state).toHaveProperty("selectedShapeIds");
		expect(state).toHaveProperty("searchQuery");
		expect(state).toHaveProperty("searchResults");
		expect(state).toHaveProperty("currentSearchIndex");
	});
});
