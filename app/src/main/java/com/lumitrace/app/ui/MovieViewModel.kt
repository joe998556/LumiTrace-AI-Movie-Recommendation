package com.lumitrace.app.ui

import android.app.Application
import android.content.Context
import android.content.SharedPreferences
import androidx.core.content.edit
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.google.gson.Gson
import com.lumitrace.app.data.Movie
import com.lumitrace.app.data.LibraryEntry
import com.lumitrace.app.data.LibraryState
import com.lumitrace.app.data.LocalTasteLibrary
import com.lumitrace.app.data.LocalTasteState
import com.lumitrace.app.data.LocalTasteStore
import com.lumitrace.app.data.ViewingContext
import com.lumitrace.app.data.FeedbackKind
import com.lumitrace.app.network.ApiClient
import com.lumitrace.app.network.TraktDeviceCodeRequest
import com.lumitrace.app.network.TraktDeviceTokenRequest
import com.lumitrace.app.network.TraktHistorySyncRequest
import com.lumitrace.app.network.TraktRatingSyncRequest
import com.lumitrace.app.network.TraktRefreshTokenRequest
import com.lumitrace.app.network.TraktRevokeTokenRequest
import com.lumitrace.app.network.TraktSyncPlanner
import com.lumitrace.app.network.TraktTokenResponse
import com.lumitrace.app.recommendation.LocalRecommendationEngine
import com.lumitrace.app.recommendation.RecommendationConstraints
import com.lumitrace.app.recommendation.RecommendationTrace
import com.lumitrace.app.recommendation.RecommendationVariation
import com.lumitrace.app.recommendation.TasteSignal
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import retrofit2.HttpException

sealed class UiState {
    object Idle : UiState()
    object Loading : UiState()
    data class Success(
        val movies: List<Movie>,
        val isSearch: Boolean = false,
        val aiTitle: String? = null,
        val aiSummary: String? = null,
        val recommendationTraces: Map<Int, RecommendationTrace> = emptyMap()
    ) : UiState()
    data class Error(val message: String) : UiState()
}

sealed class TonightUiState {
    object Idle : TonightUiState()
    object Loading : TonightUiState()
    data class Success(val movies: List<Movie>, val appliedContext: ViewingContext) : TonightUiState()
    data class Error(val message: String) : TonightUiState()
}

data class MovieCategoryState(
    val key: String,
    val title: String,
    val copy: String,
    val endpoint: String,
    val movies: List<Movie> = emptyList(),
    val page: Int = 0,
    val isLoading: Boolean = false,
    val isEnd: Boolean = false
)

data class MovieJournalEntry(
    val rating: Float = 0f,
    val note: String = ""
)

data class TraktUiState(
    val credentialsSaved: Boolean = false,
    val isConnected: Boolean = false,
    val isBusy: Boolean = false,
    val userCode: String = "",
    val activationUrl: String = "",
    val message: String = "Trakt is optional. Connect to import or upload watched movies and ratings."
)

class MovieViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = createPrefs(application)
    private val gson = Gson()
    private val tasteStore = LocalTasteStore(prefs, gson)
    private var tasteLibrary = tasteStore.load(legacyTasteEntries())
    private val localRecommendationEngine = LocalRecommendationEngine(application.assets)
    private val recommendationVariation = RecommendationVariation()
    private val movieDetailsCache = mutableMapOf<Int, Movie>()
    private var semanticTopK = SEMANTIC_PAGE_SIZE
    private var semanticEndReached = false
    private var semanticLoading = false
    private var lastSemanticLoadMoreAt = 0L
    private var lastSemanticLoadMoreSize = 0
    private var tmdbSearchPage = 0
    private var tmdbSearchQuery = ""
    private var tmdbSearchEndReached = false
    private var tmdbSearchLoading = false
    private var traktAuthJob: Job? = null
    private val categoryTemplates = listOf(
        MovieCategoryState(
            key = "trending",
            title = "Trending",
            copy = "What is moving across TMDB this week.",
            endpoint = "trending/movie/week"
        ),
        MovieCategoryState(
            key = "popular",
            title = "Popular",
            copy = "Broad audience picks with strong poster coverage.",
            endpoint = "movie/popular"
        ),
        MovieCategoryState(
            key = "top_rated",
            title = "Top rated",
            copy = "Highly rated films from the TMDB community.",
            endpoint = "movie/top_rated"
        ),
        MovieCategoryState(
            key = "now_playing",
            title = "Now playing",
            copy = "Current theatrical releases and fresh discoveries.",
            endpoint = "movie/now_playing"
        ),
        MovieCategoryState(
            key = "upcoming",
            title = "Upcoming",
            copy = "Future releases to keep on your radar.",
            endpoint = "movie/upcoming"
        )
    )

    private val _uiState = MutableStateFlow<UiState>(UiState.Idle)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private val _categories = MutableStateFlow(categoryTemplates)
    val categories: StateFlow<List<MovieCategoryState>> = _categories.asStateFlow()

    private val _homeMessage = MutableStateFlow("")
    val homeMessage: StateFlow<String> = _homeMessage.asStateFlow()

    private val _homeLoading = MutableStateFlow(false)
    val homeLoading: StateFlow<Boolean> = _homeLoading.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _tmdbApiKey = MutableStateFlow(prefs.getString(KEY_TMDB_API, "").orEmpty())
    val tmdbApiKey: StateFlow<String> = _tmdbApiKey.asStateFlow()

    private val _localTasteState = MutableStateFlow(tasteLibrary.snapshot())
    val localTasteState: StateFlow<LocalTasteState> = _localTasteState.asStateFlow()

    private val _watchedMovies = MutableStateFlow<Set<Movie>>(tasteLibrary.recommendationSeeds().map { it.movie }.toSet())
    val watchedMovies: StateFlow<Set<Movie>> = _watchedMovies.asStateFlow()

    private val _journalEntries = MutableStateFlow(tasteLibrary.recommendationSeeds().associate { entry ->
        entry.movie.id to MovieJournalEntry(entry.rating, entry.note)
    }.filterValues { it.rating > 0f || it.note.isNotBlank() })
    val journalEntries: StateFlow<Map<Int, MovieJournalEntry>> = _journalEntries.asStateFlow()

    private val _watchlistMovies = MutableStateFlow(tasteLibrary.watchlist().map { it.movie })
    val watchlistMovies: StateFlow<List<Movie>> = _watchlistMovies.asStateFlow()

    private val _tonightUiState = MutableStateFlow<TonightUiState>(TonightUiState.Idle)
    val tonightUiState: StateFlow<TonightUiState> = _tonightUiState.asStateFlow()

    private val _traktClientId = MutableStateFlow(prefs.getString(KEY_TRAKT_CLIENT_ID, "").orEmpty())
    val traktClientId: StateFlow<String> = _traktClientId.asStateFlow()

    private val _traktClientSecret = MutableStateFlow(prefs.getString(KEY_TRAKT_CLIENT_SECRET, "").orEmpty())
    val traktClientSecret: StateFlow<String> = _traktClientSecret.asStateFlow()

    private val _traktUiState = MutableStateFlow(
        TraktUiState(
            credentialsSaved = _traktClientId.value.isNotBlank() && _traktClientSecret.value.isNotBlank(),
            isConnected = prefs.getString(KEY_TRAKT_ACCESS_TOKEN, "").orEmpty().isNotBlank(),
            message = if (prefs.getString(KEY_TRAKT_ACCESS_TOKEN, "").orEmpty().isNotBlank()) {
                "Trakt is connected. Tokens and app credentials are stored only on this phone."
            } else {
                "Trakt is optional. Enter credentials from your own Trakt API app to connect."
            }
        )
    )
    val traktUiState: StateFlow<TraktUiState> = _traktUiState.asStateFlow()

    init {
        prefs.edit {
            LEGACY_NETWORK_KEYS.forEach { remove(it) }
        }
        if (_tmdbApiKey.value.isBlank()) {
            _homeMessage.value = "Please set your TMDB API key first."
        } else {
            refreshHome()
        }
    }

    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun searchTmdbMovies() {
        tmdbSearchPage = 0
        tmdbSearchQuery = _searchQuery.value.trim()
        tmdbSearchEndReached = false
        _uiState.value = UiState.Idle

        if (tmdbSearchQuery.isBlank()) return

        loadTmdbSearchPage(reset = true)
    }

    fun saveTmdbApiKey(key: String) {
        val cleanKey = key.trim()
        prefs.edit { putString(KEY_TMDB_API, cleanKey) }
        _tmdbApiKey.value = cleanKey
        _uiState.value = UiState.Idle

        if (cleanKey.isBlank()) {
            _categories.value = categoryTemplates
            _homeMessage.value = "Please set your TMDB API key first."
            return
        }

        refreshHome()
    }

    fun clearTmdbApiKey() {
        prefs.edit { remove(KEY_TMDB_API) }
        _tmdbApiKey.value = ""
        _categories.value = categoryTemplates
        _uiState.value = UiState.Idle
        _homeMessage.value = "Please set your TMDB API key first."
    }

    fun connectTrakt(clientId: String, clientSecret: String) {
        val cleanId = clientId.trim()
        val cleanSecret = clientSecret.trim()
        if (cleanId.isBlank() || cleanSecret.isBlank()) {
            _traktUiState.value = TraktUiState(
                credentialsSaved = false,
                message = "Enter both your Trakt Client ID and Client Secret."
            )
            return
        }

        val credentialsChanged = cleanId != _traktClientId.value || cleanSecret != _traktClientSecret.value
        prefs.edit {
            putString(KEY_TRAKT_CLIENT_ID, cleanId)
            putString(KEY_TRAKT_CLIENT_SECRET, cleanSecret)
            if (credentialsChanged) {
                TRAKT_TOKEN_KEYS.forEach { remove(it) }
            }
        }
        _traktClientId.value = cleanId
        _traktClientSecret.value = cleanSecret
        traktAuthJob?.cancel()

        traktAuthJob = viewModelScope.launch {
            _traktUiState.value = TraktUiState(
                credentialsSaved = true,
                isBusy = true,
                message = "Requesting a Trakt activation code..."
            )
            try {
                val codeResponse = ApiClient.traktService.requestDeviceCode(
                    clientId = cleanId,
                    request = TraktDeviceCodeRequest(cleanId)
                )
                val code = codeResponse.body()
                if (!codeResponse.isSuccessful || code == null) {
                    error("Trakt rejected the device request (HTTP ${codeResponse.code()}).")
                }

                val activationUrl = "${code.verificationUrl.trimEnd('/')}/${code.userCode}"
                _traktUiState.value = TraktUiState(
                    credentialsSaved = true,
                    isBusy = true,
                    userCode = code.userCode,
                    activationUrl = activationUrl,
                    message = "Approve code ${code.userCode} in Trakt. LumiTrace is polling at Trakt's required interval."
                )

                val deadline = System.currentTimeMillis() + code.expiresIn * 1_000L
                var intervalSeconds = code.interval.coerceAtLeast(MIN_TRAKT_POLL_SECONDS)
                while (System.currentTimeMillis() < deadline) {
                    delay(intervalSeconds * 1_000L)
                    val tokenResponse = ApiClient.traktService.pollDeviceToken(
                        clientId = cleanId,
                        request = TraktDeviceTokenRequest(
                            code = code.deviceCode,
                            clientId = cleanId,
                            clientSecret = cleanSecret
                        )
                    )

                    when (tokenResponse.code()) {
                        200 -> {
                            val token = tokenResponse.body() ?: error("Trakt returned an empty token response.")
                            saveTraktToken(token)
                            _traktUiState.value = TraktUiState(
                                credentialsSaved = true,
                                isConnected = true,
                                message = "Trakt connected. Import and upload are now available."
                            )
                            return@launch
                        }
                        400 -> Unit
                        429 -> intervalSeconds += TRAKT_SLOW_DOWN_SECONDS
                        404 -> error("The Trakt activation code is invalid. Start again.")
                        409 -> error("This Trakt activation code was already used. Start again.")
                        410 -> error("The Trakt activation code expired. Start again.")
                        418 -> error("Trakt access was denied.")
                        else -> error("Trakt authorization failed (HTTP ${tokenResponse.code()}).")
                    }
                }
                error("The Trakt activation code expired. Start again.")
            } catch (e: Exception) {
                _traktUiState.value = TraktUiState(
                    credentialsSaved = true,
                    isConnected = false,
                    message = safeTraktError(e)
                )
            }
        }
    }

    fun disconnectTrakt(clearCredentials: Boolean = false) {
        traktAuthJob?.cancel()
        traktAuthJob = null
        val clientId = _traktClientId.value
        val clientSecret = _traktClientSecret.value
        val accessToken = prefs.getString(KEY_TRAKT_ACCESS_TOKEN, "").orEmpty()

        clearTraktSession(clearCredentials)
        viewModelScope.launch {
            if (clientId.isNotBlank() && clientSecret.isNotBlank() && accessToken.isNotBlank()) {
                runCatching {
                    ApiClient.traktService.revokeToken(
                        clientId = clientId,
                        request = TraktRevokeTokenRequest(accessToken, clientId, clientSecret)
                    )
                }
            }
        }
    }

    fun importFromTrakt() {
        val apiKey = currentTmdbApiKey()
        if (apiKey == null) {
            _traktUiState.update { it.copy(message = "Save your TMDB key before importing Trakt movies.") }
            return
        }

        viewModelScope.launch {
            _traktUiState.update { it.copy(isBusy = true, message = "Importing Trakt history and ratings...") }
            try {
                val session = ensureValidTraktSession()
                val authorization = "Bearer ${session.accessToken}"
                val watched = ApiClient.traktService.getWatchedMovies(session.clientId, authorization)
                val ratings = ApiClient.traktService.getMovieRatings(session.clientId, authorization)

                val importedMovies = watched.mapNotNull { item ->
                    val tmdbId = item.movie.ids.tmdb ?: return@mapNotNull null
                    Movie(
                        id = tmdbId,
                        title = item.movie.title,
                        releaseDate = item.movie.year?.toString().orEmpty()
                    )
                }.distinctBy { it.id }

                val existingById = _watchedMovies.value.associateBy { it.id }
                val hydrationCandidates = importedMovies
                    .filter { existingById[it.id]?.posterPath == null }
                    .take(MAX_TRAKT_HYDRATION)
                val hydratedById = hydrateRecommendationMovies(hydrationCandidates, apiKey).associateBy { it.id }
                val mergedMovies = LinkedHashMap<Int, Movie>()
                existingById.values.forEach { mergedMovies[it.id] = it }
                importedMovies.forEach { imported ->
                    mergedMovies[imported.id] = existingById[imported.id]
                        ?: hydratedById[imported.id]
                        ?: imported
                }

                val importedRatingsById = mutableMapOf<Int, Float>()
                var importedRatings = 0
                ratings.forEach { item ->
                    val tmdbId = item.movie.ids.tmdb ?: return@forEach
                    if (tmdbId !in mergedMovies || item.rating !in 1..10) return@forEach
                    val local = tasteLibrary.activeEntries().find { it.movie.id == tmdbId }
                    if ((local?.rating ?: 0f) <= 0f) {
                        importedRatingsById[tmdbId] = item.rating.toFloat()
                        importedRatings += 1
                    }
                }

                val importedNewMovies = mergedMovies.keys.count { it !in existingById }
                tasteLibrary.mergeWatchedFromExternal(mergedMovies.values.toList(), importedRatingsById)
                publishTasteLibrary()
                _traktUiState.value = TraktUiState(
                    credentialsSaved = true,
                    isConnected = true,
                    message = "Imported $importedNewMovies new watched movies and $importedRatings ratings. Existing local decimal ratings were preserved."
                )
            } catch (e: Exception) {
                _traktUiState.update {
                    it.copy(isBusy = false, isConnected = hasStoredTraktToken(), message = safeTraktError(e))
                }
            }
        }
    }

    fun uploadToTrakt() {
        viewModelScope.launch {
            _traktUiState.update { it.copy(isBusy = true, message = "Comparing local data with Trakt...") }
            try {
                val session = ensureValidTraktSession()
                val authorization = "Bearer ${session.accessToken}"
                val remoteWatchedIds = ApiClient.traktService
                    .getWatchedMovies(session.clientId, authorization)
                    .mapNotNull { it.movie.ids.tmdb }
                    .toSet()
                val historyToAdd = TraktSyncPlanner.historyToAdd(
                    localTmdbIds = _watchedMovies.value.map { it.id },
                    remoteTmdbIds = remoteWatchedIds
                )

                historyToAdd.chunked(TRAKT_SYNC_BATCH_SIZE).forEach { batch ->
                    ApiClient.traktService.addWatchedHistory(
                        clientId = session.clientId,
                        authorization = authorization,
                        request = TraktHistorySyncRequest(batch)
                    )
                }

                val remoteRatings = ApiClient.traktService
                    .getMovieRatings(session.clientId, authorization)
                    .mapNotNull { item -> item.movie.ids.tmdb?.let { it to item.rating } }
                    .toMap()
                val ratingsToUpload = TraktSyncPlanner.ratingsToUpload(
                    localRatings = _journalEntries.value.mapValues { it.value.rating },
                    remoteRatings = remoteRatings
                )

                ratingsToUpload.chunked(TRAKT_SYNC_BATCH_SIZE).forEach { batch ->
                    ApiClient.traktService.addRatings(
                        clientId = session.clientId,
                        authorization = authorization,
                        request = TraktRatingSyncRequest(batch)
                    )
                }

                _traktUiState.value = TraktUiState(
                    credentialsSaved = true,
                    isConnected = true,
                    message = "Uploaded ${historyToAdd.size} new watched movies and ${ratingsToUpload.size} changed ratings. Local decimals remain unchanged."
                )
            } catch (e: Exception) {
                _traktUiState.update {
                    it.copy(isBusy = false, isConnected = hasStoredTraktToken(), message = safeTraktError(e))
                }
            }
        }
    }

    fun toggleWatched(movie: Movie) {
        val existing = tasteLibrary.activeEntries().find { it.movie.id == movie.id }
        if (existing?.state == LibraryState.WATCHED) {
            tasteLibrary.removeFromLibrary(movie.id)
        } else {
            tasteLibrary.markWatched(movie)
        }
        publishTasteLibrary()
    }

    fun addToWatchlist(movie: Movie) {
        tasteLibrary.addToWatchlist(movie)
        publishTasteLibrary()
    }

    fun removeFromLibrary(movieId: Int) {
        tasteLibrary.removeFromLibrary(movieId)
        publishTasteLibrary()
    }

    fun createViewingProfile(name: String) {
        tasteLibrary.createProfile(name)
        publishTasteLibrary()
    }

    fun renameViewingProfile(profileId: String, name: String) {
        tasteLibrary.renameProfile(profileId, name)
        publishTasteLibrary()
    }

    fun selectViewingProfile(profileId: String) {
        tasteLibrary.selectProfile(profileId)
        publishTasteLibrary()
    }

    fun deleteViewingProfile(profileId: String) {
        tasteLibrary.deleteProfile(profileId)
        publishTasteLibrary()
    }

    fun recordRecommendationFeedback(movie: Movie, kind: FeedbackKind) {
        tasteLibrary.recordFeedback(movie, kind)
        publishTasteLibrary()
    }

    fun exportLocalBackup(): String = tasteStore.exportJson(tasteLibrary)

    fun importLocalBackup(json: String): Result<Unit> = runCatching {
        tasteLibrary = tasteStore.importJson(json)
        publishTasteLibrary()
    }

    fun tonightShortlist(candidates: List<Movie>, context: ViewingContext): List<Movie> =
        tasteLibrary.tonightShortlist(candidates, context)

    fun buildTonight(context: ViewingContext) {
        val signals = localTasteSignals()
        if (signals.isEmpty()) {
            _tonightUiState.value = TonightUiState.Error("Mark at least one movie watched before building a Tonight shortlist.")
            return
        }
        val apiKey = currentTmdbApiKey() ?: return
        viewModelScope.launch {
            _tonightUiState.value = TonightUiState.Loading
            try {
                // Pre-filter the on-device catalog by mood/pace/genre/year so taste ranking
                // runs on films that can actually satisfy Tonight, not a random top-N slice.
                val genreGroups = LocalTasteLibrary.genreGroupsFor(context)
                val poolSize = if (context.language.isNullOrBlank()) {
                    TONIGHT_CANDIDATE_POOL
                } else {
                    // Language only exists after TMDB hydration — keep a wider pre-filter pool.
                    TONIGHT_CANDIDATE_POOL_WITH_LANGUAGE
                }
                val localResults = localRecommendationEngine.recommend(
                    signals = signals,
                    topK = poolSize,
                    constraints = RecommendationConstraints(
                        requiredGenreGroups = genreGroups,
                        minYear = context.minYear,
                        maxYear = context.maxYear,
                        diversifyStrength = if (genreGroups.isEmpty()) 0.08f else 0.03f
                    )
                )
                val watchedIds = signals.map { it.movie.id }.toSet()
                val watchlistCandidates = tasteLibrary.watchlist()
                    .map { it.movie }
                    .filterNot { it.id in watchedIds }
                val merged = (watchlistCandidates + localResults.movies).distinctBy { it.id }
                val hydrated = hydrateRecommendationMovies(merged, apiKey)
                val tasteScores = normalizeTonightTasteScores(localResults.traces)
                val picks = tasteLibrary.tonightShortlist(
                    candidates = hydrated,
                    context = context,
                    tasteScores = tasteScores
                )
                if (picks.isEmpty()) {
                    _tonightUiState.value = TonightUiState.Error("No candidates satisfied the selected local constraints. Relax a hard condition and try again.")
                } else {
                    _tonightUiState.value = TonightUiState.Success(picks, context)
                }
            } catch (e: Exception) {
                _tonightUiState.value = TonightUiState.Error(e.message ?: "Tonight could not build a local shortlist.")
            }
        }
    }

    private fun normalizeTonightTasteScores(traces: Map<Int, RecommendationTrace>): Map<Int, Float> {
        if (traces.isEmpty()) return emptyMap()
        val scores = traces.mapValues { it.value.finalScore }
        val min = scores.values.minOrNull() ?: return emptyMap()
        val max = scores.values.maxOrNull() ?: return emptyMap()
        val range = (max - min).coerceAtLeast(1e-4f)
        return scores.mapValues { (_, score) -> ((score - min) / range).coerceIn(0f, 1f) }
    }

    fun updateJournalRating(movieId: Int, rating: Float) {
        val current = _journalEntries.value[movieId] ?: MovieJournalEntry()
        tasteLibrary.setRating(movieId, rating.coerceIn(0f, MAX_USER_RATING), current.note)
        publishTasteLibrary()
    }

    fun updateJournalNote(movieId: Int, note: String) {
        val current = _journalEntries.value[movieId] ?: MovieJournalEntry()
        tasteLibrary.setRating(movieId, current.rating, note.take(MAX_NOTE_LENGTH))
        publishTasteLibrary()
    }

    fun refreshHome() {
        val apiKey = currentTmdbApiKey() ?: return
        _categories.value = categoryTemplates
        _homeMessage.value = ""
        _homeLoading.value = true
        _uiState.value = UiState.Idle

        categoryTemplates.forEach { category ->
            loadCategoryPage(category.key, apiKeyOverride = apiKey)
        }
    }

    fun fetchPopularMovies() {
        refreshHome()
    }

    fun loadMoreCategory(categoryKey: String) {
        loadCategoryPage(categoryKey)
    }

    fun resetRecommendations() {
        semanticTopK = SEMANTIC_PAGE_SIZE
        recommendationVariation.reset()
        semanticEndReached = false
        semanticLoading = false
        lastSemanticLoadMoreAt = 0L
        lastSemanticLoadMoreSize = 0
        _uiState.value = UiState.Idle
    }

    fun loadMoreTmdbSearch() {
        if (tmdbSearchQuery.isBlank() || tmdbSearchEndReached || tmdbSearchLoading || _uiState.value !is UiState.Success) return
        loadTmdbSearchPage(reset = false)
    }

    fun loadMoreSemanticMovies(seedMovies: List<Movie> = emptyList()) {
        val currentSize = (_uiState.value as? UiState.Success)?.movies?.size ?: return
        val now = System.currentTimeMillis()
        if (semanticEndReached || semanticLoading || currentSize == 0) return
        if (currentSize == lastSemanticLoadMoreSize) return
        if (now - lastSemanticLoadMoreAt < SEMANTIC_LOAD_MORE_COOLDOWN_MS) return
        lastSemanticLoadMoreAt = now
        lastSemanticLoadMoreSize = currentSize
        searchSemanticMovies(seedMovies = seedMovies, expand = true)
    }

    fun searchSemanticMovies(seedMovies: List<Movie> = emptyList(), expand: Boolean = false) {
        if (semanticLoading) return
        val signals = if (seedMovies.isEmpty()) localTasteSignals() else seedMovies.distinctBy { it.id }.map { movie ->
            TasteSignal(movie, _journalEntries.value[movie.id]?.rating ?: 0f)
        }
        if (signals.isEmpty()) {
            _uiState.value = UiState.Error("Mark at least one movie as watched to build your local taste profile.")
            return
        }
        val apiKey = currentTmdbApiKey() ?: return
        val currentResults = (_uiState.value as? UiState.Success)?.movies.orEmpty()
        val requestedTopK = if (expand) semanticTopK + SEMANTIC_PAGE_SIZE else SEMANTIC_PAGE_SIZE
        val variationSeed = recommendationVariation.seedFor(expand)

        viewModelScope.launch {
            semanticLoading = true
            if (!expand) {
                semanticEndReached = false
                lastSemanticLoadMoreAt = 0L
                lastSemanticLoadMoreSize = 0
                _uiState.value = UiState.Loading
            }
            try {
                val result = localRecommendationEngine.recommend(
                    signals = signals,
                    topK = requestedTopK,
                    variationSeed = variationSeed
                )
                val hydratedMovies = hydrateRecommendationMovies(result.movies, apiKey)

                if (hydratedMovies.isNotEmpty()) {
                    semanticEndReached = hydratedMovies.size < requestedTopK ||
                        (expand && hydratedMovies.size <= currentResults.size)
                    semanticTopK = requestedTopK
                    _uiState.value = UiState.Success(
                        movies = hydratedMovies,
                        isSearch = true,
                        aiTitle = result.title,
                        aiSummary = result.summary,
                        recommendationTraces = result.traces
                    )
                } else {
                    semanticEndReached = true
                    _uiState.value = UiState.Error("No local recommendations were available for this taste profile.")
                }
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "Local recommendation failed.")
            } finally {
                semanticLoading = false
            }
        }
    }

    private suspend fun hydrateRecommendationMovies(
        candidates: List<Movie>,
        apiKey: String
    ): List<Movie> = coroutineScope {
        val hydrated = ArrayList<Movie>(candidates.size)
        for (chunk in candidates.chunked(TMDB_HYDRATION_CONCURRENCY)) {
            val rows = chunk.map { candidate ->
                async {
                    val details = movieDetailsCache[candidate.id] ?: runCatching {
                        ApiClient.tmdbService.getMovieDetails(candidate.id, apiKey)
                    }.getOrNull()?.also { movieDetailsCache[candidate.id] = it }

                    details?.copy(
                        genreIds = details.resolvedGenreIds().ifEmpty { candidate.resolvedGenreIds() },
                        reason = candidate.reason
                    ) ?: candidate
                }
            }.awaitAll()
            hydrated += rows
        }
        hydrated
    }

    private fun loadTmdbSearchPage(reset: Boolean) {
        val apiKey = currentTmdbApiKey() ?: return
        if (tmdbSearchLoading) return

        val query = tmdbSearchQuery
        if (query.isBlank()) return

        val nextPage = if (reset) 1 else tmdbSearchPage + 1
        val existing = if (reset) emptyList() else (_uiState.value as? UiState.Success)?.movies.orEmpty()
        tmdbSearchLoading = true
        if (reset) _uiState.value = UiState.Loading

        viewModelScope.launch {
            try {
                val response = ApiClient.tmdbService.getTmdbData(
                    endpoint = "search/movie",
                    apiKey = apiKey,
                    page = nextPage,
                    query = query
                )
                val existingIds = existing.map { it.id }.toSet()
                val freshMovies = response.results
                    .filter { it.posterPath != null && it.id !in existingIds }
                tmdbSearchPage = nextPage
                tmdbSearchEndReached = freshMovies.isEmpty() || nextPage >= response.totalPages
                _uiState.value = UiState.Success(
                    movies = existing + freshMovies,
                    isSearch = true
                )
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "Search failed.")
            } finally {
                tmdbSearchLoading = false
            }
        }
    }

    private fun loadCategoryPage(categoryKey: String, apiKeyOverride: String? = null) {
        val apiKey = apiKeyOverride ?: currentTmdbApiKey() ?: return
        val current = _categories.value.firstOrNull { it.key == categoryKey } ?: return
        if (current.isLoading || current.isEnd) return

        markCategory(categoryKey) { it.copy(isLoading = true) }

        viewModelScope.launch {
            try {
                val pageToLoad = current.page + 1
                val response = ApiClient.tmdbService.getTmdbData(
                    endpoint = current.endpoint,
                    apiKey = apiKey,
                    page = pageToLoad
                )
                val existingIds = current.movies.map { it.id }.toSet()
                val freshMovies = response.results
                    .filter { it.posterPath != null && it.id !in existingIds }

                markCategory(categoryKey) {
                    it.copy(
                        movies = it.movies + freshMovies,
                        page = pageToLoad,
                        isLoading = false,
                        isEnd = freshMovies.isEmpty() || pageToLoad >= response.totalPages
                    )
                }
                _homeMessage.value = ""
            } catch (e: Exception) {
                markCategory(categoryKey) { it.copy(isLoading = false) }
                if (_categories.value.all { it.movies.isEmpty() }) {
                    _homeMessage.value = e.message ?: "Failed to load TMDB movies."
                }
            } finally {
                _homeLoading.value = _categories.value.any { it.isLoading }
            }
        }
    }

    private fun markCategory(
        categoryKey: String,
        transform: (MovieCategoryState) -> MovieCategoryState
    ) {
        _categories.update { categories ->
            categories.map { category ->
                if (category.key == categoryKey) transform(category) else category
            }
        }
        _homeLoading.value = _categories.value.any { it.isLoading }
    }

    private fun currentTmdbApiKey(): String? {
        val apiKey = _tmdbApiKey.value.trim()
        if (apiKey.isBlank()) {
            _homeMessage.value = "Please set your TMDB API key first."
            return null
        }
        return apiKey
    }

    private fun legacyTasteEntries(): List<LibraryEntry> {
        val journal = loadJournalEntries()
        return loadWatchedMovies().map { movie ->
            val entry = journal[movie.id] ?: MovieJournalEntry()
            LibraryEntry(
                movie = movie,
                state = LibraryState.WATCHED,
                rating = entry.rating,
                note = entry.note
            )
        }
    }

    private fun publishTasteLibrary() {
        tasteStore.save(tasteLibrary)
        val snapshot = tasteLibrary.snapshot()
        val active = snapshot.profiles.first { it.id == snapshot.activeProfileId }
        _localTasteState.value = snapshot
        _watchedMovies.value = active.entries.filter { it.state == LibraryState.WATCHED }.map { it.movie }.toSet()
        _watchlistMovies.value = active.entries.filter { it.state == LibraryState.WATCHLIST }
            .sortedBy { it.queuedAt ?: Long.MAX_VALUE }
            .map { it.movie }
        _journalEntries.value = active.entries
            .filter { it.state == LibraryState.WATCHED && (it.rating > 0f || it.note.isNotBlank()) }
            .associate { it.movie.id to MovieJournalEntry(it.rating, it.note) }
    }

    private fun localTasteSignals(): List<TasteSignal> {
        val profile = tasteLibrary.snapshot().profiles.first { it.id == tasteLibrary.snapshot().activeProfileId }
        val signals = LinkedHashMap<Int, TasteSignal>()
        profile.entries
            .filter { it.state == LibraryState.WATCHED }
            .forEach { entry -> signals[entry.movie.id] = TasteSignal(entry.movie, entry.rating) }
        profile.feedback.forEach { feedback ->
            val rating = when (feedback.kind) {
                FeedbackKind.MORE_LIKE_THIS -> 8f
                FeedbackKind.LESS_LIKE_THIS -> 1f
                else -> return@forEach
            }
            feedback.movie?.let { movie -> signals[movie.id] = TasteSignal(movie, rating) }
        }
        return signals.values.toList()
    }

    private fun saveJournalEntry(movieId: Int, entry: MovieJournalEntry) {
        val cleanEntry = entry.copy(note = entry.note.take(MAX_NOTE_LENGTH))
        prefs.edit {
            if (cleanEntry.rating <= 0f && cleanEntry.note.isBlank()) {
                remove("$KEY_JOURNAL_RATING_PREFIX$movieId")
                remove("$KEY_JOURNAL_NOTE_PREFIX$movieId")
            } else {
                putFloat("$KEY_JOURNAL_RATING_PREFIX$movieId", cleanEntry.rating)
                putString("$KEY_JOURNAL_NOTE_PREFIX$movieId", cleanEntry.note)
            }
        }

        _journalEntries.update { entries ->
            if (cleanEntry.rating <= 0f && cleanEntry.note.isBlank()) {
                entries - movieId
            } else {
                entries + (movieId to cleanEntry)
            }
        }
    }

    private fun saveJournalEntries(entries: Map<Int, MovieJournalEntry>) {
        prefs.edit {
            entries.forEach { (movieId, entry) ->
                val cleanRating = entry.rating.coerceIn(0f, MAX_USER_RATING)
                val cleanNote = entry.note.take(MAX_NOTE_LENGTH)
                if (cleanRating > 0f) putFloat("$KEY_JOURNAL_RATING_PREFIX$movieId", cleanRating)
                if (cleanNote.isNotBlank()) putString("$KEY_JOURNAL_NOTE_PREFIX$movieId", cleanNote)
            }
        }
        _journalEntries.value = entries.mapValues { (_, entry) ->
            entry.copy(
                rating = entry.rating.coerceIn(0f, MAX_USER_RATING),
                note = entry.note.take(MAX_NOTE_LENGTH)
            )
        }
    }

    private suspend fun ensureValidTraktSession(): TraktSession {
        val clientId = _traktClientId.value.trim()
        val clientSecret = _traktClientSecret.value.trim()
        if (clientId.isBlank() || clientSecret.isBlank()) {
            error("Trakt credentials are missing.")
        }

        val accessToken = prefs.getString(KEY_TRAKT_ACCESS_TOKEN, "").orEmpty()
        val expiresAt = prefs.getLong(KEY_TRAKT_EXPIRES_AT, 0L)
        if (accessToken.isNotBlank() && expiresAt > System.currentTimeMillis() + TRAKT_REFRESH_MARGIN_MS) {
            return TraktSession(clientId, accessToken)
        }

        val refreshToken = prefs.getString(KEY_TRAKT_REFRESH_TOKEN, "").orEmpty()
        if (refreshToken.isBlank()) error("Connect Trakt again to authorize this phone.")
        val response = ApiClient.traktService.refreshToken(
            clientId = clientId,
            request = TraktRefreshTokenRequest(
                refreshToken = refreshToken,
                clientId = clientId,
                clientSecret = clientSecret
            )
        )
        val token = response.body()
        if (!response.isSuccessful || token == null) {
            clearTraktTokens()
            error("Trakt authorization expired (HTTP ${response.code()}). Connect again.")
        }
        saveTraktToken(token)
        return TraktSession(clientId, token.accessToken)
    }

    private fun saveTraktToken(token: TraktTokenResponse) {
        val createdAtMillis = if (token.createdAt > 0L) {
            token.createdAt * 1_000L
        } else {
            System.currentTimeMillis()
        }
        prefs.edit {
            putString(KEY_TRAKT_ACCESS_TOKEN, token.accessToken)
            putString(KEY_TRAKT_REFRESH_TOKEN, token.refreshToken)
            putLong(KEY_TRAKT_EXPIRES_AT, createdAtMillis + token.expiresIn * 1_000L)
        }
    }

    private fun clearTraktSession(clearCredentials: Boolean) {
        prefs.edit {
            TRAKT_TOKEN_KEYS.forEach { remove(it) }
            if (clearCredentials) {
                remove(KEY_TRAKT_CLIENT_ID)
                remove(KEY_TRAKT_CLIENT_SECRET)
            }
        }
        if (clearCredentials) {
            _traktClientId.value = ""
            _traktClientSecret.value = ""
        }
        _traktUiState.value = TraktUiState(
            credentialsSaved = !clearCredentials && _traktClientId.value.isNotBlank() && _traktClientSecret.value.isNotBlank(),
            message = if (clearCredentials) {
                "Trakt credentials and tokens were removed from this phone."
            } else {
                "Trakt was disconnected. Your local LumiTrace profile was not changed."
            }
        )
    }

    private fun clearTraktTokens() {
        prefs.edit { TRAKT_TOKEN_KEYS.forEach { remove(it) } }
    }

    private fun hasStoredTraktToken(): Boolean {
        return prefs.getString(KEY_TRAKT_ACCESS_TOKEN, "").orEmpty().isNotBlank()
    }

    private fun safeTraktError(error: Exception): String {
        return when (error) {
            is HttpException -> "Trakt request failed (HTTP ${error.code()})."
            else -> error.message?.takeIf { it.isNotBlank() } ?: "Trakt request failed."
        }
    }

    private fun loadJournalEntries(): Map<Int, MovieJournalEntry> {
        val ids = prefs.all.keys.mapNotNull { key ->
            when {
                key.startsWith(KEY_JOURNAL_RATING_PREFIX) -> key.removePrefix(KEY_JOURNAL_RATING_PREFIX).toIntOrNull()
                key.startsWith(KEY_JOURNAL_NOTE_PREFIX) -> key.removePrefix(KEY_JOURNAL_NOTE_PREFIX).toIntOrNull()
                else -> null
            }
        }.toSet()

        return ids.mapNotNull { movieId ->
            val rating = readJournalRating(movieId)
            val note = prefs.getString("$KEY_JOURNAL_NOTE_PREFIX$movieId", "").orEmpty()
            if (rating <= 0f && note.isBlank()) {
                null
            } else {
                movieId to MovieJournalEntry(rating = rating, note = note.take(MAX_NOTE_LENGTH))
            }
        }.toMap()
    }

    private fun readJournalRating(movieId: Int): Float {
        val value = prefs.all["$KEY_JOURNAL_RATING_PREFIX$movieId"]
        return when (value) {
            is Number -> value.toFloat()
            is String -> value.toFloatOrNull() ?: 0f
            else -> 0f
        }.coerceIn(0f, MAX_USER_RATING)
    }

    private fun saveWatchedMovies(movies: Set<Movie>) {
        val json = gson.toJson(movies.toList())
        prefs.edit { putString(KEY_WATCHED_MOVIES, json) }
    }

    private fun loadWatchedMovies(): Set<Movie> {
        val json = prefs.getString(KEY_WATCHED_MOVIES, null)
        if (json.isNullOrBlank()) return emptySet()
        return try {
            parseMovieArray(JSONArray(json)).toSet()
        } catch (e: Exception) {
            emptySet()
        }
    }

    private fun parseMovieArray(array: JSONArray?): List<Movie> {
        if (array == null) return emptyList()

        val movies = mutableListOf<Movie>()
        for (index in 0 until array.length()) {
            val movieJson = array.optJSONObject(index) ?: continue
            movies.add(parseMovieObject(movieJson))
        }
        return movies
    }

    private fun parseMovieObject(movieJson: JSONObject): Movie {
        return Movie(
            id = movieJson.optIntAny("id"),
            title = movieJson.optStringAny("title", "name").ifBlank { "Untitled" },
            overview = movieJson.optStringAny("overview"),
            posterPath = movieJson.optNullableString("poster_path", "posterPath"),
            releaseDate = movieJson.optStringAny("release_date", "releaseDate"),
            voteAverage = movieJson.optDoubleAny("vote_average", "voteAverage"),
            originalLanguage = movieJson.optStringAny("original_language", "originalLanguage"),
            genreIds = movieJson.optIntListAny("genre_ids", "genreIds"),
            reason = movieJson.optNullableString("reason", "recommendation_reason", "why")
        )
    }

    private fun JSONObject.optNullableString(vararg names: String): String? {
        for (name in names) {
            if (has(name) && !isNull(name)) {
                return optString(name).takeIf { it.isNotBlank() }
            }
        }
        return null
    }

    private fun JSONObject.optStringAny(vararg names: String): String {
        return optNullableString(*names).orEmpty()
    }

    private fun JSONObject.optIntAny(vararg names: String): Int {
        for (name in names) {
            if (has(name) && !isNull(name)) {
                val value = opt(name)
                return when (value) {
                    is Number -> value.toInt()
                    is String -> value.toIntOrNull() ?: 0
                    else -> optInt(name, 0)
                }
            }
        }
        return 0
    }

    private fun JSONObject.optDoubleAny(vararg names: String): Double {
        for (name in names) {
            if (has(name) && !isNull(name)) {
                val value = opt(name)
                return when (value) {
                    is Number -> value.toDouble()
                    is String -> value.toDoubleOrNull() ?: 0.0
                    else -> optDouble(name, 0.0)
                }
            }
        }
        return 0.0
    }

    private fun JSONObject.optIntListAny(vararg names: String): List<Int> {
        for (name in names) {
            val array = optJSONArray(name) ?: continue
            val ids = mutableListOf<Int>()
            for (index in 0 until array.length()) {
                val value = array.opt(index)
                when (value) {
                    is Number -> ids.add(value.toInt())
                    is String -> value.toIntOrNull()?.let { ids.add(it) }
                }
            }
            return ids
        }
        return emptyList()
    }

    private fun createPrefs(application: Application): SharedPreferences {
        return try {
            val masterKey = MasterKey.Builder(application)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()

            EncryptedSharedPreferences.create(
                application,
                "lumitrace_secure_prefs",
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (_: Exception) {
            application.getSharedPreferences("lumitrace_prefs", Context.MODE_PRIVATE)
        }
    }

    companion object {
        private const val KEY_TMDB_API = "tmdb_api_key"
        private const val KEY_WATCHED_MOVIES = "watched_movies"
        private const val KEY_JOURNAL_RATING_PREFIX = "journal_rating_"
        private const val KEY_JOURNAL_NOTE_PREFIX = "journal_note_"
        private const val KEY_TRAKT_CLIENT_ID = "trakt_client_id"
        private const val KEY_TRAKT_CLIENT_SECRET = "trakt_client_secret"
        private const val KEY_TRAKT_ACCESS_TOKEN = "trakt_access_token"
        private const val KEY_TRAKT_REFRESH_TOKEN = "trakt_refresh_token"
        private const val KEY_TRAKT_EXPIRES_AT = "trakt_expires_at"
        private const val MAX_NOTE_LENGTH = 280
        private const val MAX_USER_RATING = 10f
        private const val SEMANTIC_PAGE_SIZE = 20
        private const val TONIGHT_CANDIDATE_POOL = 120
        private const val TONIGHT_CANDIDATE_POOL_WITH_LANGUAGE = 220
        private const val SEMANTIC_LOAD_MORE_COOLDOWN_MS = 1800L
        private const val TMDB_HYDRATION_CONCURRENCY = 5
        private const val MIN_TRAKT_POLL_SECONDS = 5
        private const val TRAKT_SLOW_DOWN_SECONDS = 5
        private const val TRAKT_REFRESH_MARGIN_MS = 60_000L
        private const val TRAKT_SYNC_BATCH_SIZE = 100
        private const val MAX_TRAKT_HYDRATION = 200
        private val TRAKT_TOKEN_KEYS = listOf(
            KEY_TRAKT_ACCESS_TOKEN,
            KEY_TRAKT_REFRESH_TOKEN,
            KEY_TRAKT_EXPIRES_AT
        )
        // Upgrade-only deletion targets: removed integrations must not leave credentials behind.
        private val LEGACY_NETWORK_KEYS = listOf(
            "remote_search_url",
            "llm_api_url",
            "llm_api_key",
            "llm_model"
        )
    }

    private data class TraktSession(
        val clientId: String,
        val accessToken: String
    )
}
