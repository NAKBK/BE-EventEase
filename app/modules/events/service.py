from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.modules.events.models import AccessibilityClaim, Event
from app.modules.events.schemas import MatchBreakdown, MatchResponse
from app.modules.users.models import NeedProfile


def calculate_match(user_id: str, event_id: str, session: Session) -> MatchResponse:
    profile = session.get(NeedProfile, user_id)
    if profile is None:
        raise APIError(
            409,
            "NEED_PROFILE_MISSING",
            "Harap isi profil kebutuhan aksesibilitas terlebih dahulu",
        )

    event = session.get(Event, event_id)
    if event is None:
        raise APIError(404, "EVENT_NOT_FOUND", "Event tidak ditemukan")

    claim = session.get(AccessibilityClaim, event_id)
    if claim is None:
        raise APIError(404, "CLAIM_NOT_FOUND", "Data aksesibilitas belum tersedia")

    facility_attrs = [
        "step_free_entrance",
        "elevator_or_ramp",
        "accessible_restroom",
        "accessible_seating",
        "rest_area",
        "parking_or_dropoff",
    ]

    breakdowns = []
    unknowns = []
    total_coeff = 0.0

    for attr in facility_attrs:
        is_required = getattr(profile, attr)
        coeff = 2.0 if is_required else 0.25

        claim_val = getattr(claim, attr)
        if claim_val is None:
            fulfillment = None
            unknowns.append(attr)
            label = "unknown"
        else:
            fulfillment = float(claim_val)
            if fulfillment == 1.0:
                label = "fulfilled"
            elif fulfillment == 0.5:
                label = "partially_fulfilled"
            else:
                label = "not_fulfilled"

        total_coeff += coeff
        breakdowns.append(
            MatchBreakdown(
                attribute=attr,
                required=is_required,
                weight=coeff,
                fulfillment=fulfillment,
                label=label,
            )
        )

    dist_req = profile.walking_distance
    if dist_req == "short":
        coeff = 2.0
    elif dist_req == "moderate":
        coeff = 1.0
    else:
        coeff = 0.25
    total_coeff += coeff

    claim_dist = claim.walking_distance_m
    if claim_dist is None:
        fulfillment = None
        unknowns.append("walking_distance")
        label = "unknown"
    else:
        if dist_req == "short":
            if claim_dist <= 200:
                fulfillment = 1.0
                label = "fulfilled"
            elif claim_dist <= 500:
                fulfillment = 0.5
                label = "partially_fulfilled"
            else:
                fulfillment = 0.0
                label = "not_fulfilled"
        elif dist_req == "moderate":
            if claim_dist <= 500:
                fulfillment = 1.0
                label = "fulfilled"
            elif claim_dist <= 1000:
                fulfillment = 0.5
                label = "partially_fulfilled"
            else:
                fulfillment = 0.0
                label = "not_fulfilled"
        else:
            fulfillment = 1.0
            label = "fulfilled"

    breakdowns.append(
        MatchBreakdown(
            attribute="walking_distance",
            required=True,
            weight=coeff,
            fulfillment=fulfillment,
            label=label,
        )
    )

    score_sum = 0.0
    for bd in breakdowns:
        if bd.fulfillment is not None:
            score_sum += (bd.weight / total_coeff) * bd.fulfillment

    final_score = round(100 * score_sum)

    summary = "Kecocokan dihitung berdasarkan kebutuhan Anda."
    if unknowns:
        summary = "Some required information is unknown; contact the organizer."

    return MatchResponse(
        event_id=event_id,
        score=final_score,
        weight_version="provisional-v1",
        breakdown=breakdowns,
        unknown_attributes=unknowns,
        summary=summary,
    )
