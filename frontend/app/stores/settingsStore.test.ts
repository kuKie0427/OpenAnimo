import { describe, it, expect } from "vitest";
import { useSettingsStore } from "./settingsStore";

describe("settingsStore", () => {
  it("starts with modal closed", () => {
    expect(useSettingsStore.getState().isModalOpen).toBe(false);
  });

  it("openModal sets isModalOpen to true", () => {
    useSettingsStore.getState().openModal();
    expect(useSettingsStore.getState().isModalOpen).toBe(true);
  });

  it("closeModal sets isModalOpen to false", () => {
    useSettingsStore.getState().openModal();
    useSettingsStore.getState().closeModal();
    expect(useSettingsStore.getState().isModalOpen).toBe(false);
  });
});
