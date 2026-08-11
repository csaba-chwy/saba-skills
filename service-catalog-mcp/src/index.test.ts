import assert from "node:assert/strict";
import test from "node:test";

import { getLastVerified, getSummary } from "./index.js";

test("extracts the verification date without polluting the summary", () => {
  const markdown = `# Checkout Service Description

Last verified: 2026-08-11

## Service in one paragraph

Owns checkout state transitions and publishes completed orders.
`;

  assert.equal(getLastVerified(markdown), "2026-08-11");
  assert.equal(
    getSummary(markdown),
    "Owns checkout state transitions and publishes completed orders."
  );
});

test("returns null when a service description has no verification date", () => {
  assert.equal(getLastVerified("# Legacy service\n\nUndated description."), null);
});
