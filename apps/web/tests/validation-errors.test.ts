import { describe, expect, it } from "vitest";

import { toFieldErrors } from "../components/profile/form-primitives";

/**
 * FR-014: a rejection must reach the field it concerns, carrying the API's
 * reason. Collapsing these into a single "save failed" is the failure mode this
 * guards against.
 */
describe("field error mapping", () => {
  it("maps each failure onto its field", () => {
    const errors = toFieldErrors([
      { field: "ended_on", reason: "must be on or after started_on" },
      { field: "salary_max", reason: "must be greater than or equal to salary_min" },
    ]);

    expect(errors.ended_on).toBe("must be on or after started_on");
    expect(errors.salary_max).toBe("must be greater than or equal to salary_min");
  });

  it("returns nothing for fields the API did not object to", () => {
    const errors = toFieldErrors([{ field: "ended_on", reason: "must be on or after started_on" }]);
    expect(errors.started_on).toBeUndefined();
  });

  it("handles an empty failure list", () => {
    expect(toFieldErrors([])).toEqual({});
  });
});
