package com.lumitrace.app.ui

import android.app.Application
import android.content.Context
import android.content.SharedPreferences
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.lumitrace.app.BuildConfig
import com.lumitrace.app.data.Movie
import com.lumitrace.app.data.RecommendationRequest
import com.lumitrace.app.network.ApiClient
import java.net.URI
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

sealed class UiState {
    object Idle : UiState()
    object Loading : UiState()
    data class Success(val movies: List<Movie>, val isSearch: Boolean = false) : UiState()
    data class Error(val message: String) : UiState()
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

class MovieViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = createPrefs(application)
    private val gson = Gson()
    private var semanticTopK = SEMANTIC_PAGE_SIZE
    private var semanticEndReached = false
    private var semanticLoading = false
    private var lastSemanticLoadMoreAt = 0L
    private var lastSemanticLoadMoreSize = 0
    private var tmdbSearchPage = 0
    private var tmdbSearchQuery = ""
    private var tmdbSearchEndReached = false
    private var tmdbSearchLoading = false
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

    private val _remoteSearchUrl = MutableStateFlow(
        prefs.getString(KEY_REMOTE_SEARCH_URL, BuildConfig.REMOTE_SEARCH_URL).orEmpty()
    )
    val remoteSearchUrl: StateFlow<String> = _remoteSearchUrl.asStateFlow()

    private val _watchedMovies = MutableStateFlow<Set<Movie>>(loadWatchedMovies())
    val watchedMovies: StateFlow<Set<Movie>> = _watchedMovies.asStateFlow()

    private val _journalEntries = MutableStateFlow(loadJournalEntries())
    val journalEntries: StateFlow<Map<Int, MovieJournalEntry>> = _journalEntries.asStateFlow()

    init {
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
        prefs.edit().putString(KEY_TMDB_API, cleanKey).apply()
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
        prefs.edit().remove(KEY_TMDB_API).apply()
        _tmdbApiKey.value = ""
        _categories.value = categoryTemplates
        _uiState.value = UiState.Idle
        _homeMessage.value = "Please set your TMDB API key first."
    }

    fun saveRemoteSearchUrl(url: String) {
        val cleanUrl = url.trim()
        prefs.edit().putString(KEY_REMOTE_SEARCH_URL, cleanUrl).apply()
        _remoteSearchUrl.value = cleanUrl
    }

    fun clearRemoteSearchUrl() {
        prefs.edit().remove(KEY_REMOTE_SEARCH_URL).apply()
        _remoteSearchUrl.value = ""
    }

    fun toggleWatched(movie: Movie) {
        val current = _watchedMovies.value.toMutableSet()
        val existing = current.find { it.id == movie.id }
        if (existing != null) {
            current.remove(existing)
        } else {
            current.add(movie)
        }
        _watchedMovies.value = current
        saveWatchedMovies(current)
    }

    fun updateJournalRating(movieId: Int, rating: Float) {
        val current = _journalEntries.value[movieId] ?: MovieJournalEntry()
        saveJournalEntry(movieId, current.copy(rating = rating.coerceIn(0f, MAX_USER_RATING)))
    }

    fun updateJournalNote(movieId: Int, note: String) {
        val current = _journalEntries.value[movieId] ?: MovieJournalEntry()
        saveJournalEntry(movieId, current.copy(note = note.take(MAX_NOTE_LENGTH)))
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
        val endpoint = currentRemoteSearchUrl() ?: return
        val query = _searchQuery.value.trim()
        val tasteMovies = seedMovies.ifEmpty { _watchedMovies.value.toList() }.distinctBy { it.id }
        val journalSnapshot = _journalEntries.value
        val currentResults = (_uiState.value as? UiState.Success)?.movies.orEmpty()
        val requestedTopK = if (expand) semanticTopK + SEMANTIC_PAGE_SIZE else SEMANTIC_PAGE_SIZE

        val overviewsToSend = mutableListOf<String>()
        val genreIdsToSend = mutableListOf<List<Int>>()
        val ratingsToSend = mutableListOf<Double>()
        val releaseYearsToSend = mutableListOf<Int>()

        if (query.isNotBlank()) {
            overviewsToSend.add(query)
            genreIdsToSend.add(emptyList())
            ratingsToSend.add(EXPLICIT_QUERY_RATING.toDouble())
        }

        tasteMovies.forEach { movie ->
            val journalEntry = journalSnapshot[movie.id]
            val semanticText = buildSemanticTasteText(movie, journalEntry)
            if (semanticText.isBlank()) return@forEach
            overviewsToSend.add(semanticText)
            genreIdsToSend.add(movie.genreIds)
            movie.releaseYear()?.let { releaseYearsToSend.add(it) }
            ratingsToSend.add(
                (journalEntry?.rating?.takeIf { it > 0f } ?: NEUTRAL_USER_RATING)
                    .toDouble()
                    .coerceIn(1.0, MAX_USER_RATING.toDouble())
            )
        }

        viewModelScope.launch {
            semanticLoading = true
            if (!expand) {
                semanticEndReached = false
                lastSemanticLoadMoreAt = 0L
                lastSemanticLoadMoreSize = 0
                _uiState.value = UiState.Loading
            }
            try {
                val request = RecommendationRequest(
                    overviews = overviewsToSend,
                    excludeIds = tasteMovies.map { it.id },
                    userGenreIds = genreIdsToSend,
                    userVoteCounts = ratingsToSend,
                    userReleaseYears = releaseYearsToSend,
                    playlistGenreIds = inferPlaylistGenres(query),
                    preferredLanguages = inferPreferredLanguages(query),
                    topK = requestedTopK
                )

                val response = ApiClient.bertService.getSemanticRecommendations(
                    url = endpoint,
                    request = request
                )

                if (response.results.isNotEmpty()) {
                    semanticEndReached = response.results.size < requestedTopK ||
                        (expand && response.results.size <= currentResults.size)
                    semanticTopK = requestedTopK
                    _uiState.value = UiState.Success(response.results, isSearch = true)
                } else {
                    semanticEndReached = true
                    _uiState.value = UiState.Error(
                        response.error ?: response.fallback ?: "No semantic results found."
                    )
                }
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "Failed to reach AI engine")
            } finally {
                semanticLoading = false
            }
        }
    }

    private fun buildSemanticTasteText(movie: Movie, journalEntry: MovieJournalEntry?): String {
        val parts = mutableListOf<String>()
        if (movie.title.isNotBlank() && movie.title != "Untitled") {
            parts.add(movie.title)
        }
        movie.releaseYear()?.let { parts.add("Release year: $it") }
        if (movie.originalLanguage.isNotBlank()) {
            parts.add("Original language: ${movie.originalLanguage}")
        }
        if (movie.overview.isNotBlank()) {
            parts.add(movie.overview)
        }
        val note = journalEntry?.note?.trim().orEmpty()
        if (note.isNotBlank()) {
            parts.add("Viewer note: $note")
        }
        return parts.joinToString(". ")
    }

    private fun Movie.releaseYear(): Int? {
        val year = releaseDate.take(4).toIntOrNull() ?: return null
        return year.takeIf { it in 1888..2100 }
    }

    private fun inferPlaylistGenres(prompt: String): List<Int> {
        val text = prompt.lowercase()
        if (text.isBlank()) return emptyList()
        val genres = linkedSetOf<Int>()
        fun hasAny(vararg terms: String) = terms.any { text.contains(it) }

        if (hasAny("mystery", "suspense", "twist", "detective", "whodunit", "懸疑", "推理", "反轉")) genres.add(9648)
        if (hasAny("thriller", "tense", "psychological", "驚悚", "緊張")) genres.add(53)
        if (hasAny("crime", "noir", "heist", "criminal", "犯罪", "黑色電影")) genres.add(80)
        if (hasAny("drama", "slow burn", "slow-burn", "melancholy", "劇情", "慢節奏")) genres.add(18)
        if (hasAny("romance", "romantic", "love", "愛情", "浪漫")) genres.add(10749)
        if (hasAny("sci-fi", "science fiction", "space", "future", "科幻", "太空")) genres.add(878)
        if (hasAny("horror", "scary", "haunted", "恐怖")) genres.add(27)
        if (hasAny("comedy", "funny", "light", "喜劇", "輕鬆")) genres.add(35)
        if (hasAny("animation", "animated", "動畫")) genres.add(16)
        if (hasAny("documentary", "紀錄片")) genres.add(99)
        if (hasAny("fantasy", "magical", "myth", "奇幻", "魔法")) genres.add(14)

        return genres.toList()
    }

    private fun inferPreferredLanguages(prompt: String): List<String> {
        val text = prompt.lowercase()
        if (text.isBlank()) return emptyList()
        val languages = linkedSetOf<String>()
        fun hasAny(vararg terms: String) = terms.any { text.contains(it) }

        if (hasAny("european", "europe", "歐洲", "欧洲")) {
            languages.addAll(listOf("fr", "de", "es", "it", "da", "sv", "no", "nl", "pl", "pt", "fi"))
        }
        if (hasAny("french", "france", "法國", "法語")) languages.add("fr")
        if (hasAny("german", "germany", "德國", "德語")) languages.add("de")
        if (hasAny("spanish", "spain", "西班牙", "西語")) languages.add("es")
        if (hasAny("italian", "italy", "義大利", "義語")) languages.add("it")
        if (hasAny("japanese", "japan", "日本", "日語")) languages.add("ja")
        if (hasAny("korean", "korea", "韓國", "韓語")) languages.add("ko")
        if (hasAny("chinese", "mandarin", "taiwan", "hong kong", "中文", "華語", "台灣", "香港")) languages.add("zh")
        if (hasAny("english", "british", "american", "英語", "美國", "英國")) languages.add("en")

        return languages.toList()
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

    private fun currentRemoteSearchUrl(): String? {
        val rawEndpoint = _remoteSearchUrl.value.trim()
        if (rawEndpoint.isBlank()) {
            _uiState.value = UiState.Error("AI endpoint is not configured. Add your PC LAN endpoint in Settings.")
            return null
        }
        val endpoint = if (rawEndpoint.contains("://")) rawEndpoint else "http://$rawEndpoint"

        val uri = runCatching { URI(endpoint) }.getOrNull()
        val scheme = uri?.scheme.orEmpty().lowercase()
        val host = uri?.host.orEmpty().lowercase()
        val isHttps = scheme == "https"
        val isPrivateHttp = scheme == "http" && isPrivateNetworkHost(host)
        val isDebugHttp = BuildConfig.DEBUG && scheme == "http"
        if (!isHttps && !isPrivateHttp && !isDebugHttp) {
            _uiState.value = UiState.Error("Use HTTPS for public gateways, or a private LAN endpoint like http://192.168.x.x:5001/search.")
            return null
        }

        return endpoint
    }

    private fun isPrivateNetworkHost(host: String): Boolean {
        if (host == "localhost" || host == "127.0.0.1") return true
        if (host.startsWith("10.")) return true
        if (host.startsWith("192.168.")) return true
        val parts = host.split(".")
        if (parts.size >= 2 && parts[0] == "172") {
            val second = parts[1].toIntOrNull() ?: return false
            return second in 16..31
        }
        return false
    }

    private fun saveJournalEntry(movieId: Int, entry: MovieJournalEntry) {
        val cleanEntry = entry.copy(note = entry.note.take(MAX_NOTE_LENGTH))
        prefs.edit().apply {
            if (cleanEntry.rating <= 0f && cleanEntry.note.isBlank()) {
                remove("$KEY_JOURNAL_RATING_PREFIX$movieId")
                remove("$KEY_JOURNAL_NOTE_PREFIX$movieId")
            } else {
                putFloat("$KEY_JOURNAL_RATING_PREFIX$movieId", cleanEntry.rating)
                putString("$KEY_JOURNAL_NOTE_PREFIX$movieId", cleanEntry.note)
            }
        }.apply()

        _journalEntries.update { entries ->
            if (cleanEntry.rating <= 0f && cleanEntry.note.isBlank()) {
                entries - movieId
            } else {
                entries + (movieId to cleanEntry)
            }
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
        prefs.edit().putString(KEY_WATCHED_MOVIES, json).apply()
    }

    private fun loadWatchedMovies(): Set<Movie> {
        val json = prefs.getString(KEY_WATCHED_MOVIES, null)
        if (json.isNullOrBlank()) return emptySet()
        return try {
            val type = object : TypeToken<List<Movie>>() {}.type
            val list: List<Movie> = gson.fromJson(json, type)
            list.toSet()
        } catch (e: Exception) {
            emptySet()
        }
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
        private const val KEY_REMOTE_SEARCH_URL = "remote_search_url"
        private const val KEY_WATCHED_MOVIES = "watched_movies"
        private const val KEY_JOURNAL_RATING_PREFIX = "journal_rating_"
        private const val KEY_JOURNAL_NOTE_PREFIX = "journal_note_"
        private const val MAX_NOTE_LENGTH = 280
        private const val MAX_USER_RATING = 10f
        private const val NEUTRAL_USER_RATING = 5f
        private const val EXPLICIT_QUERY_RATING = 8f
        private const val SEMANTIC_PAGE_SIZE = 20
        private const val SEMANTIC_LOAD_MORE_COOLDOWN_MS = 1800L
    }
}
