# LumiTrace Domain Context

LumiTrace is a local-first Android app that turns explicit viewing history into transparent movie recommendations and a focused choice for a particular viewing occasion.

## Taste and Identity

### Viewing Profile
A user-named, device-local partition of viewing data, such as Solo, Partner, or Family. It owns collection entries, ratings, notes, taste signals, a queue, and viewing events. It is not an online account.

### Taste Profile
The recommendation engine's computed vector and metadata summary for one recommendation run. It is derived from a Viewing Profile and is not a persisted identity.

### Taste Signal
Explicit evidence allowed to influence ranking, including watched state, a 1-10 rating, or deliberate recommendation feedback.

## Choosing a Movie

### Viewing Context
The conditions for one Tonight decision, including hard constraints and soft preferences. It does not become a Viewing Profile.

### Hard Constraint
A condition a result must satisfy, such as release year or a required genre group.

### Soft Preference
A bounded ranking influence, such as diversity strength, that may be traded against relevance.

### Recommendation Run
One on-device execution using a computed Taste Profile and optional Viewing Context. It produces ranked candidates and traces.

### Decision Shortlist
A small, temporary set of candidates being compared for one viewing decision.

## Collection and History

### Collection Entry
The current local relationship to a movie, including favorite, watched, rating, note, and feedback state.

### Watch Queue
A persistent list of movies intended for later viewing. Queue membership is not evidence that the user likes a movie.

### Viewing Event
An immutable, timestamped local record of a meaningful viewing or recommendation action.

### Taste Timeline
A time-windowed projection of Viewing Events that shows how recorded activity and explicit signals changed.

## Explainability

### Recommendation Trace
The structured local explanation for a Recommendation Run, including semantic, genre, quality, negative-preference, and diversity score components.

### Candidate Trace
The portion of a Recommendation Trace that explains one candidate's eligibility and score.

## External Providers

### Provider Key
A credential supplied and owned by the user for direct access to a third-party provider. It is never a LumiTrace account credential.

### Optional Integration
A provider connection that is disabled until the user configures and invokes it. Trakt sync and Google AI Edge Gallery explanation are Optional Integrations.
