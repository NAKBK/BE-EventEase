# ADR-0004: Reliability is scoped to the organizer, not the event or the venue

## Context

After an event, attendees verify whether the organizer's seven accessibility claims
actually held true (`fulfilled`/`partially_fulfilled`/`not_fulfilled`). This feeds a
"reliability" indicator (the agreed P0 reliability rule: average the last 20
verifications' 1/0.5/0 values, ×100, rounded; `sample_count` = number of
verifications, not attributes; `score:null` with zero samples). The open question is
*whose* number this is — the event's, the venue's, or the organizer's — since all
three are plausible-sounding nouns to attach a trust score to.

## Decision

Reliability is a property of the **`Organizer`** (`app/modules/organizers/service.py::get_organizer_reliability`),
aggregated across the last 20 verifications from **all of that organizer's events**,
regardless of which venue each event was held at. The query chain is
`Verification → AccessibilityRequest → Event → WHERE Event.organizer_id = :id`; the
`Venue` table is never joined and never referenced in the computation.

Why the organizer and not the other two nouns:

1. **The claim being verified is an organizational promise, not a physical fact.**
   `AccessibilityClaim` values ("step-free entrance: 1") describe how the organizer
   says they'll run *this* event at *this* venue — staffing the ramp, unlocking the
   accessible entrance, keeping the accessible restroom unblocked. Verification
   checks whether the organizer delivered on that promise. A venue with a physically
   accessible restroom that the organizer's staff kept locked all day is a
   verification *failure* — and it's a failure of the organizer's execution, not a
   fact about the building.
2. **Venues are reused across organizers; organizers reuse venues.** Scoring the
   venue would let a chronically-unreliable organizer inherit a good venue's score
   at their next event there, and would incorrectly penalize a good venue whose one
   bad booking was actually a different organizer's failure.
3. **Only the organizer is an accountable, logged-in actor.** `Organizer.owner_user_id`
   is a real user who registers, publishes events, and responds to requests. `Venue`
   has no owner, no login, and no profile endpoint — there's no one for a
   venue-scored number to be *about* in a way the product could act on (e.g. warn a
   future attendee, or let the organizer improve).
4. **The product already surfaces it this way.** `GET /api/organizers/{id}`
   (BE-API-013) is explicitly an organizer profile endpoint; `OrganizerEmbed` (not a
   `VenueEmbed` field) is what every event list/detail response carries.

### Corollary: missing or incomplete venue data has zero effect on reliability

Because `Venue` never enters the query at all, a venue with `lat`/`lng` still `null`,
or any other incomplete venue field, changes nothing about the reliability
computation — there's no fallback path to reach for, because there was never a
dependency to fall back from. `Event.venue_id` is `NOT NULL` at the schema level
(every event structurally has a venue row), but that row's completeness is
irrelevant here by construction.

## History: a real drift bug this ADR closes

Until this audit, the formula was implemented **twice**: once correctly in
`organizers/service.py::get_organizer_reliability` (flattens all attribute values
across the 20 verifications, then averages), and once independently in
`events/service.py::_organizer_embed` (averaged *per verification* first, then
averaged those per-verification averages). These two give different results
whenever verifications don't all report the same number of known attributes —
exactly the kind of drift that having a single authoritative implementation is
meant to prevent. Fixed by deleting the second implementation and having
`events.service._organizer_embed` call `organizers.service.get_organizer_reliability`
directly, so there is now exactly one formula, called from every site that needs a
reliability number (`organizers.controller`, `events.service` list/detail,
`verification.service.submit_verification`).

## Consequences

- One formula, one place to fix or re-derive it. No caller is allowed its own copy —
  enforced by convention (there's no technical guard against a future duplicate
  besides code review and this ADR).
- A venue-level or event-level reliability metric is explicitly out of scope for
  this product's current model; if a future requirement genuinely needs one, it is
  a new metric with its own query and its own justification, not a reinterpretation
  of this one.
