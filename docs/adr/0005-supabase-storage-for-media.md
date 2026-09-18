# ADR-0005: Claim evidence photos live in Supabase Storage, not the database

## Context

BE-009 lets an organizer attach photo evidence to an accessibility claim
(BE-API-017). The backend already uses Supabase-hosted Postgres (ADR-0001); the
question is where the actual image bytes live.

## Decision

Store the file in Supabase Storage (a public bucket), and store only the resulting
public URL plus metadata (`id`, `event_id`, `uploader_id`, `uploaded_at`) in
Postgres, via `EventMedia` (`app/modules/events/models.py`). The upload path itself
goes through a deliberately thin wrapper, `app/core/storage.py::SupabaseStorageClient`,
using plain `httpx` calls to Supabase's Storage REST API - no Supabase SDK
dependency. Validation happens before the network call:
content-type must start with `image/`, size is capped at 5&nbsp;MB by reading at
most `MAX_MEDIA_BYTES + 1` bytes regardless of what the client claims about size,
and an empty body is rejected.

## Consequences

- The JSON API never carries raw image bytes in a request or response body - only a
  fetchable URL, matching the wire contract's explicit implementation note ("return
  only a fetchable URL, never raw bytes").
- Postgres stays small and fast to back up/restore; large binary data scales
  independently in object storage built for it.
- `get_storage_client()` raises `StorageNotConfigured` (surfaced as 500
  `STORAGE_NOT_CONFIGURED`) if `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` are unset,
  rather than silently skipping the upload or writing a broken URL - a misconfigured
  deploy fails loudly on the first upload attempt instead of producing event detail
  responses with dead media links.
- Accepted gap, tracked rather than silently ignored: content-type is trusted from
  the client's multipart header, not sniffed from the file's actual bytes - there is
  no magic-byte check. Risk is limited in practice because Supabase Storage serves
  the file back with the same content-type it was uploaded with, so a mislabeled
  file is still served as that label, not executed as something else. Full content
  sniffing (and any moderation/ML content check) is explicitly out of scope for
  this task.
- Accepted gap: if the Supabase upload succeeds but the subsequent
  `session.commit()` fails, the uploaded object is orphaned in the bucket with no
  `EventMedia` row pointing to it. The API still correctly returns 500 to the
  client in that case; there is just no automatic storage cleanup. Low likelihood,
  not yet worth the complexity of a compensating delete.
