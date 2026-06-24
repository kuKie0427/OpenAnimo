import { useCallback, useLayoutEffect, useRef } from "react";
import { AtomMap, EditorAtom, type Editor, type TLShape, type TLShapeId } from "tldraw";

const ShapeSizes = new EditorAtom("shape-sizes", (editor: Editor) => {
  const map = new AtomMap<TLShapeId, { width: number; height: number }>("shape-sizes");
  editor.sideEffects.registerAfterDeleteHandler("shape", (shape) => {
    map.delete(shape.id);
  });
  return map;
});

export function getShapeSize(editor: Editor, shapeId: TLShapeId) {
  return ShapeSizes.get(editor).get(shapeId);
}

export function useDomSize(shape: TLShape, editor: Editor | null) {
  const ref = useRef<HTMLDivElement>(null);

  const updateSize = useCallback(() => {
    if (!ref.current || !editor) return;
    const width = ref.current.offsetWidth;
    const height = ref.current.offsetHeight;
    if (height <= 0) return;
    ShapeSizes.update(editor, (map) => {
      const existing = map.get(shape.id);
      if (existing && existing.width === width && existing.height === height) return map;
      return map.set(shape.id, { width, height });
    });
  }, [editor, shape.id]);

  useLayoutEffect(() => {
    updateSize();
  }, [updateSize]);

  useLayoutEffect(() => {
    if (!ref.current || !editor) return;
    const observer = new ResizeObserver(updateSize);
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [updateSize]);

  return ref;
}
