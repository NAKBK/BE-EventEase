# ADR-0003: Deterministic weighted-sum match score, explicitly provisional

## Context

The product's original scope defines a weighted-sum formula
(`S = Σ(wᵢ × xᵢ) / Σwᵢ × 100`) but supplies **no actual AHP-derived weights** - no
pairwise comparison study, no participant panel. Attendees rely on this score to
decide whether an event is worth attending; the agreed product rule that no
real-world attendee should interpret a score as a safety guarantee means the
score's provisionality has to be structurally visible, not just mentioned in a
footnote.

## Decision

Implement the formula in one place, `app/modules/events/service.py::_compute_match`,
with concrete, documented, versioned coefficients (base weight 1, ×2 if required
/ ×0.25 if not for the six facility attributes; 2/1/0.25 for walking distance
short/moderate/any), and:

- Tag every response with `weight_version="provisional-v1"` so a future re-weighting
  is a version bump, not a silent behavior change.
- Return all seven breakdown rows every time, including `label: "unknown"` ones -
  never omit an attribute the organizer didn't claim.
- Treat an unknown claim as fulfillment `xᵢ=0` (conservative, not "assume
  accessible") **and** list it in `unknown_attributes` - the score alone never
  implies certainty a human didn't confirm.
- Call `_compute_match` from exactly two places - `GET /events/{id}/match`
  (BE-API-006) and `sort=match_score` on `GET /events` (BE-API-018) - never
  reimplement it. `tests/test_be010.py` regression-tests that both call sites agree
  on both the score and the resulting order.

## Consequences

- Changing the weights later (once real AHP data exists) is a one-function change
  plus a version bump - every caller already goes through `_compute_match`, so there
  is no second copy of the formula to find and update.
- The score can never claim more confidence than the underlying data supports: an
  event with three unknown claims gets a lower score *and* a visible list of what's
  unknown, by construction of the formula, not by a UI-layer disclaimer bolted on
  after the fact.
- Cost: `sort=match_score` requires an attendee bearer token with a saved
  `NeedProfile` (409 `NEED_PROFILE_MISSING` otherwise) - an organizer, or an
  attendee who hasn't set needs yet, cannot use this sort mode. This is intentional
  (a score with no profile behind it is meaningless), not an oversight, and is
  covered by `tests/test_be010.py::test_sort_match_score_requires_saved_profile`
  and `test_sort_match_score_forbidden_for_organizer`.
