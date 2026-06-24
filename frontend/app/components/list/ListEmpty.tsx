import { DocumentIcon } from "@heroicons/react/24/outline";

interface ListEmptyProps {
  searchQuery?: string;
}

export function ListEmpty({ searchQuery }: ListEmptyProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-base-content/40">
      <DocumentIcon className="w-12 h-12 mb-4" />
      {searchQuery ? (
        <>
          <p className="text-sm">没有找到匹配的内容</p>
          <p className="text-xs mt-1">尝试调整搜索关键词</p>
        </>
      ) : (
        <>
          <p className="text-sm">还没有内容</p>
          <p className="text-xs mt-1">在画布上创建内容后会显示在这里</p>
        </>
      )}
    </div>
  );
}
