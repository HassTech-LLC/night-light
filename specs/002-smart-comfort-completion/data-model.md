# Data, state and migration contract

Status: proposed schemas, not existing field claims. All times are validated; NaN, infinities, malformed coordinates and unbounded input are rejected.

## Persistent configuration v2

| Entity | Fields and rules |
|---|---|
| Root | `schema_version=2`, increasing `config_revision`, `policy_version`, `migration_state`; keep unrelated existing preferences |
| Intent | `mode=off/manual/smart`; manual warmth/dim; Off survives restart; first install defaults Off |
| Timing | `kind=solar/personal`, local `evening_ready`, `morning_neutral`, solar offset, warmth/dim lead, explicit optional fallback pair, `timezone_policy=system`; no fixed UTC offset |
| Location | optional country/postal/city/coarse coordinates, source and lookup date; no fresh GPS or automatic lookup; personal timing independent |
| Comfort | approximate `warmth_kelvin` 1200–6500; `dim_fraction` 0–0.8; default preview 4000 K/0 dim; no claim those bounds certify physiological safety |
| Transition | policy ID, optional slower multiplier 0.5 or 1.0; changing speed does not change endpoint; normal/catch-up numerical constants live in versioned policy rather than dozens of user fields |
| Override | optional kind `neutral_pause/manual_hold`, original duration, start UTC, expiry UTC, temporary endpoint; live monotonic timing separate |
| Appearance | `mode=system/light/dark`, independent light/dark token objects, material ID, reduced-motion preference; preserve legacy unknown fields during migration |
| Onboarding | version, completed/skipped steps, dismissed tips; skipped setup is not consent to tracking or autostart |
| Routine data | legacy collection flag/history/retention until migration choice; v2 has no new collector; deletion explicit; no inferred timing authority in v2 |
| Integrations | autostart/shortcut preferences with OS-operation acknowledgement; retain existing app identity/IPC credential securely, never expose secret to UI |

Normalize warmth for engineering interpolation as `w=(1/K-1/6500)/(1/1200-1/6500)`, bounded 0–1. Normalize dimming as `d=dim_fraction/0.8`. The existing transform maps these preferences to RGB. Equal differences in these coordinates do not imply equal perceived or biological effects. Never infer measured Kelvin by inverting an arbitrary externally modified matrix.

## Runtime entities

- `ScheduleOccurrence`: rule revision, local date, zone ID, fold/gap resolution, UTC start/ready/return, validity/fallback reason. Its ID prevents duplicate folded-time events.
- `Trajectory`: generation, reason, desired path/endpoint, start active-time epoch, starting position/velocity, rate/acceleration limits, predicted completion or uncertainty, next event.
- `OutputObservation`: requested transform, last successful write transform/time, readback transform/time if supported, validity, provenance (`write_ack/readback/unavailable`), last error. These are software observations only.
- `Availability`: `available/windows_on/windows_unknown/external_conflict/unsupported/backend_error/unknown`; its reason is separate from saved mode.
- `TransientPreview`: token, type `comfort/compare`, expiry, draft appearance, prior intent revision. Not persisted across process exit; native watchdog owns expiry.
- `Snapshot`: session ID, sequence, config revision, intent revision, availability, phase, current software observation, target, schedule, override, confirmation statuses. No raw history or credentials.

## State reducer

Inputs are intents/events, never raw UI writes to the display. Resolution order:

1. A new explicit Off/emergency request invalidates all generations and preview tokens, requests neutral immediately and independently attempts to persist Off. Storage failure cannot block recovery.
2. Availability policy blocks unsafe writes. A conflict must not make repeated neutral writes over another owner.
3. An explicitly initiated, bounded comfort preview may temporarily operate even over persisted Off for first-run setup. It requires a fresh native token and availability; a newer Off always invalidates it. Compare while already Off is a no-op with explanation.
4. Otherwise persistent Off remains neutral/no scheduled work; active previews over other modes remain bounded by native expiry and newer-intent invalidation.
5. Temporary manual hold or neutral pause; these are mutually exclusive.
6. Manual persistent endpoint or current Smart trajectory.
7. Future routine suggestions are display-only and have no output authority.

| Event | Intent/override result | Output behavior |
|---|---|---|
| Enable Smart | mode Smart, clear hold/pause | schedule or catch-up after availability check |
| Choose Manual | mode Manual, cancel Smart override | retain current chosen appearance; do not invent a new default |
| Smart slider edit | Smart retained, manual hold starts/restarts | interactive adjustment, then held until expiry |
| Save nightly preference | persist endpoint, clear temporary hold | replan from accepted output without jump |
| Pause | Smart retained, neutral pause replaces hold | deliberate prompt neutral; ETA until resume shown |
| Resume | Smart retained, clear pause/hold | catch-up from valid output |
| Off | Off persisted, all transient state cancelled | prompt neutral, no later automatic reactivation |
| Begin compare/comfort preview | no durable intent change | reversible temporary output with token |
| End preview | no durable change unless explicit Keep/Save | resolve current intent, never replay stale snapshot |
| Availability failure | intent preserved, preview cancelled | stop competing writes, show reason |
| Safe Windows exclusion clears | intent preserved | Smart catches up if not paused/Off; Manual shows Resume manual appearance and waits for explicit action |
| Unexpected backend/owner conflict clears | fault remains latched | explicit Retry required |
| Wake/clock/zone change | recalculate occurrences and bounded hold expiry | rebase interpolation, no leap |

Manual interactive slider changes may be faster than automatic transitions because they are explicit user actions; coalesce pointer input, cap a short responsive smoothing window and test readability. They cannot bypass validated intensity bounds or availability checks. Off is always immediate intent, irrespective of animation preference.

## Transactional Save

Validate the complete draft and expected revision. Stage and atomically persist the candidate; only then commit runtime settings and emit a saved acknowledgement. Disk failure preserves prior config/runtime and draft. A saved configuration with a blocked display is a success for storage plus a separate display limitation, not a failed Save.

Use `(session_id, request_id)` idempotency with bounded recent results. After timeout query the config revision and canonical saved values; on process restart compare expected/new revision and draft digest, not request ID alone. If reconciliation is uncertain, retain draft and show explicit reload/retry choices. Reject stale-revision updates rather than overwrite newer settings.

Config serialization preserves IPC credentials without exposing them in logs or backups with broader ACLs. Autostart is a separate OS transaction: config records success only after the native action succeeds, otherwise show/revert its checkbox. Do not treat all side effects as an atomic filesystem transaction.

Off is an exception to save-before-runtime-commit. It ignores stale expected-config revisions, invalidates in-flight enable/save intents, requests neutral promptly, then persists. Immediately before every asynchronous Save commit, revalidate intent generation so an older Save cannot re-enable after Off. Serialize commits on the owner.

If Off persistence fails, show `Off now. Couldn't save this for next startup.` and offer Retry saving; never claim durable success. Maintain a small atomic session-recovery record created before enabling automated output. A clean-shutdown receipt is issued only after final intent is durably saved. On next startup, an unclosed session or inconsistent config/receipt opens neutral with recovery guidance. If the recovery record itself cannot be made durable at startup, automated enable is blocked until repaired. This is a crash/failure guard, not proof that a storage device cannot lose acknowledged writes. No success claim survives uncertain persistence.

## Migration and rollback

1. Inventory known legacy schemas, keys, settings locations and authoritative installed path. Capture exact current app/config hashes privately; never dump a credential-bearing config into reports.
2. Create one ACL-preserving pre-migration backup and a schema-migration receipt. Validate backup before modifying the source; atomic writes and recovery tests are mandatory.
3. Preserve Off, manual settings, location, explicit times, themes/materials, custom colors, startup choice and consent. Unknown fields survive under a legacy namespace.
4. Existing users with automatic learning or materially different solar intensity/timing see a one-time explanation: `Your current schedule is unchanged. Preview the new Smart schedule.` Schedule choices: Switch with preview / Keep current schedule. Delete routine history is a separate privacy action, never a substitute for choosing a schedule. No silent stronger output or collection.
5. `migration_state=legacy_pending` runs an explicitly labelled, supported legacy adapter under a narrow constitution migration exception, including already-consented legacy timing behavior. It cannot gain new inputs, retention or permissions. It remains covered by safety tests. When the user switches, retain explicit preferences, stop inference-based changes and collection, record consent version and delete history if requested. The new v2 policy never uses inferred timing. New installs use v2 with collection off.
6. Rollback restores the matching previous binary plus its matching configuration while the owner is stopped. Never feed a v2-only file to a v1 app and claim compatibility. An old retained installer is not sufficient rollback proof.
7. Deleting personal data must disclose whether recovery backups are also removed. Delete selected history/location from active state and app-managed retained copies; a dedicated full-delete path removes all app-managed preference backups after confirmation.

Live transform state is never persisted as proof of physical screen state. Neutral recovery, startup identity, command ownership and backend availability must be re-established after restart.
