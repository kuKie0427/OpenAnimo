import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/fonts.css";
import "./styles/globals.css";

async function enableMocking() {
	if (import.meta.env.MODE !== "development") {
		return;
	}

	const shouldEnableMocking = import.meta.env.VITE_ENABLE_MSW === "true";
	const reloadKey = "__openanimo_msw_disabled_reload__";

	if (!shouldEnableMocking) {
		if ("serviceWorker" in navigator) {
			const isControlledByMockWorker =
				navigator.serviceWorker.controller?.scriptURL.includes(
					"mockServiceWorker.js",
				);
			const registrations = await navigator.serviceWorker.getRegistrations();
			await Promise.all(
				registrations
					.filter((registration) =>
						registration.active?.scriptURL.includes("mockServiceWorker.js"),
					)
					.map((registration) => registration.unregister()),
			);

			if (
				isControlledByMockWorker &&
				!window.sessionStorage.getItem(reloadKey)
			) {
				window.sessionStorage.setItem(reloadKey, "true");
				window.location.reload();
				return new Promise(() => {});
			}

			window.sessionStorage.removeItem(reloadKey);
		}
		return;
	}

	const { worker } = await import("~/mocks/browser");

	// `worker.start()` returns a Promise that resolves
	// once the Service Worker is up and running.
	return worker.start({
		onUnhandledRequest: "bypass",
	});
}

const rootElement = document.getElementById("root")!;
const root = createRoot(rootElement);

enableMocking().then(() => {
	root.render(
		<StrictMode>
			<App />
		</StrictMode>,
	);
});
