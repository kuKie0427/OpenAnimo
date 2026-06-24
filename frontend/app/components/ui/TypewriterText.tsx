import { useEffect, useState, useRef, useCallback } from "react";

interface TypewriterTextProps {
  /** 要显示的文本 */
  text: string;
  /** 每个字符的延迟（毫秒） */
  charDelay?: number;
  /** 是否启用打字机效果 */
  enabled?: boolean;
  /** 打字完成回调 */
  onComplete?: () => void;
  /** 进度更新回调 (0-1) */
  onProgress?: (progress: number) => void;
}

/**
 * 打字机效果文本组件
 * 逐字显示文本，模拟打字效果
 */
export function TypewriterText({
  text,
  charDelay = 20,
  enabled = true,
  onComplete,
  onProgress,
}: TypewriterTextProps) {
  const [displayedText, setDisplayedText] = useState(enabled ? "" : text);
  const [isComplete, setIsComplete] = useState(!enabled);
  const indexRef = useRef(0);
  const textRef = useRef(text);
  const progressRef = useRef<number | null>(null);

  const reportProgress = useCallback((progress: number) => {
    // 四舍五入到两位小数，避免重复触发相同进度值
    const roundedProgress = Math.round(progress * 100) / 100;
    if (progressRef.current !== roundedProgress) {
      onProgress?.(roundedProgress);
      progressRef.current = roundedProgress;
    }
  }, [onProgress]);

  useEffect(() => {
    // 处理文本变化，特别是流式文本
    if (text !== textRef.current) {
      textRef.current = text;
      if (enabled) {
        if (text.startsWith(displayedText)) {
          // 新文本是旧文本的扩展，继续打字
          if (isComplete) {
            setIsComplete(false); // 有新文本需要打字
          }
        } else {
          // 完全不同的文本，重新开始
          indexRef.current = 0;
          setDisplayedText("");
          setIsComplete(false);
          progressRef.current = null;
          reportProgress(0);
        }
      } else {
        // 禁用时直接显示完整文本
        setDisplayedText(text);
        if (!isComplete) setIsComplete(true);
        reportProgress(1);
      }
    }
  }, [text, enabled, displayedText, isComplete, reportProgress]);

  useEffect(() => {
    // 处理打字动画
    if (!enabled) {
      setDisplayedText(text);
      if (!isComplete) {
        setIsComplete(true);
        reportProgress(1);
        onComplete?.();
      }
      return;
    }

    if (indexRef.current >= text.length) {
      if (!isComplete) {
        setIsComplete(true);
        reportProgress(1);
        onComplete?.();
      }
      return;
    }

    const timer = setTimeout(() => {
      // 处理流式文本，确保不会跳过已显示的文本
      if (indexRef.current < displayedText.length) {
        indexRef.current = displayedText.length;
      }

      indexRef.current += 1;
      setDisplayedText(text.slice(0, indexRef.current));

      const progress = text.length > 0 ? indexRef.current / text.length : 1;
      reportProgress(progress);
    }, charDelay);

    return () => clearTimeout(timer);
  }, [text, charDelay, enabled, displayedText, isComplete, onComplete, reportProgress]);

  return (
    <span>
      {displayedText}
      {enabled && !isComplete && (
        <span className="inline-block w-0.5 h-4 bg-current animate-pulse ml-0.5" />
      )}
    </span>
  );
}
