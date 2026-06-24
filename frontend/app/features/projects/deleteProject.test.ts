import { describe, expect, it, vi } from "vitest";

import { cleanupDeletedProjectCaches } from "./deleteProject";

describe("cleanupDeletedProjectCaches", () => {
  it("invalidates project list and removes deleted project caches", () => {
    const queryClient = {
      invalidateQueries: vi.fn(),
      removeQueries: vi.fn(),
    };

    cleanupDeletedProjectCaches(queryClient as never, [42]);

    expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ["projects"] });
    expect(queryClient.removeQueries).toHaveBeenNthCalledWith(1, {
      queryKey: ["project", 42],
    });
    expect(queryClient.removeQueries).toHaveBeenNthCalledWith(2, {
      queryKey: ["characters", 42],
    });
    expect(queryClient.removeQueries).toHaveBeenNthCalledWith(3, {
      queryKey: ["shots", 42],
    });
    expect(queryClient.removeQueries).toHaveBeenNthCalledWith(4, {
      queryKey: ["messages", 42],
    });
  });
});
