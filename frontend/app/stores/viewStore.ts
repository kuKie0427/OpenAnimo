import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ViewMode = "canvas" | "timeline" | "list";

interface ViewState {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;

  isSearchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  isMinimapVisible: boolean;
  setMinimapVisible: (visible: boolean) => void;

  selectedShapeIds: string[];
  setSelectedShapeIds: (ids: string[]) => void;

  searchQuery: string;
  setSearchQuery: (query: string) => void;
  searchResults: string[];
  setSearchResults: (results: string[]) => void;
  currentSearchIndex: number;
  setCurrentSearchIndex: (index: number) => void;

  currentTime: number;
  setCurrentTime: (time: number) => void;
  isPlaying: boolean;
  setIsPlaying: (playing: boolean) => void;
  totalDuration: number;
  setTotalDuration: (duration: number) => void;
}

export const useViewStore = create<ViewState>()(
  persist(
    (set) => ({
      viewMode: "canvas",
      setViewMode: (mode) => set({ viewMode: mode }),

      isSearchOpen: false,
      setSearchOpen: (open) => set({ isSearchOpen: open }),
      isMinimapVisible: true,
      setMinimapVisible: (visible) => set({ isMinimapVisible: visible }),

      selectedShapeIds: [],
      setSelectedShapeIds: (ids) => set({ selectedShapeIds: ids }),

      searchQuery: "",
      setSearchQuery: (query) => set({ searchQuery: query }),
      searchResults: [],
      setSearchResults: (results) => set({ searchResults: results }),
      currentSearchIndex: 0,
      setCurrentSearchIndex: (index) => set({ currentSearchIndex: index }),

      currentTime: 0,
      setCurrentTime: (time) => set({ currentTime: time }),
      isPlaying: false,
      setIsPlaying: (playing) => set({ isPlaying: playing }),
      totalDuration: 0,
      setTotalDuration: (duration) => set({ totalDuration: duration }),
    }),
    {
      name: "openanimo-view",
      partialize: (state) => ({
        viewMode: state.viewMode,
        isMinimapVisible: state.isMinimapVisible,
      }),
    },
  ),
);
