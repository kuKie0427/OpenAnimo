import type { QueryClient } from "@tanstack/react-query";

export function cleanupDeletedProjectCaches(
  queryClient: QueryClient,
  deletedIds: number[]
) {
  queryClient.invalidateQueries({ queryKey: ["projects"] });
  for (const deletedId of deletedIds) {
    queryClient.removeQueries({ queryKey: ["project", deletedId] });
    queryClient.removeQueries({ queryKey: ["characters", deletedId] });
    queryClient.removeQueries({ queryKey: ["shots", deletedId] });
    queryClient.removeQueries({ queryKey: ["messages", deletedId] });
  }
}
