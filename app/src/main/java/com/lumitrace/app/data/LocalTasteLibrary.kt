package com.lumitrace.app.data

import java.util.UUID

enum class LibraryState { WATCHLIST, WATCHED }

enum class FeedbackKind {
    MORE_LIKE_THIS,
    LESS_LIKE_THIS,
    ALREADY_SEEN,
    NOT_TONIGHT,
    TOO_LONG,
    UNAVAILABLE
}

data class ViewingContext(
    val maxRuntimeMinutes: Int? = null,
    val minYear: Int? = null,
    val maxYear: Int? = null,
    val language: String? = null,
    val genreIds: Set<Int> = emptySet(),
    val mood: String? = null,
    val pace: String? = null,
    val companion: String? = null
)

data class LibraryEntry(
    val movie: Movie,
    val state: LibraryState,
    val rating: Float = 0f,
    val note: String = "",
    val queuedAt: Long? = null,
    val watchedAt: Long? = null
)

data class TasteFeedback(
    val movieId: Int,
    val kind: FeedbackKind,
    val createdAt: Long,
    val movie: Movie? = null
)

data class ViewingEvent(
    val kind: String,
    val movieId: Int,
    val createdAt: Long
)

data class ViewingProfile(
    val id: String,
    val name: String,
    val entries: List<LibraryEntry> = emptyList(),
    val feedback: List<TasteFeedback> = emptyList(),
    val events: List<ViewingEvent> = emptyList()
)

data class LocalTasteState(
    val version: Int = 1,
    val activeProfileId: String,
    val profiles: List<ViewingProfile>
)

class LocalTasteLibrary(
    initial: LocalTasteState = newState(),
    private val now: () -> Long = System::currentTimeMillis,
    private val ids: () -> String = { UUID.randomUUID().toString() }
) {
    private var state = requireValid(initial)

    fun snapshot(): LocalTasteState = state

    fun createProfile(name: String): ViewingProfile {
        val clean = name.trim().take(40)
        require(clean.isNotBlank()) { "A Viewing Profile needs a name." }
        val profile = ViewingProfile(id = ids(), name = clean)
        state = state.copy(activeProfileId = profile.id, profiles = state.profiles + profile)
        return profile
    }

    fun renameProfile(profileId: String, name: String) {
        val clean = name.trim().take(40)
        require(clean.isNotBlank()) { "A Viewing Profile needs a name." }
        state = state.copy(profiles = state.profiles.map { profile ->
            if (profile.id == profileId) profile.copy(name = clean) else profile
        })
    }

    fun selectProfile(profileId: String) {
        require(state.profiles.any { it.id == profileId }) { "Unknown Viewing Profile." }
        state = state.copy(activeProfileId = profileId)
    }

    fun deleteProfile(profileId: String) {
        require(state.profiles.size > 1) { "Keep at least one Viewing Profile." }
        val remaining = state.profiles.filterNot { it.id == profileId }
        require(remaining.size != state.profiles.size) { "Unknown Viewing Profile." }
        state = state.copy(
            activeProfileId = if (state.activeProfileId == profileId) remaining.first().id else state.activeProfileId,
            profiles = remaining
        )
    }

    fun addToWatchlist(movie: Movie) = mutateActive { profile ->
        val timestamp = now()
        val existing = profile.entries.find { it.movie.id == movie.id }
        val entry = (existing ?: LibraryEntry(movie = movie, state = LibraryState.WATCHLIST, queuedAt = timestamp)).copy(
            movie = movie,
            state = LibraryState.WATCHLIST,
            queuedAt = existing?.queuedAt ?: timestamp
        )
        profile.copy(
            entries = profile.entries.replaceEntry(entry),
            events = profile.events + ViewingEvent("queued", movie.id, timestamp)
        )
    }

    fun markWatched(movie: Movie) = mutateActive { profile ->
        val timestamp = now()
        val existing = profile.entries.find { it.movie.id == movie.id }
        val entry = (existing ?: LibraryEntry(movie = movie, state = LibraryState.WATCHED)).copy(
            movie = movie,
            state = LibraryState.WATCHED,
            watchedAt = existing?.watchedAt ?: timestamp
        )
        profile.copy(
            entries = profile.entries.replaceEntry(entry),
            events = profile.events + ViewingEvent("watched", movie.id, timestamp)
        )
    }

    fun removeFromLibrary(movieId: Int) = mutateActive { profile ->
        profile.copy(
            entries = profile.entries.filterNot { it.movie.id == movieId },
            events = profile.events + ViewingEvent("removed", movieId, now())
        )
    }

    fun setRating(movieId: Int, rating: Float, note: String = "") = mutateActive { profile ->
        val entry = profile.entries.find { it.movie.id == movieId } ?: error("Rate a movie in your library first.")
        val timestamp = now()
        val normalizedRating = normalizeUserRating(rating)
        val rated = entry.copy(rating = normalizedRating, note = note.take(280))
        profile.copy(
            entries = profile.entries.replaceEntry(rated),
            events = profile.events + ViewingEvent("rated", movieId, timestamp)
        )
    }

    fun recordFeedback(movie: Movie, kind: FeedbackKind) = mutateActive { profile ->
        val timestamp = now()
        profile.copy(
            feedback = profile.feedback.filterNot { it.movieId == movie.id } + TasteFeedback(movie.id, kind, timestamp, movie),
            events = profile.events + ViewingEvent("feedback:${kind.name}", movie.id, timestamp)
        )
    }

    fun recordFeedback(movieId: Int, kind: FeedbackKind) = mutateActive { profile ->
        val timestamp = now()
        profile.copy(
            feedback = profile.feedback.filterNot { it.movieId == movieId } + TasteFeedback(movieId, kind, timestamp),
            events = profile.events + ViewingEvent("feedback:${kind.name}", movieId, timestamp)
        )
    }

    /** Merges optional external history into only the active on-device profile. */
    fun mergeWatchedFromExternal(movies: List<Movie>, ratings: Map<Int, Float>) = mutateActive { profile ->
        val timestamp = now()
        val existing = profile.entries.associateBy { it.movie.id }
        val merged = LinkedHashMap<Int, LibraryEntry>()
        profile.entries.forEach { merged[it.movie.id] = it }
        movies.distinctBy { it.id }.forEach { movie ->
            val local = existing[movie.id]
            val importedRating = ratings[movie.id]?.coerceIn(0f, 10f) ?: 0f
            merged[movie.id] = (local ?: LibraryEntry(movie = movie, state = LibraryState.WATCHED)).copy(
                movie = if (local?.movie?.posterPath != null) local.movie else movie,
                state = LibraryState.WATCHED,
                rating = if ((local?.rating ?: 0f) > 0f) local!!.rating else importedRating,
                watchedAt = local?.watchedAt ?: timestamp
            )
        }
        profile.copy(
            entries = merged.values.toList(),
            events = profile.events + ViewingEvent("external_history_merged", 0, timestamp)
        )
    }

    fun recommendationSeeds(): List<LibraryEntry> = active().entries.filter { it.state == LibraryState.WATCHED }

    fun watchlist(): List<LibraryEntry> = active().entries
        .filter { it.state == LibraryState.WATCHLIST }
        .sortedBy { it.queuedAt ?: Long.MAX_VALUE }

    fun activeEntries(): List<LibraryEntry> = active().entries

    /**
     * @param tasteScores optional 0..1 taste affinity per movie id (from the local ranker).
     * When omitted, list order is treated as a weak proxy for taste.
     */
    fun tonightShortlist(
        candidates: List<Movie>,
        context: ViewingContext,
        limit: Int = 3,
        tasteScores: Map<Int, Float> = emptyMap()
    ): List<Movie> {
        val permanentBlocked = setOf(
            FeedbackKind.ALREADY_SEEN,
            FeedbackKind.TOO_LONG,
            FeedbackKind.UNAVAILABLE
        )
        val nowMs = now()
        val excluded = buildSet {
            active().feedback.forEach { feedback ->
                when {
                    feedback.kind in permanentBlocked -> add(feedback.movieId)
                    // "Not tonight" is for this evening, not forever.
                    feedback.kind == FeedbackKind.NOT_TONIGHT &&
                        nowMs - feedback.createdAt <= NOT_TONIGHT_TTL_MS -> add(feedback.movieId)
                }
            }
            active().entries.forEach { entry ->
                if (entry.state == LibraryState.WATCHED) add(entry.movie.id)
            }
        }
        val watchlistIds = active().entries
            .asSequence()
            .filter { it.state == LibraryState.WATCHLIST }
            .map { it.movie.id }
            .toSet()
        val moodSet = moodGenres(context.mood)
        val paceSet = paceGenres(context.pace)
        val companionSet = companionGenres(context.companion)
        val explicitGenres = context.genreIds
        val take = limit.coerceIn(1, 5)
        val hasTasteScores = tasteScores.isNotEmpty()
        val fallbackDenom = (candidates.size - 1).coerceAtLeast(1).toFloat()

        // Require every selected Tonight dimension to match, then rank by blended
        // context fit + real taste score (not list position — watchlist used to steal rank 0).
        return candidates.asSequence()
            .filterNot { it.id in excluded }
            .filter { movie ->
                context.maxRuntimeMinutes == null ||
                    (movie.runtimeMinutes > 0 && movie.runtimeMinutes <= context.maxRuntimeMinutes)
            }
            .filter { movie ->
                context.language.isNullOrBlank() ||
                    movie.originalLanguage.equals(context.language, ignoreCase = true)
            }
            .filter { movie ->
                context.minYear == null ||
                    movie.releaseDate.take(4).toIntOrNull()?.let { it >= context.minYear } == true
            }
            .filter { movie ->
                context.maxYear == null ||
                    movie.releaseDate.take(4).toIntOrNull()?.let { it <= context.maxYear } == true
            }
            .filter { movie ->
                val genres = movie.resolvedGenreIds()
                explicitGenres.isEmpty() || genres.any { it in explicitGenres }
            }
            .filter { movie ->
                val genres = movie.resolvedGenreIds()
                moodSet.isEmpty() || genres.any { it in moodSet }
            }
            .filter { movie ->
                val genres = movie.resolvedGenreIds()
                paceSet.isEmpty() || genres.any { it in paceSet }
            }
            .filter { movie ->
                val genres = movie.resolvedGenreIds()
                companionSet.isEmpty() || genres.any { it in companionSet }
            }
            .mapIndexed { index, movie ->
                val fit = tonightContextFit(
                    movie = movie,
                    context = context,
                    moodSet = moodSet,
                    paceSet = paceSet,
                    companionSet = companionSet,
                    explicitGenres = explicitGenres,
                    onWatchlist = movie.id in watchlistIds
                )
                val taste = when {
                    hasTasteScores -> tasteScores[movie.id]?.coerceIn(0f, 1f)
                        ?: if (movie.id in watchlistIds) 0.55f else 0.25f
                    else -> 1f - (index.toFloat() / fallbackDenom)
                }
                val combined = fit * 0.42f + taste * 0.58f
                Triple(combined, taste, movie)
            }
            .sortedWith(
                compareByDescending<Triple<Float, Float, Movie>> { it.first }
                    .thenByDescending { it.second }
            )
            .map { it.third }
            .distinctBy { it.id }
            .take(take)
            .toList()
    }

    /**
     * Higher is better for tonight. Blends context-dimension coverage, runtime headroom,
     * quality, and a modest watchlist boost. Taste is blended separately in [tonightShortlist].
     */
    private fun tonightContextFit(
        movie: Movie,
        context: ViewingContext,
        moodSet: Set<Int>,
        paceSet: Set<Int>,
        companionSet: Set<Int>,
        explicitGenres: Set<Int>,
        onWatchlist: Boolean
    ): Float {
        var score = 0f
        val genres = movie.resolvedGenreIds()
        if (moodSet.isNotEmpty()) score += dimensionCoverage(genres, moodSet) * 1.5f
        if (paceSet.isNotEmpty()) score += dimensionCoverage(genres, paceSet) * 1.15f
        if (companionSet.isNotEmpty()) score += dimensionCoverage(genres, companionSet) * 1.15f
        if (explicitGenres.isNotEmpty()) score += dimensionCoverage(genres, explicitGenres) * 1.35f

        val maxRuntime = context.maxRuntimeMinutes
        if (maxRuntime != null && movie.runtimeMinutes > 0) {
            // Prefer films that clearly fit the time budget, not ones that barely squeeze in.
            val headroom = (maxRuntime - movie.runtimeMinutes).toFloat() / maxRuntime.toFloat()
            score += headroom.coerceIn(0f, 1f) * 0.5f
            // Mild preference for not wasting a long slot on a very short film when budget is large.
            if (maxRuntime >= 100 && movie.runtimeMinutes in 1 until 60) {
                score -= 0.12f
            }
        }

        score += (movie.voteAverage / 10.0).toFloat().coerceIn(0f, 1f) * 0.2f
        if (onWatchlist) score += 0.35f
        return score
    }

    private fun dimensionCoverage(movieGenres: List<Int>, target: Set<Int>): Float {
        if (target.isEmpty() || movieGenres.isEmpty()) return 0f
        val hits = movieGenres.count { it in target }
        // Emphasize precision (fraction of the film's tags that match) so multi-genre
        // action/comedy epics don't outrank tighter mood matches.
        val recall = (hits.toFloat() / target.size.coerceAtLeast(1)).coerceIn(0f, 1f)
        val precision = (hits.toFloat() / movieGenres.size.coerceAtLeast(1)).coerceIn(0f, 1f)
        return recall * 0.45f + precision * 0.55f
    }

    companion object {
        /** Skip suggestions for the rest of the evening, then allow them again. */
        private const val NOT_TONIGHT_TTL_MS = 18L * 60L * 60L * 1000L

        fun newState(): LocalTasteState {
            val profile = ViewingProfile(id = "default", name = "Default")
            return LocalTasteState(activeProfileId = profile.id, profiles = listOf(profile))
        }

        /** Genre groups for catalog pre-filter: each set is OR, groups are AND-ed. */
        fun genreGroupsFor(context: ViewingContext): List<Set<Int>> = buildList {
            if (context.genreIds.isNotEmpty()) add(context.genreIds)
            moodGenres(context.mood).takeIf { it.isNotEmpty() }?.let { add(it) }
            paceGenres(context.pace).takeIf { it.isNotEmpty() }?.let { add(it) }
            companionGenres(context.companion).takeIf { it.isNotEmpty() }?.let { add(it) }
        }

        fun moodGenres(mood: String?): Set<Int> = when (mood?.lowercase()) {
            // Comedy / romance / family / music — cozy rather than dark thrills.
            "warm" -> setOf(35, 10749, 10751, 10402)
            // Thriller / horror / mystery / crime / war.
            "tense" -> setOf(53, 27, 9648, 80, 10752)
            // Comedy / animation / family / adventure / music.
            "light" -> setOf(35, 16, 10751, 12, 10402)
            // Drama / sci-fi / documentary / mystery / history.
            "cerebral" -> setOf(18, 878, 99, 9648, 36)
            else -> emptySet()
        }

        fun paceGenres(pace: String?): Set<Int> = when (pace?.lowercase()) {
            "fast" -> setOf(28, 12, 53, 80, 878)
            "slow" -> setOf(18, 99, 36, 10749, 9648)
            else -> emptySet()
        }

        fun companionGenres(companion: String?): Set<Int> = when (companion?.lowercase()) {
            "solo" -> setOf(18, 878, 99, 9648, 36)
            "date" -> setOf(10749, 35, 18)
            "family" -> setOf(16, 12, 35, 10751)
            "friends" -> setOf(28, 12, 35, 53, 878)
            else -> emptySet()
        }
    }

    fun timeline(): List<ViewingEvent> = active().events.sortedByDescending { it.createdAt }

    private fun active(): ViewingProfile = state.profiles.first { it.id == state.activeProfileId }

    private fun mutateActive(transform: (ViewingProfile) -> ViewingProfile) {
        val active = active()
        state = state.copy(profiles = state.profiles.map { profile ->
            if (profile.id == active.id) transform(profile) else profile
        })
    }

    private fun List<LibraryEntry>.replaceEntry(next: LibraryEntry): List<LibraryEntry> =
        filterNot { it.movie.id == next.movie.id } + next

    private fun requireValid(candidate: LocalTasteState): LocalTasteState {
        require(candidate.profiles.isNotEmpty()) { "At least one Viewing Profile is required." }
        require(candidate.profiles.any { it.id == candidate.activeProfileId }) { "The active Viewing Profile is missing." }
        return candidate
    }
}

internal fun normalizeUserRating(rating: Float): Float {
    if (rating.isNaN()) return 0f
    if (rating.isInfinite()) {
        return if (rating > 0f) 10f else 0f
    }
    if (rating <= 0f) return 0f
    val clamped = rating.coerceIn(1f, 10f)
    return (kotlin.math.round(clamped * 10f) / 10f).coerceIn(1f, 10f)
}
