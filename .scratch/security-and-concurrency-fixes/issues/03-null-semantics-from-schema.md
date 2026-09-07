# PATCH/PUT null semantics should be derived from the model schema

Status: needs-triage

## Background

Explicit-null handling on update routes is hand-maintained per service and
has already drifted:

- Flow (apps/flow/src/zrun/flow/api/routes.py): drops nulls for a hardcoded
  `("name", "status")` tuple; `description` null clears the value.
- UC (apps/uc/src/zrun/uc/api/routes.py): blanket-drops every null.

Failure mode: because `model_copy(update=)` skips validation, adding a
required updatable field to `FlowUpdate` without extending the tuple stores
an explicit `None` into a required `FlowResponse` field and serves it as
JSON null — silent contract corruption. Symmetrically, adding a nullable
field to `UserUpdate` makes it permanently unclearable.

Found by code review of the security-and-concurrency-fixes branch
(2026-09-07).

## Proposed direction

Derive nullable-ness from `FlowUpdate.model_fields` / `UserUpdate.model_fields`
(e.g. `None in typing.get_args(field.annotation)`) — ideally as one shared
helper so both services (and future ones) implement a single documented
contract: "explicit null clears nullable fields, is ignored for required
fields".

Tests to keep pinning both sides: flow `description` null clears, flow
`name` null ignored, UC null ignored.
