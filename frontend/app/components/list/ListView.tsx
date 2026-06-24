import { useState, useMemo } from "react";
import { ListHeader } from "./ListHeader";
import { ListItem } from "./ListItem";
import { ListEmpty } from "./ListEmpty";

interface ListViewProps {
  projectId: number;
  shapes: Array<{
    id: string;
    type: string;
    content: any;
    x: number;
    y: number;
  }>;
  onShapeSelect: (id: string) => void;
  onShapeEdit: (id: string) => void;
  onShapeDelete: (ids: string[]) => void;
}

export function ListView({
  projectId: _projectId,
  shapes,
  onShapeSelect,
  onShapeEdit,
  onShapeDelete,
}: ListViewProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"name" | "type" | "position">(
    "position"
  );

  const filteredShapes = useMemo(() => {
    let result = shapes;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          s.content?.title?.toLowerCase().includes(query) ||
          s.content?.description?.toLowerCase().includes(query)
      );
    }

    if (typeFilter !== "all") {
      result = result.filter((s) => s.type === typeFilter);
    }

    result = [...result].sort((a, b) => {
      if (sortBy === "name")
        return (a.content?.title || "").localeCompare(b.content?.title || "");
      if (sortBy === "type") return a.type.localeCompare(b.type);
      return a.x - b.x || a.y - b.y;
    });

    return result;
  }, [shapes, searchQuery, typeFilter, sortBy]);

  const handleSelectAll = () => {
    if (selectedIds.length === filteredShapes.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredShapes.map((s) => s.id));
    }
  };

  const handleDelete = () => {
    if (selectedIds.length > 0) {
      onShapeDelete(selectedIds);
      setSelectedIds([]);
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-base-100">
      <ListHeader
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        sortBy={sortBy}
        onSortChange={setSortBy}
        selectedCount={selectedIds.length}
        totalCount={filteredShapes.length}
        onSelectAll={handleSelectAll}
        onDelete={handleDelete}
      />

      <div className="flex-1 overflow-y-auto p-4">
        {filteredShapes.length === 0 ? (
          <ListEmpty searchQuery={searchQuery} />
        ) : (
          <div className="space-y-2">
            {filteredShapes.map((shape, index) => (
              <ListItem
                key={shape.id}
                shape={shape}
                isSelected={selectedIds.includes(shape.id)}
                index={index}
                onSelect={(selected) => {
                  if (selected) {
                    setSelectedIds([...selectedIds, shape.id]);
                  } else {
                    setSelectedIds(
                      selectedIds.filter((id) => id !== shape.id)
                    );
                  }
                }}
                onClick={() => onShapeSelect(shape.id)}
                onEdit={() => onShapeEdit(shape.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
