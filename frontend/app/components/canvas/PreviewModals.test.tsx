import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ImagePreviewModal, VideoPreviewModal, PreviewableImage } from "./PreviewModals";

describe("PreviewModals", () => {
	describe("ImagePreviewModal", () => {
		it("keeps open when clicking the image itself", async () => {
			const user = userEvent.setup();
			const onClose = vi.fn();

			render(<ImagePreviewModal src="/img.png" alt="封面图" onClose={onClose} />);

			await user.click(screen.getByAltText("封面图"));
			expect(onClose).not.toHaveBeenCalled();

			await user.click(screen.getByRole("dialog"));
			expect(onClose).toHaveBeenCalledTimes(1);
		});

		it("calls onClose when clicking close button", async () => {
			const user = userEvent.setup();
			const onClose = vi.fn();

			render(<ImagePreviewModal src="/img.png" alt="封面图" onClose={onClose} />);
			await user.click(screen.getByRole("button", { name: "关闭" }));
			expect(onClose).toHaveBeenCalledTimes(1);
		});

		it("calls onClose on Escape key", () => {
			const onClose = vi.fn();

			render(<ImagePreviewModal src="/img.png" alt="封面图" onClose={onClose} />);
			fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
			expect(onClose).toHaveBeenCalledTimes(1);
		});

		it("does not call onClose on non-Escape key", () => {
			const onClose = vi.fn();

			render(<ImagePreviewModal src="/img.png" alt="封面图" onClose={onClose} />);
			fireEvent.keyDown(screen.getByRole("dialog"), { key: "Enter" });
			expect(onClose).not.toHaveBeenCalled();
		});
	});

	describe("VideoPreviewModal", () => {
		it("keeps open when clicking the video element", async () => {
			const user = userEvent.setup();
			const onClose = vi.fn();

			render(<VideoPreviewModal src="/video.mp4" title="最终视频" onClose={onClose} />);

			const video = screen.getByRole("dialog").querySelector("video");
			if (!video) throw new Error("video element not found");
			await user.click(video);
			expect(onClose).not.toHaveBeenCalled();

			await user.click(screen.getByRole("dialog"));
			expect(onClose).toHaveBeenCalledTimes(1);
		});

		it("calls onClose on Escape key", () => {
			const onClose = vi.fn();

			render(<VideoPreviewModal src="/video.mp4" title="最终视频" onClose={onClose} />);
			fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
			expect(onClose).toHaveBeenCalledTimes(1);
		});

		it("shows download button by default", () => {
			render(<VideoPreviewModal src="/video.mp4" title="最终视频" onClose={vi.fn()} />);
			expect(screen.getByText("下载")).toBeInTheDocument();
		});

		it("hides download button when showDownload is false", () => {
			render(<VideoPreviewModal src="/video.mp4" title="最终视频" onClose={vi.fn()} showDownload={false} />);
			expect(screen.queryByText("下载")).not.toBeInTheDocument();
		});

		it("calls onDownload when download button clicked", async () => {
			const user = userEvent.setup();
			const onDownload = vi.fn();

			render(<VideoPreviewModal src="/video.mp4" title="最终视频" onClose={vi.fn()} onDownload={onDownload} />);
			await user.click(screen.getByText("下载"));
			expect(onDownload).toHaveBeenCalledTimes(1);
		});

		it("opens video in new tab when no onDownload provided", async () => {
			const user = userEvent.setup();
			const openSpy = vi.spyOn(window, "open").mockReturnValue(null);

			render(<VideoPreviewModal src="/video.mp4" title="最终视频" onClose={vi.fn()} />);
			await user.click(screen.getByText("下载"));
			expect(openSpy).toHaveBeenCalledWith("/video.mp4", "_blank", "noopener,noreferrer");
			openSpy.mockRestore();
		});
	});

	describe("PreviewableImage", () => {
		it("renders image and calls onPreview on click", async () => {
			const user = userEvent.setup();
			const onPreview = vi.fn();

			render(<PreviewableImage src="/thumb.png" alt="缩略图" onPreview={onPreview} />);
			await user.click(screen.getByAltText("缩略图"));
			expect(onPreview).toHaveBeenCalledWith("/thumb.png", "缩略图");
		});
	});
});
