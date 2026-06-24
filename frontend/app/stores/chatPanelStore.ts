import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ChatPanelState {
	isOpen: boolean;
	toggle: () => void;
	open: () => void;
	close: () => void;
}

export const useChatPanelStore = create<ChatPanelState>()(
	persist(
		(set) => ({
			isOpen: false,
			toggle: () => set((state) => ({ isOpen: !state.isOpen })),
			open: () => set({ isOpen: true }),
			close: () => set({ isOpen: false }),
		}),
		{
			name: "openanimo-chat-panel",
		}
	)
);
