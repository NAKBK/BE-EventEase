# ADR-0006: Simple Additive Weighting (SAW), not a machine-learning model, for the match score

## Context

`_compute_match` (ADR-0003) ranks events for an attendee using a weighted sum of
the seven accessibility attributes — this is the classic **Simple Additive
Weighting (SAW)** multi-criteria method: normalize each criterion's weight,
multiply by that criterion's fulfillment value, sum, scale to 0–100. The
alternative on the table was a learned model — e.g. a regression or ranking model
that infers weights (or a full score function) from historical data instead of
hand-set coefficients.

A learned model needs training data that this product does not have yet:

- **No real usage history.** Every event, claim, and verification in the database
  today is seeded demo data (`source="demo"`) or organizer-entered data — there is
  no corpus of real attendee outcomes to learn from.
- **No labeled ground truth for "good match."** The one closest thing to a label
  is a post-event `Verification` (did the claim hold true), and even that only
  exists once an attendee has gone through the full Need → Match → Commit →
  Verify loop for a real event — which, at this stage, has happened zero times
  outside seeded fixtures.
- **No volume.** Even a simple learned weighting needs enough independent
  examples per attribute combination to avoid overfitting; a handful of seeded
  rows is orders of magnitude short of that, in any direction.
- **BE-007 (Jakarta open-data import) is not implemented** (see
  `docs/api-status.md`), so the one planned source of a larger, real venue
  dataset doesn't exist yet either — training on organizer self-reported claims
  alone would just learn the organizers' own reporting bias, not attendee outcomes.

## Decision

Use SAW for the match score for as long as the product has no real outcome
dataset, and treat that as a deliberate, temporary choice — not a permanent
architectural ceiling:

- SAW requires zero training data: coefficients are hand-set and documented
  (ADR-0003), not fit from examples, so it works correctly on day one with only
  seeded fixtures.
- SAW is fully explainable per the product rule against unsupported accessibility
  claims: every score ships with its complete per-attribute breakdown
  (`weight`, `fulfillment`, `label`) — a hand-set linear formula can be explained
  attribute-by-attribute in a way a trained model's weights usually can't without
  extra explainability tooling.
- SAW is deterministic and versioned (`weight_version="provisional-v1"`) — the
  same profile and claim always produce the same score, which matters for trust
  and for testability (`tests/test_be003.py`, `tests/test_be010.py`).

## Roadmap: migrate to a learned model once enough data exists

This is provisional by design, not a final answer. The trigger to revisit is
data volume, not a calendar date:

1. **Accumulate real outcome data first.** Every real (non-seeded) `Verification`
   row is a data point tying an organizer's claim, an attendee's need profile, and
   what actually happened. This only starts accumulating once real events run
   through the full loop in production.
2. **Once there's enough volume to hold out a validation set** (order of
   magnitude: hundreds of independent verified request/verification pairs, not a
   fixed number decided in advance), fit a model — e.g. learned per-attribute
   weights via regression against verification outcomes, or a ranking model — as
   a candidate scorer evaluated *offline* against SAW's historical scores first.
3. **Never replace SAW silently.** Any learned scorer ships as a new
   `weight_version` (e.g. `"learned-v1"`), reachable the same way BE-API-006/018
   already version the formula, so a score's provenance is always inspectable and
   a regression can be rolled back by pinning the version.
4. **Keep SAW as the cold-start fallback**, not deleted code, for any attribute
   combination or organizer with too little data behind it — a learned model
   should never be forced to extrapolate from near-zero examples when a documented
   deterministic fallback is sitting right there.
5. **BE-007's dataset import, if and when it lands, is a venue-attribute data
   source, not an outcome dataset** — it would improve claim coverage/provenance
   but does not by itself provide the verification-outcome data step 1 requires.
   Don't conflate the two when deciding it's "time" to train a model.

## Consequences

- No ML infrastructure (feature store, training pipeline, model registry) is
  justified or built for this yet — that would be solving a data problem the
  product doesn't have with a tooling investment it can't yet pay for.
- The explicit `weight_version` versioning from ADR-0003 is what makes this
  migration possible later without a breaking change: FE and any analysis code
  should treat the score's meaning as tied to `weight_version`, not assume it's a
  stable absolute scale across versions.
- Revisiting this decision without first checking real outcome-data volume (step
  2) risks training a model on organizer self-report bias instead of attendee
  reality — the exact failure mode the "no unsupported accessibility claim as
  fact" product rule exists to prevent.
