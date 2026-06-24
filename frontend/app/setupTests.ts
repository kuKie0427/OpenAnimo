import "@testing-library/jest-dom";
import { server } from "~/mocks/server";

// jsdom exposes requestSubmit() as a not-implemented stub in some versions.
// Override it deterministically so form-oriented tests stay warning-clean
// without changing production component behavior.
Object.defineProperty(HTMLFormElement.prototype, "requestSubmit", {
	configurable: true,
	value(this: HTMLFormElement, submitter?: HTMLElement) {
		if (submitter) {
			submitter.click();
			return;
		}
		this.dispatchEvent(
			new SubmitEvent("submit", { bubbles: true, cancelable: true }),
		);
	},
});

// Establish API mocking before all tests.
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests.
afterEach(() => server.resetHandlers());

// Clean up after the tests are finished.
afterAll(() => server.close());
