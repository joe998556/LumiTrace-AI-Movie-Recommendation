package com.lumitrace.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import coil.compose.AsyncImage
import com.lumitrace.app.data.Movie
import com.lumitrace.app.ui.AppTheme
import com.lumitrace.app.ui.Clay
import com.lumitrace.app.ui.Dim
import com.lumitrace.app.ui.GlassBg
import com.lumitrace.app.ui.Ink
import com.lumitrace.app.ui.Ink2
import com.lumitrace.app.ui.Muted
import com.lumitrace.app.ui.OuterShell
import com.lumitrace.app.ui.PanelSoft
import com.lumitrace.app.ui.PanelStrong
import com.lumitrace.app.ui.Sage
import com.lumitrace.app.ui.Teal
import com.lumitrace.app.ui.Teal2
import com.lumitrace.app.ui.Text as LumiText
import com.lumitrace.app.ui.TextSoft as LumiTextSoft
import com.lumitrace.app.ui.MovieViewModel
import com.lumitrace.app.ui.MovieCategoryState
import com.lumitrace.app.ui.MovieJournalEntry
import com.lumitrace.app.ui.UiState
import java.util.Locale
import kotlinx.coroutines.delay

private val HeavyEase = CubicBezierEasing(0.22f, 1f, 0.36f, 1f)
private val SpringEase = CubicBezierEasing(0.32f, 0.72f, 0f, 1f)
private val ShellShape = RoundedCornerShape(34.dp)
private val CoreShape = RoundedCornerShape(28.dp)
private val CardShape = RoundedCornerShape(26.dp)

private enum class AppDestination {
    Home,
    Settings,
    Recommendation,
    TasteInput
}

class MainActivity : ComponentActivity() {
    private val viewModel: MovieViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AppTheme {
                Surface(color = Ink, modifier = Modifier.fillMaxSize()) {
                    MovieScreen(viewModel)
                }
            }
        }
    }
}

@Composable
fun MovieScreen(viewModel: MovieViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    val categories by viewModel.categories.collectAsState()
    val homeMessage by viewModel.homeMessage.collectAsState()
    val homeLoading by viewModel.homeLoading.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val tmdbApiKey by viewModel.tmdbApiKey.collectAsState()
    val remoteSearchUrl by viewModel.remoteSearchUrl.collectAsState()
    val journalEntries by viewModel.journalEntries.collectAsState()
    var selectedMovie by remember { mutableStateOf<Movie?>(null) }
    val watchedMovies by viewModel.watchedMovies.collectAsState()
    var apiKeyInput by remember { mutableStateOf(tmdbApiKey) }
    var aiEndpointInput by remember { mutableStateOf(remoteSearchUrl) }
    var destination by remember { mutableStateOf(AppDestination.Home) }
    var heroIndex by remember { mutableStateOf(0) }

    val heroMovies = remember(categories) {
        categories
            .flatMap { it.movies }
            .distinctBy { it.id }
            .filter { it.posterPath != null }
            .take(16)
    }
    val watchedMovieIds = watchedMovies.map { it.id }.toSet()

    LaunchedEffect(tmdbApiKey) {
        if (apiKeyInput != tmdbApiKey) apiKeyInput = tmdbApiKey
    }

    LaunchedEffect(remoteSearchUrl) {
        if (aiEndpointInput != remoteSearchUrl) aiEndpointInput = remoteSearchUrl
    }

    LaunchedEffect(heroMovies.size, destination) {
        if (heroMovies.isEmpty() || destination != AppDestination.Home) return@LaunchedEffect
        heroIndex %= heroMovies.size
        while (true) {
            delay(5200)
            heroIndex = (heroIndex + 1) % heroMovies.size
        }
    }

    val onToggleWatched: (Movie) -> Unit = { movie ->
        viewModel.toggleWatched(movie)
    }
    val onSubmitHomeSearch: () -> Unit = {
        viewModel.resetRecommendations()
        if (searchQuery.isBlank()) {
            viewModel.fetchPopularMovies()
        } else {
            viewModel.searchTmdbMovies()
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        CinematicBackground()

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 18.dp, top = 22.dp, end = 18.dp, bottom = 34.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp)
        ) {
            item {
                Reveal(index = 0) {
                    BrandIsland(
                        tasteCount = watchedMovies.size,
                        canRecommend = true,
                        isSubPage = destination != AppDestination.Home,
                        onRecommend = {
                            viewModel.resetRecommendations()
                            destination = AppDestination.Recommendation
                        },
                        onSettings = {
                            destination = if (destination == AppDestination.Home) {
                                AppDestination.Settings
                            } else {
                                AppDestination.Home
                            }
                        }
                    )
                }
            }

            if (destination == AppDestination.Settings) {
                item {
                    Reveal(index = 1) {
                        SettingsScreen(
                            apiKey = apiKeyInput,
                            savedApiKey = tmdbApiKey,
                            aiEndpoint = aiEndpointInput,
                            savedAiEndpoint = remoteSearchUrl,
                            onApiKeyChange = { apiKeyInput = it },
                            onAiEndpointChange = { aiEndpointInput = it },
                            onSave = {
                                viewModel.saveTmdbApiKey(apiKeyInput)
                                viewModel.saveRemoteSearchUrl(aiEndpointInput)
                                destination = AppDestination.Home
                            },
                            onClear = {
                                apiKeyInput = ""
                                aiEndpointInput = ""
                                viewModel.clearTmdbApiKey()
                                viewModel.clearRemoteSearchUrl()
                            }
                        )
                    }
                }
            } else if (tmdbApiKey.isBlank()) {
                item {
                    Reveal(index = 1) {
                        ApiGatePanel(
                            message = homeMessage.ifBlank { "Please set your TMDB API key first." },
                            onOpenSettings = { destination = AppDestination.Settings }
                        )
                    }
                }
            } else if (destination == AppDestination.Recommendation) {
                item {
                    Reveal(index = 1) {
                        RecommendationScreen(
                            seedMovies = watchedMovies.toList(),
                            searchQuery = searchQuery,
                            aiEndpointReady = remoteSearchUrl.isNotBlank(),
                            onRun = { viewModel.searchSemanticMovies(watchedMovies.toList()) },
                            onOpenTasteInput = { destination = AppDestination.TasteInput },
                            onOpenSettings = { destination = AppDestination.Settings },
                            onBackHome = {
                                viewModel.resetRecommendations()
                                destination = AppDestination.Home
                            }
                        )
                    }
                }
                when (val state = uiState) {
                    UiState.Idle -> {
                        item {
                            Reveal(index = 2) {
                                RecommendationIdlePanel(
                                    canRun = watchedMovies.isNotEmpty() || searchQuery.isNotBlank()
                                )
                            }
                        }
                    }
                    UiState.Loading -> {
                        item {
                            Reveal(index = 2) {
                                LoadingPanel()
                            }
                        }
                    }
                    is UiState.Error -> {
                        item {
                            Reveal(index = 2) {
                                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                    StatusPanel(message = "AI backend is not ready yet: ${state.message}")
                                    if (watchedMovies.isNotEmpty() || searchQuery.isNotBlank()) {
                                        LumiPillButton(
                                            label = "Retry AI recommendation",
                                            onClick = { viewModel.searchSemanticMovies(watchedMovies.toList()) }
                                        )
                                    }
                                }
                            }
                        }
                    }
                    is UiState.Success -> {
                        item {
                            Reveal(index = 2) {
                                SectionHeader(
                                    eyebrow = if (searchQuery.isBlank()) "Based on watched" else "AI results",
                                    title = "Recommended for you",
                                    copy = "Scroll down for more semantic matches."
                                )
                            }
                        }
                        val recommendationRows = state.movies.chunked(2)
                        itemsIndexed(
                            items = recommendationRows,
                            key = { rowIndex, row -> "recommendation-row-$rowIndex-${row.joinToString("-") { it.id.toString() }}" }
                        ) { rowIndex, row ->
                            if (rowIndex >= recommendationRows.lastIndex - 1) {
                                LaunchedEffect(state.movies.size, rowIndex) {
                                    viewModel.loadMoreSemanticMovies(watchedMovies.toList())
                                }
                            }
                            Reveal(index = rowIndex + 3) {
                                MovieGridRow(
                                    row = row,
                                    watchedMovieIds = watchedMovieIds,
                                    onToggleWatched = onToggleWatched,
                                    onSelect = { selectedMovie = it }
                                )
                            }
                        }
                    }
                }
            } else if (destination == AppDestination.TasteInput) {
                item {
                    Reveal(index = 1) {
                        TasteInputScreen(
                            seedMovies = watchedMovies.toList(),
                            watchedMovieIds = watchedMovieIds,
                            onToggleWatched = onToggleWatched,
                            onSelect = { selectedMovie = it },
                            onBackToRecommendation = { destination = AppDestination.Recommendation },
                            onBackHome = { destination = AppDestination.Home }
                        )
                    }
                }
            } else {
                item {
                    Reveal(index = 1) {
                        SearchPanel(
                            query = searchQuery,
                            onQueryChange = viewModel::updateSearchQuery,
                            onSearch = onSubmitHomeSearch,
                            onClear = {
                                viewModel.updateSearchQuery("")
                                viewModel.fetchPopularMovies()
                            }
                        )
                    }
                }

                when (val state = uiState) {
                    UiState.Idle -> Unit
                    UiState.Loading -> {
                        item {
                            Reveal(index = 2) {
                                LoadingPanel()
                            }
                        }
                    }
                    is UiState.Error -> {
                        item {
                            Reveal(index = 2) {
                                StatusPanel(message = "Search failed: ${state.message}")
                            }
                        }
                    }
                    is UiState.Success -> {
                        item {
                            Reveal(index = 2) {
                                SectionHeader(
                                    eyebrow = if (searchQuery.isBlank()) "Based on watched" else "Search results",
                                    title = if (searchQuery.isBlank()) "Matches your watched movies" else "Results for your prompt",
                                    copy = "Semantic movie matches shown directly on the home page."
                                )
                            }
                        }
                        item {
                            Reveal(index = 3) {
                                MovieVerticalGrid(
                                    categoryKey = "home-search",
                                    movies = state.movies,
                                    watchedMovieIds = watchedMovieIds,
                                    onToggleWatched = onToggleWatched,
                                    onSelect = { selectedMovie = it },
                                    onLoadMore = { viewModel.loadMoreTmdbSearch() }
                                )
                            }
                        }
                    }
                }

                val focusMovie = if (heroMovies.isNotEmpty()) heroMovies[heroIndex % heroMovies.size] else null
                focusMovie?.let { movie ->
                    item {
                        Reveal(index = 4) {
                            SectionHeader(
                                eyebrow = "Featured signal",
                                title = "Focus poster",
                                copy = "The lead movie rotates through the live feed instead of staying fixed."
                            )
                        }
                    }
                    item {
                        Reveal(index = 5) {
                            HeroMovieCard(movie = movie, onClick = { selectedMovie = movie })
                        }
                    }
                }

                if (homeLoading && categories.all { it.movies.isEmpty() }) {
                    item {
                        Reveal(index = 6) {
                            LoadingPanel()
                        }
                    }
                }

                if (homeMessage.isNotBlank() && categories.all { it.movies.isEmpty() }) {
                    item {
                        Reveal(index = 6) {
                            StatusPanel(message = homeMessage)
                        }
                    }
                }

                itemsIndexed(categories) { index, category ->
                    if (category.movies.isNotEmpty() || category.isLoading) {
                        Reveal(index = index + 7) {
                            CategorySection(
                                category = category,
                                watchedMovieIds = watchedMovieIds,
                                onToggleWatched = onToggleWatched,
                                onSelect = { selectedMovie = it },
                                onLoadMore = { viewModel.loadMoreCategory(category.key) }
                            )
                        }
                    }
                }
            }
        }
    }

    selectedMovie?.let { movie ->
        MovieDetailDialog(
            movie = movie,
            isWatched = movie.id in watchedMovieIds,
            journalEntry = journalEntries[movie.id] ?: MovieJournalEntry(),
            onWatchedClick = { onToggleWatched(movie) },
            onRatingChange = { viewModel.updateJournalRating(movie.id, it) },
            onNoteChange = { viewModel.updateJournalNote(movie.id, it) },
            onDismiss = { selectedMovie = null }
        )
    }
}

@Composable
private fun SettingsScreen(
    apiKey: String,
    savedApiKey: String,
    aiEndpoint: String,
    savedAiEndpoint: String,
    onApiKeyChange: (String) -> Unit,
    onAiEndpointChange: (String) -> Unit,
    onSave: () -> Unit,
    onClear: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        SectionHeader(
            eyebrow = "Settings",
            title = "Private API setup",
            copy = "Keep keys and gateway URLs on this device. Open-source builds ship without a lab endpoint."
        )
        ApiKeyPanel(
            value = apiKey,
            onValueChange = onApiKeyChange,
            onSave = onSave,
            hasSavedKey = savedApiKey.isNotBlank()
        )
        AiEndpointPanel(
            value = aiEndpoint,
            onValueChange = onAiEndpointChange,
            onSave = onSave,
            hasSavedEndpoint = savedAiEndpoint.isNotBlank()
        )
        DoubleBezel {
            Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Eyebrow("Connection")
                Text("Bring your own gateway", color = LumiText, style = MaterialTheme.typography.headlineSmall)
                Text(
                    "The public source does not contain the lab server IP, gateway token, or your TMDB key. Add a local PC endpoint or HTTPS gateway only on devices you control.",
                    color = LumiTextSoft,
                    style = MaterialTheme.typography.bodyLarge
                )
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                    LumiPillButton(
                        label = "Save setup",
                        onClick = onSave,
                        modifier = Modifier.weight(1f)
                    )
                    LumiPillButton(
                        label = "Clear",
                        secondary = true,
                        onClick = onClear,
                        modifier = Modifier.weight(0.72f)
                    )
                }
            }
        }
    }
}

@Composable
private fun RecommendationScreen(
    seedMovies: List<Movie>,
    searchQuery: String,
    aiEndpointReady: Boolean,
    onRun: () -> Unit,
    onOpenTasteInput: () -> Unit,
    onOpenSettings: () -> Unit,
    onBackHome: () -> Unit
) {
    val hasTasteSignal = seedMovies.isNotEmpty() || searchQuery.isNotBlank()
    val canRun = aiEndpointReady && hasTasteSignal

    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        SectionHeader(
            eyebrow = "Recommendation",
            title = "Your AI queue",
            copy = "A dedicated space for taste signals, backend status, and recommendation results."
        )

        RecommendationControlPanel(
            seedCount = seedMovies.size,
            searchQuery = searchQuery,
            aiEndpointReady = aiEndpointReady,
            canRun = canRun,
            onOpenTasteInput = onOpenTasteInput,
            onOpenSettings = onOpenSettings,
            onRun = onRun,
            onBackHome = onBackHome
        )
    }
}

@Composable
private fun RecommendationControlPanel(
    seedCount: Int,
    searchQuery: String,
    aiEndpointReady: Boolean,
    canRun: Boolean,
    onOpenTasteInput: () -> Unit,
    onOpenSettings: () -> Unit,
    onRun: () -> Unit,
    onBackHome: () -> Unit
) {
    DoubleBezel {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Eyebrow("AI controls")
            Text(
                text = if (seedCount == 0) "Recommendation room" else "$seedCount watched movies queued",
                color = LumiText,
                style = MaterialTheme.typography.headlineSmall
            )
            Text(
                text = if (searchQuery.isBlank()) {
                    if (aiEndpointReady) {
                        "Open Taste input to review watched movies, or run AI after marking a few titles."
                    } else {
                        "Add your PC LAN endpoint or HTTPS BERT gateway in Settings before running AI recommendations."
                    }
                } else {
                    "Prompt: $searchQuery"
                },
                color = LumiTextSoft,
                style = MaterialTheme.typography.bodyLarge
            )

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                LumiPillButton(
                    label = "Taste input",
                    secondary = true,
                    onClick = onOpenTasteInput,
                    modifier = Modifier.weight(0.92f)
                )
                if (canRun) {
                    LumiPillButton(
                        label = "Run AI recommendation",
                        onClick = onRun,
                        modifier = Modifier.weight(1.35f)
                    )
                } else if (!aiEndpointReady) {
                    LumiPillButton(
                        label = "Set AI endpoint",
                        onClick = onOpenSettings,
                        modifier = Modifier.weight(1.35f)
                    )
                } else {
                    LumiPillButton(
                        label = "Browse home",
                        secondary = true,
                        onClick = onBackHome,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }
    }
}

@Composable
private fun RecommendationIdlePanel(canRun: Boolean) {
    DoubleBezel(radius = 26.dp, innerRadius = 20.dp) {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Eyebrow("Ready")
            Text(
                text = if (canRun) "Recommendation page is ready" else "Waiting for watched movies",
                color = LumiText,
                style = MaterialTheme.typography.headlineSmall
            )
            Text(
                text = if (canRun) {
                    "The UI shell is in place. Connect the IIS rewrite/BERT backend, then run the AI recommendation from this page."
                } else {
                    "Go back to Home and mark a few movies as Watched to build the taste profile."
                },
                color = LumiTextSoft,
                style = MaterialTheme.typography.bodyLarge
            )
        }
    }
}

@Composable
private fun TasteInputScreen(
    seedMovies: List<Movie>,
    watchedMovieIds: Set<Int>,
    onToggleWatched: (Movie) -> Unit,
    onSelect: (Movie) -> Unit,
    onBackToRecommendation: () -> Unit,
    onBackHome: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        SectionHeader(
            eyebrow = "Taste input",
            title = "Watched movies",
            copy = "These posters are your current taste signal for AI recommendation."
        )

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            LumiPillButton(
                label = "Recommendation",
                onClick = onBackToRecommendation,
                modifier = Modifier.weight(1.1f)
            )
            LumiPillButton(
                label = "Browse home",
                secondary = true,
                onClick = onBackHome,
                modifier = Modifier.weight(0.9f)
            )
        }

        if (seedMovies.isEmpty()) {
            StatusPanel(message = "No watched movies yet. Go home and mark films as Watched to build this input list.")
        } else {
            MovieVerticalGrid(
                categoryKey = "taste-input",
                movies = seedMovies,
                watchedMovieIds = watchedMovieIds,
                onToggleWatched = onToggleWatched,
                onSelect = onSelect
            )
        }
    }
}

@Composable
private fun ApiGatePanel(message: String, onOpenSettings: () -> Unit) {
    DoubleBezel {
        Column(modifier = Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Eyebrow("Setup required")
            Text("Please set API first.", color = LumiText, style = MaterialTheme.typography.displayLarge)
            Text(
                message.ifBlank { "Open Settings and paste your TMDB API key before loading movie posters." },
                color = LumiTextSoft,
                style = MaterialTheme.typography.bodyLarge
            )
            LumiPillButton(label = "Open Settings", onClick = onOpenSettings)
        }
    }
}

@Composable
private fun CategorySection(
    category: MovieCategoryState,
    watchedMovieIds: Set<Int>,
    onToggleWatched: (Movie) -> Unit,
    onSelect: (Movie) -> Unit,
    onLoadMore: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionHeader(
            eyebrow = "Category",
            title = category.title,
            copy = category.copy
        )
        MovieShelf(
            categoryKey = category.key,
            movies = category.movies,
            watchedMovieIds = watchedMovieIds,
            onToggleWatched = onToggleWatched,
            onSelect = onSelect,
            onLoadMore = onLoadMore
        )
        if (category.isLoading && category.movies.isNotEmpty()) {
            Text("Loading more...", color = Muted, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
        }
    }
}

@Composable
private fun MovieShelf(
    categoryKey: String,
    movies: List<Movie>,
    watchedMovieIds: Set<Int>,
    onToggleWatched: (Movie) -> Unit,
    onSelect: (Movie) -> Unit,
    onLoadMore: () -> Unit
) {
    if (movies.isEmpty()) {
        DoubleBezel(radius = 26.dp, innerRadius = 20.dp) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(174.dp),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(color = Teal, strokeWidth = 2.dp)
            }
        }
        return
    }

    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        contentPadding = PaddingValues(horizontal = 2.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        itemsIndexed(
            items = movies,
            key = { _, movie -> "$categoryKey-${movie.id}" }
        ) { index, movie ->
            if (index >= movies.lastIndex - 4) {
                LaunchedEffect(categoryKey, movies.size, index) {
                    onLoadMore()
                }
            }
            Box(modifier = Modifier.width(172.dp)) {
                MovieCard(
                    movie = movie,
                    isWatched = movie.id in watchedMovieIds,
                    onToggleWatched = { onToggleWatched(movie) },
                    onClick = { onSelect(movie) }
                )
            }
        }
    }
}

@Composable
private fun MovieVerticalGrid(
    categoryKey: String,
    movies: List<Movie>,
    watchedMovieIds: Set<Int>,
    onToggleWatched: (Movie) -> Unit,
    onSelect: (Movie) -> Unit,
    onLoadMore: (() -> Unit)? = null
) {
    if (movies.isEmpty()) {
        StatusPanel(message = "No movies to show yet.")
        return
    }

    val rows = movies.chunked(2)
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        rows.forEachIndexed { rowIndex, row ->
            if (onLoadMore != null && rowIndex >= rows.lastIndex - 1) {
                LaunchedEffect(categoryKey, movies.size, rowIndex) {
                    onLoadMore()
                }
            }
            MovieGridRow(
                row = row,
                watchedMovieIds = watchedMovieIds,
                onToggleWatched = onToggleWatched,
                onSelect = onSelect
            )
        }
    }
}

@Composable
private fun CinematicBackground() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        Color(0xFF07100F),
                        Color(0xFF11100D),
                        Color(0xFF070706)
                    )
                )
            )
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val lineColor = LumiText.copy(alpha = 0.035f)
            val accent = Teal.copy(alpha = 0.08f)

            for (x in 0..size.width.toInt() step 92) {
                drawLine(
                    color = lineColor,
                    start = Offset(x.toFloat(), 0f),
                    end = Offset(x.toFloat() + size.height * 0.18f, size.height),
                    strokeWidth = 1f
                )
            }

            drawPath(
                path = Path().apply {
                    moveTo(size.width * 0.58f, size.height * 0.12f)
                    lineTo(size.width * 1.05f, size.height * 0.28f)
                    lineTo(size.width * 0.88f, size.height * 0.74f)
                    lineTo(size.width * 0.46f, size.height * 0.58f)
                    close()
                },
                color = accent
            )

            drawLine(
                color = Teal2.copy(alpha = 0.08f),
                start = Offset(size.width * 0.04f, size.height * 0.32f),
                end = Offset(size.width * 0.96f, size.height * 0.22f),
                strokeWidth = 1.2f
            )
        }
    }
}

@Composable
private fun Reveal(index: Int, content: @Composable () -> Unit) {
    var visible by remember { mutableStateOf(false) }
    val density = LocalDensity.current
    val alpha by animateFloatAsState(
        targetValue = if (visible) 1f else 0f,
        animationSpec = tween(durationMillis = 820, delayMillis = index.coerceAtMost(10) * 55, easing = HeavyEase),
        label = "revealAlpha"
    )
    val y by animateFloatAsState(
        targetValue = if (visible) 0f else 34f,
        animationSpec = tween(durationMillis = 900, delayMillis = index.coerceAtMost(10) * 55, easing = HeavyEase),
        label = "revealY"
    )

    LaunchedEffect(Unit) {
        visible = true
    }

    Box(
        modifier = Modifier
            .alpha(alpha)
            .graphicsLayer {
                translationY = with(density) { y.dp.toPx() }
            }
    ) {
        content()
    }
}

@Composable
private fun BrandIsland(
    tasteCount: Int,
    canRecommend: Boolean,
    isSubPage: Boolean,
    onRecommend: () -> Unit,
    onSettings: () -> Unit
) {
    DoubleBezel(radius = 30.dp, innerRadius = 25.dp) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .clip(RoundedCornerShape(21.dp))
                        .background(Brush.linearGradient(listOf(Teal.copy(alpha = 0.65f), Teal2.copy(alpha = 0.32f)))),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "L",
                        color = LumiText,
                        fontFamily = FontFamily.Serif,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp
                    )
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text("LumiTrace", color = LumiText, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Text(
                        "TASTE ENGINE",
                        color = LumiTextSoft,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 9.sp,
                        letterSpacing = 2.sp
                    )
                }
            }

            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (!isSubPage) {
                    MiniRecommendButton(
                        tasteCount = tasteCount,
                        enabled = canRecommend,
                        onClick = onRecommend
                    )
                }
                RoundIconButton(label = if (isSubPage) "Back home" else "Settings", secondary = true, onClick = onSettings) {
                    if (isSubPage) {
                        ThinCloseIcon(color = LumiTextSoft, modifier = Modifier.size(15.dp))
                    } else {
                        ThinSlidersIcon(color = LumiTextSoft, modifier = Modifier.size(17.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun HeroPanel() {
    DoubleBezel {
        Column(modifier = Modifier.padding(22.dp)) {
            Eyebrow("AI movie recommendation")
            Spacer(modifier = Modifier.height(14.dp))
            Text(
                text = "Trace your taste.",
                color = LumiText,
                style = MaterialTheme.typography.displayLarge,
                maxLines = 2
            )
            Spacer(modifier = Modifier.height(14.dp))
            Text(
                text = "Paste a TMDB API key, browse live movie data, save films that feel right, then ask LumiTrace for AI recommendations.",
                color = LumiTextSoft,
                style = MaterialTheme.typography.bodyLarge
            )
            Spacer(modifier = Modifier.height(22.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                MetricCard("30k", "xlarge vectors", Modifier.weight(1f))
                MetricCard("BERT", "semantic mode", Modifier.weight(1f))
                MetricCard("local", "your key", Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun ApiKeyPanel(
    value: String,
    onValueChange: (String) -> Unit,
    onSave: () -> Unit,
    hasSavedKey: Boolean
) {
    DoubleBezel {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Eyebrow("Start here")
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Connect TMDB", color = LumiText, fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
                }
                StatusDot(active = hasSavedKey)
            }
            Text(
                "Your TMDB key stays on this device. LumiTrace only sends movie taste signals to the AI gateway.",
                color = Muted,
                fontSize = 12.sp,
                lineHeight = 18.sp
            )
            LumiTextField(
                value = value,
                onValueChange = onValueChange,
                placeholder = "Paste your TMDB API key",
                secret = true,
                trailing = {
                    RoundIconButton(label = "Save key", onClick = onSave) {
                        ThinCheckIcon(color = Ink, modifier = Modifier.size(17.dp))
                    }
                }
            )
        }
    }
}

@Composable
private fun AiEndpointPanel(
    value: String,
    onValueChange: (String) -> Unit,
    onSave: () -> Unit,
    hasSavedEndpoint: Boolean
) {
    DoubleBezel {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Eyebrow("Optional AI")
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Connect BERT gateway", color = LumiText, fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
                }
                StatusDot(active = hasSavedEndpoint)
            }
            Text(
                "Paste the endpoint shown by the Windows AI setup script, such as 192.168.1.23:5001/search. HTTPS gateways also work.",
                color = Muted,
                fontSize = 12.sp,
                lineHeight = 18.sp
            )
            LumiTextField(
                value = value,
                onValueChange = onValueChange,
                placeholder = "192.168.1.23:5001/search",
                onSubmit = onSave,
                trailing = {
                    RoundIconButton(label = "Save endpoint", onClick = onSave) {
                        ThinCheckIcon(color = Ink, modifier = Modifier.size(17.dp))
                    }
                }
            )
        }
    }
}

@Composable
private fun SearchPanel(
    query: String,
    onQueryChange: (String) -> Unit,
    onSearch: () -> Unit,
    onClear: () -> Unit
) {
    DoubleBezel {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Eyebrow("Ask the engine")
                Spacer(modifier = Modifier.weight(1f))
                Text("BERT gateway", color = Teal2, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
            }
            LumiTextField(
                value = query,
                onValueChange = onQueryChange,
                placeholder = "Describe a movie or mark watched...",
                onSubmit = onSearch,
                trailing = {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (query.isNotBlank()) {
                            RoundIconButton(label = "Clear", secondary = true, onClick = onClear) {
                                ThinCloseIcon(color = LumiTextSoft, modifier = Modifier.size(16.dp))
                            }
                        }
                        RoundIconButton(label = "Search", onClick = onSearch) {
                            ThinSearchIcon(color = Ink, modifier = Modifier.size(17.dp))
                        }
                    }
                }
            )
        }
    }
}

@Composable
private fun LoadingPanel() {
    DoubleBezel {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(14.dp)) {
                CircularProgressIndicator(color = Teal, strokeWidth = 2.dp)
                Text("Tracing movie signals...", color = LumiTextSoft, fontSize = 13.sp)
            }
        }
    }
}

@Composable
private fun StatusPanel(message: String) {
    DoubleBezel {
        Column(modifier = Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Eyebrow("Status")
            Text("Waiting for a signal", color = LumiText, style = MaterialTheme.typography.headlineSmall)
            Text(message, color = LumiTextSoft, style = MaterialTheme.typography.bodyLarge)
        }
    }
}

@Composable
private fun SectionHeader(eyebrow: String, title: String, copy: String) {
    Column(modifier = Modifier.padding(top = 4.dp, bottom = 2.dp)) {
        Eyebrow(eyebrow)
        Spacer(modifier = Modifier.height(8.dp))
        Text(title, color = LumiText, style = MaterialTheme.typography.headlineSmall)
        Spacer(modifier = Modifier.height(6.dp))
        Text(copy, color = Muted, fontSize = 13.sp, lineHeight = 19.sp)
    }
}

@Composable
private fun MovieGridRow(
    row: List<Movie>,
    watchedMovieIds: Set<Int>,
    onToggleWatched: (Movie) -> Unit,
    onSelect: (Movie) -> Unit
) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
        row.forEach { movie ->
            Box(modifier = Modifier.weight(1f)) {
                MovieCard(
                    movie = movie,
                    isWatched = movie.id in watchedMovieIds,
                    onToggleWatched = { onToggleWatched(movie) },
                    onClick = { onSelect(movie) }
                )
            }
        }
        if (row.size == 1) Spacer(modifier = Modifier.weight(1f))
    }
}

@Composable
private fun HeroMovieCard(movie: Movie, onClick: () -> Unit) {
    DoubleBezel(radius = 34.dp, innerRadius = 28.dp) {
        PressableScale(onClick = onClick) { pressModifier ->
            Box(
                modifier = pressModifier
                    .fillMaxWidth()
                    .aspectRatio(0.74f)
                    .clip(RoundedCornerShape(28.dp))
            ) {
                MoviePoster(movie = movie, imageSize = "w780", modifier = Modifier.fillMaxSize())
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(
                            Brush.verticalGradient(
                                listOf(
                                    Color.Transparent,
                                    Color(0x22000000),
                                    Color(0xEE070706)
                                )
                            )
                        )
                )
                Column(
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .padding(22.dp)
                ) {
                    RatingPill(movie.voteAverage)
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = movie.title,
                        color = Color.White,
                        fontFamily = FontFamily.Serif,
                        fontSize = 30.sp,
                        lineHeight = 31.sp,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = movie.overview,
                        color = Color.White.copy(alpha = 0.76f),
                        fontSize = 13.sp,
                        lineHeight = 19.sp,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}

@Composable
private fun MovieCard(
    movie: Movie,
    isWatched: Boolean,
    onToggleWatched: () -> Unit,
    onClick: () -> Unit
) {
    DoubleBezel(radius = 26.dp, innerRadius = 20.dp, outerPadding = 5.dp) {
        Box(modifier = Modifier.fillMaxWidth()) {
            Column {
                PressableScale(onClick = onClick) { pressModifier ->
                    Box(
                        modifier = pressModifier
                            .fillMaxWidth()
                            .aspectRatio(0.68f)
                            .clip(RoundedCornerShape(18.dp))
                            .background(PanelSoft)
                    ) {
                        MoviePoster(movie = movie, imageSize = "w500", modifier = Modifier.fillMaxSize())
                    }
                }
                Column(
                    modifier = Modifier.padding(start = 10.dp, top = 10.dp, end = 10.dp, bottom = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(7.dp)
                ) {
                    Text(
                        text = movie.title,
                        color = LumiText,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        lineHeight = 17.sp,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(7.dp)
                    ) {
                        RatingPill(movie.voteAverage)
                        WatchedButton(isWatched = isWatched, onClick = onToggleWatched)
                    }
                }
            }
        }
    }
}

@Composable
private fun MoviePoster(movie: Movie, imageSize: String, modifier: Modifier = Modifier) {
    if (movie.posterPath != null) {
        AsyncImage(
            model = "https://image.tmdb.org/t/p/$imageSize${movie.posterPath}",
            contentDescription = movie.title,
            contentScale = ContentScale.Crop,
            modifier = modifier
        )
    } else {
        Box(modifier = modifier.background(GlassBg), contentAlignment = Alignment.Center) {
            Text("No poster", color = Muted, fontSize = 12.sp)
        }
    }
}

@Composable
private fun MovieDetailDialog(
    movie: Movie,
    isWatched: Boolean,
    journalEntry: MovieJournalEntry,
    onWatchedClick: () -> Unit,
    onRatingChange: (Float) -> Unit,
    onNoteChange: (String) -> Unit,
    onDismiss: () -> Unit
) {
    Dialog(onDismissRequest = onDismiss) {
        DoubleBezel(radius = 34.dp, innerRadius = 28.dp) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Row(verticalAlignment = Alignment.Top) {
                    Column(modifier = Modifier.weight(1f)) {
                        Eyebrow("Movie detail")
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = movie.title,
                            color = LumiText,
                            style = MaterialTheme.typography.headlineSmall,
                            maxLines = 3,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                    RoundIconButton(label = "Close", secondary = true, onClick = onDismiss) {
                        ThinCloseIcon(color = LumiTextSoft, modifier = Modifier.size(16.dp))
                    }
                }
                RatingPill(movie.voteAverage)
                Text(movie.overview, color = LumiTextSoft, style = MaterialTheme.typography.bodyLarge)
                DetailWatchedButton(
                    isWatched = isWatched,
                    onClick = onWatchedClick,
                    modifier = Modifier.fillMaxWidth()
                )
                MovieJournalPanel(
                    entry = journalEntry,
                    onRatingChange = onRatingChange,
                    onNoteChange = onNoteChange
                )
            }
        }
    }
}

@Composable
private fun MovieJournalPanel(
    entry: MovieJournalEntry,
    onRatingChange: (Float) -> Unit,
    onNoteChange: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Eyebrow("Your journal")
                Spacer(modifier = Modifier.height(7.dp))
                Text(
                    text = if (entry.rating > 0f) {
                        "Your score: ${formatRating(entry.rating)}/10"
                    } else {
                        "Add your score"
                    },
                    color = LumiText,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp
                )
            }
            if (entry.rating > 0f) {
                SmallTextButton(label = "Clear", onClick = { onRatingChange(0f) })
            }
        }

        PersonalRatingSlider(
            rating = entry.rating,
            onRatingChange = onRatingChange
        )

        MovieNoteField(
            value = entry.note,
            onValueChange = onNoteChange
        )
    }
}

@Composable
private fun PersonalRatingSlider(
    rating: Float,
    onRatingChange: (Float) -> Unit
) {
    val sliderValue = if (rating > 0f) rating else 5f
    val animatedRating by animateFloatAsState(
        targetValue = sliderValue,
        animationSpec = tween(durationMillis = 420, easing = HeavyEase),
        label = "journalRatingGlow"
    )
    val progress = (animatedRating / 10f).coerceIn(0f, 1f)
    val signalLabel = when {
        rating <= 0f -> "Not scored"
        rating < 5f -> "Reduce similar"
        rating == 5f -> "Neutral"
        else -> "Boost similar"
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(Color.White.copy(alpha = 0.045f))
    ) {
        Column(
            modifier = Modifier.padding(start = 14.dp, top = 10.dp, end = 14.dp, bottom = 10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = formatRating(animatedRating),
                    color = LumiText,
                    fontSize = 22.sp,
                    lineHeight = 24.sp,
                    fontWeight = FontWeight.ExtraBold
                )
                Text(signalLabel, color = LumiTextSoft, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(if (rating > 0f) Teal.copy(alpha = 0.16f) else Color.White.copy(alpha = 0.06f))
                        .padding(horizontal = 9.dp, vertical = 5.dp)
                ) {
                    Text("1-10", color = if (rating > 0f) Teal2 else Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                }
            }
            DotRatingSlider(
                value = sliderValue,
                onValueChange = onRatingChange
            )
        }
    }
}

@Composable
private fun DotRatingSlider(value: Float, onValueChange: (Float) -> Unit) {
    val animatedValue by animateFloatAsState(
        targetValue = value,
        animationSpec = tween(durationMillis = 260, easing = SpringEase),
        label = "dotRatingSlider"
    )
    val progress = ((animatedValue - 1f) / 9f).coerceIn(0f, 1f)

    fun normalizedScore(offsetX: Float, width: Int, insetPx: Float): Float {
        val trackWidth = (width - insetPx * 2f).coerceAtLeast(1f)
        val ratio = ((offsetX - insetPx) / trackWidth).coerceIn(0f, 1f)
        return (kotlin.math.round((1f + ratio * 9f) * 10f) / 10f).coerceIn(1f, 10f)
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(28.dp)
            .pointerInput(Unit) {
                fun update(offsetX: Float) {
                    onValueChange(normalizedScore(offsetX, size.width, 7.dp.toPx()))
                }
                detectTapGestures { tapOffset -> update(tapOffset.x) }
            }
            .pointerInput(Unit) {
                fun update(offsetX: Float) {
                    onValueChange(normalizedScore(offsetX, size.width, 7.dp.toPx()))
                }
                detectDragGestures(
                    onDragStart = { dragOffset -> update(dragOffset.x) },
                    onDrag = { change, _ -> update(change.position.x) }
                )
            }
    ) {
        Canvas(modifier = Modifier.matchParentSize()) {
            val inset = 7.dp.toPx()
            val trackHeight = 5.dp.toPx()
            val trackWidth = size.width - inset * 2f
            val y = size.height / 2f
            val trackTop = y - trackHeight / 2f
            val dotX = inset + trackWidth * progress

            drawRoundRect(
                color = Color.White.copy(alpha = 0.16f),
                topLeft = Offset(inset, trackTop),
                size = Size(trackWidth, trackHeight),
                cornerRadius = CornerRadius(trackHeight, trackHeight)
            )
            drawRoundRect(
                brush = Brush.horizontalGradient(listOf(Teal.copy(alpha = 0.70f), Teal2)),
                topLeft = Offset(inset, trackTop),
                size = Size(trackWidth * progress, trackHeight),
                cornerRadius = CornerRadius(trackHeight, trackHeight)
            )
            drawCircle(color = Teal2.copy(alpha = 0.18f), radius = 11.dp.toPx(), center = Offset(dotX, y))
            drawCircle(color = Teal2, radius = 5.5.dp.toPx(), center = Offset(dotX, y))
            drawCircle(color = LumiText.copy(alpha = 0.75f), radius = 2.dp.toPx(), center = Offset(dotX, y))
        }
    }
}

private fun formatRating(score: Float): String = String.format(Locale.US, "%.1f", score)

@Composable
private fun MovieNoteField(value: String, onValueChange: (String) -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(112.dp)
            .clip(RoundedCornerShape(22.dp))
            .background(Color.White.copy(alpha = 0.055f))
            .padding(14.dp)
    ) {
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            textStyle = TextStyle(color = LumiText, fontSize = 13.sp, lineHeight = 18.sp),
            cursorBrush = SolidColor(Teal),
            modifier = Modifier.fillMaxWidth(),
            decorationBox = { innerTextField ->
                if (value.isEmpty()) {
                    Text("Write a short thought after watching...", color = Dim, fontSize = 13.sp, lineHeight = 18.sp)
                }
                innerTextField()
            }
        )
    }
}

@Composable
private fun SmallTextButton(label: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(Color.White.copy(alpha = 0.06f))
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 7.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(label, color = LumiTextSoft, fontSize = 10.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun DetailWatchedButton(
    isWatched: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.97f else 1f,
        animationSpec = tween(durationMillis = 320, easing = SpringEase),
        label = "detailWatchedScale"
    )
    val textColor = if (isWatched) Ink else LumiTextSoft

    Row(
        modifier = modifier
            .scale(scale)
            .clip(RoundedCornerShape(999.dp))
            .then(
                if (isWatched) {
                    Modifier.background(Brush.linearGradient(listOf(Teal, Teal2)))
                } else {
                    Modifier.background(Color.White.copy(alpha = 0.055f))
                }
            )
            .clickable(
                interactionSource = source,
                indication = null,
                onClickLabel = if (isWatched) "Mark unwatched" else "Mark watched",
                onClick = onClick
            )
            .height(56.dp)
            .padding(start = 18.dp, end = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(
            text = if (isWatched) "Watched" else "Mark watched",
            color = textColor,
            fontSize = 13.sp,
            fontWeight = FontWeight.ExtraBold
        )
        Box(
            modifier = Modifier
                .size(32.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(if (isWatched) Color.Black.copy(alpha = 0.08f) else Color.White.copy(alpha = 0.06f)),
            contentAlignment = Alignment.Center
        ) {
            if (isWatched) {
                ThinCheckIcon(color = Ink, modifier = Modifier.size(16.dp))
            } else {
                ThinEyeIcon(color = LumiTextSoft, modifier = Modifier.size(16.dp))
            }
        }
    }
}

@Composable
private fun DoubleBezel(
    modifier: Modifier = Modifier,
    radius: androidx.compose.ui.unit.Dp = 34.dp,
    innerRadius: androidx.compose.ui.unit.Dp = 28.dp,
    outerPadding: androidx.compose.ui.unit.Dp = 6.dp,
    content: @Composable () -> Unit
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .shadow(18.dp, RoundedCornerShape(radius), ambientColor = Color.Black.copy(alpha = 0.15f), spotColor = Color.Black.copy(alpha = 0.18f))
            .clip(RoundedCornerShape(radius))
            .background(OuterShell)
            .padding(outerPadding)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(innerRadius))
                .background(PanelStrong)
        ) {
            content()
        }
    }
}

@Composable
private fun LumiTextField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    secret: Boolean = false,
    onSubmit: (() -> Unit)? = null,
    trailing: @Composable () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(22.dp))
            .background(Color.White.copy(alpha = 0.055f))
            .padding(start = 16.dp, top = 8.dp, end = 8.dp, bottom = 8.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            BasicTextField(
                value = value,
                onValueChange = onValueChange,
                singleLine = true,
                textStyle = TextStyle(color = LumiText, fontSize = 14.sp, lineHeight = 20.sp),
                cursorBrush = SolidColor(Teal),
                visualTransformation = if (secret) PasswordVisualTransformation() else VisualTransformation.None,
                keyboardOptions = KeyboardOptions(imeAction = if (onSubmit != null) ImeAction.Search else ImeAction.Done),
                keyboardActions = KeyboardActions(
                    onSearch = { onSubmit?.invoke() },
                    onDone = { onSubmit?.invoke() }
                ),
                modifier = Modifier.weight(1f),
                decorationBox = { innerTextField ->
                    if (value.isEmpty()) {
                        Text(placeholder, color = Dim, fontSize = 13.sp)
                    }
                    innerTextField()
                }
            )
            Spacer(modifier = Modifier.width(10.dp))
            trailing()
        }
    }
}

@Composable
private fun MetricCard(value: String, label: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(18.dp))
            .background(Color.White.copy(alpha = 0.045f))
            .padding(12.dp)
    ) {
        Column {
            Text(value, color = LumiText, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp, maxLines = 1)
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                label,
                color = Muted,
                fontFamily = FontFamily.Monospace,
                fontSize = 8.sp,
                lineHeight = 11.sp,
                letterSpacing = 0.8.sp,
                maxLines = 2
            )
        }
    }
}

@Composable
private fun Eyebrow(text: String) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(Teal.copy(alpha = 0.12f))
            .padding(horizontal = 11.dp, vertical = 6.dp)
    ) {
        Text(
            text = text.uppercase(),
            color = Teal2,
            style = MaterialTheme.typography.labelSmall
        )
    }
}

@Composable
private fun RatingPill(score: Double) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(Color.Black.copy(alpha = 0.34f))
            .padding(horizontal = 9.dp, vertical = 6.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
            Text("TMDB", color = Teal2, fontSize = 8.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
            Text(String.format("%.1f", score), color = LumiText, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun StatusDot(active: Boolean) {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(if (active) Teal.copy(alpha = 0.12f) else Clay.copy(alpha = 0.11f))
            .padding(horizontal = 10.dp, vertical = 7.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(7.dp)
    ) {
        Box(
            modifier = Modifier
                .size(7.dp)
                .clip(RoundedCornerShape(999.dp))
                .background(if (active) Teal2 else Clay)
        )
        Text(if (active) "READY" else "LOCAL", color = LumiTextSoft, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
    }
}

@Composable
private fun MiniRecommendButton(tasteCount: Int, enabled: Boolean, onClick: () -> Unit) {
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.97f else 1f,
        animationSpec = tween(durationMillis = 360, easing = SpringEase),
        label = "miniRecommendScale"
    )
    val alpha = if (enabled) 1f else 0.66f

    Row(
        modifier = Modifier
            .scale(scale)
            .alpha(alpha)
            .clip(RoundedCornerShape(999.dp))
            .background(
                Brush.linearGradient(
                    listOf(
                        Teal.copy(alpha = 0.82f),
                        Teal2.copy(alpha = 0.68f)
                    )
                )
            )
            .clickable(
                interactionSource = source,
                indication = null,
                enabled = enabled,
                onClick = onClick
            )
            .height(56.dp)
            .padding(start = 9.dp, top = 7.dp, end = 13.dp, bottom = 7.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Box(
            modifier = Modifier
                .size(34.dp)
                .clip(RoundedCornerShape(17.dp))
                .background(Color.White.copy(alpha = 0.10f)),
            contentAlignment = Alignment.Center
        ) {
            Text("AI", color = Ink, fontWeight = FontWeight.Black, fontSize = 11.sp, lineHeight = 11.sp)
        }
        Column(
            modifier = Modifier.height(34.dp),
            verticalArrangement = Arrangement.Center
        ) {
            Text("Recommend", color = Ink, fontWeight = FontWeight.ExtraBold, fontSize = 11.sp, lineHeight = 12.sp)
            Text("$tasteCount watched", color = Ink.copy(alpha = 0.70f), fontSize = 8.sp, lineHeight = 10.sp, fontFamily = FontFamily.Monospace)
        }
    }
}

@Composable
private fun LumiPillButton(
    label: String,
    modifier: Modifier = Modifier,
    secondary: Boolean = false,
    onClick: () -> Unit
) {
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.97f else 1f,
        animationSpec = tween(durationMillis = 340, easing = SpringEase),
        label = "pillScale"
    )

    Row(
        modifier = modifier
            .scale(scale)
            .clip(RoundedCornerShape(999.dp))
            .then(
                if (secondary) {
                    Modifier.background(Color.White.copy(alpha = 0.055f))
                } else {
                    Modifier.background(Brush.linearGradient(listOf(Teal, Teal2)))
                }
            )
            .clickable(interactionSource = source, indication = null, onClick = onClick)
            .padding(start = 17.dp, top = 9.dp, end = 9.dp, bottom = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text(
            label,
            color = if (secondary) LumiTextSoft else Ink,
            fontSize = 12.sp,
            fontWeight = FontWeight.ExtraBold
        )
        Box(
            modifier = Modifier
                .size(29.dp)
                .clip(RoundedCornerShape(999.dp))
                .background(if (secondary) Color.White.copy(alpha = 0.06f) else Color.Black.copy(alpha = 0.08f)),
            contentAlignment = Alignment.Center
        ) {
            ThinCheckIcon(
                color = if (secondary) LumiTextSoft else Ink,
                modifier = Modifier.size(15.dp)
            )
        }
    }
}

@Composable
private fun RoundIconButton(
    label: String,
    secondary: Boolean = false,
    onClick: () -> Unit,
    content: @Composable () -> Unit
) {
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.94f else 1f,
        animationSpec = tween(durationMillis = 320, easing = SpringEase),
        label = "roundIconScale"
    )

    Box(
        modifier = Modifier
            .scale(scale)
            .size(42.dp)
            .clip(RoundedCornerShape(21.dp))
            .then(
                if (secondary) {
                    Modifier.background(Color.White.copy(alpha = 0.055f))
                } else {
                    Modifier.background(Brush.linearGradient(listOf(Teal, Teal2)))
                }
            )
            .clickable(interactionSource = source, indication = null, onClickLabel = label, onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        content()
    }
}

@Composable
private fun WatchedButton(isWatched: Boolean, onClick: () -> Unit) {
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.92f else 1f,
        animationSpec = tween(durationMillis = 300, easing = SpringEase),
        label = "watchedButtonScale"
    )
    val textColor = if (isWatched) Ink else LumiTextSoft

    Row(
        modifier = Modifier
            .scale(scale)
            .height(30.dp)
            .width(if (isWatched) 82.dp else 78.dp)
            .clip(RoundedCornerShape(999.dp))
            .then(
                if (isWatched) {
                    Modifier.background(Brush.linearGradient(listOf(Teal, Teal2)))
                } else {
                    Modifier.background(Color.White.copy(alpha = 0.055f))
                }
            )
            .clickable(
                interactionSource = source,
                indication = null,
                onClickLabel = if (isWatched) "Mark unwatched" else "Mark watched",
                onClick = onClick
            )
            .padding(horizontal = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(5.dp)
    ) {
        if (isWatched) {
            ThinCheckIcon(color = textColor, modifier = Modifier.size(14.dp))
        } else {
            ThinEyeIcon(color = textColor, modifier = Modifier.size(14.dp))
        }
        Text(
            text = if (isWatched) "Watched" else "Watch",
            color = textColor,
            fontSize = 9.sp,
            lineHeight = 10.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun PressableScale(
    onClick: () -> Unit,
    content: @Composable (Modifier) -> Unit
) {
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.985f else 1f,
        animationSpec = tween(durationMillis = 360, easing = SpringEase),
        label = "pressScale"
    )
    content(
        Modifier
            .scale(scale)
            .clickable(interactionSource = source, indication = null, onClick = onClick)
    )
}

@Composable
private fun ThinSearchIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        drawCircle(color = color, radius = size.minDimension * 0.32f, center = Offset(size.width * 0.43f, size.height * 0.43f), style = Stroke(width = 2.1f))
        drawLine(color = color, start = Offset(size.width * 0.65f, size.height * 0.65f), end = Offset(size.width * 0.9f, size.height * 0.9f), strokeWidth = 2.1f)
    }
}

@Composable
private fun ThinEyeIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        val stroke = 1.8f
        val eyePath = Path().apply {
            moveTo(size.width * 0.08f, size.height * 0.50f)
            cubicTo(size.width * 0.25f, size.height * 0.24f, size.width * 0.75f, size.height * 0.24f, size.width * 0.92f, size.height * 0.50f)
            cubicTo(size.width * 0.75f, size.height * 0.76f, size.width * 0.25f, size.height * 0.76f, size.width * 0.08f, size.height * 0.50f)
        }
        drawPath(path = eyePath, color = color, style = Stroke(width = stroke))
        drawCircle(
            color = color,
            radius = size.minDimension * 0.12f,
            center = Offset(size.width * 0.50f, size.height * 0.50f),
            style = Stroke(width = stroke)
        )
    }
}

@Composable
private fun ThinSlidersIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        val stroke = 2.0f
        drawLine(color = color, start = Offset(size.width * 0.16f, size.height * 0.28f), end = Offset(size.width * 0.84f, size.height * 0.28f), strokeWidth = stroke)
        drawLine(color = color, start = Offset(size.width * 0.16f, size.height * 0.52f), end = Offset(size.width * 0.84f, size.height * 0.52f), strokeWidth = stroke)
        drawLine(color = color, start = Offset(size.width * 0.16f, size.height * 0.76f), end = Offset(size.width * 0.84f, size.height * 0.76f), strokeWidth = stroke)
        drawCircle(color = color, radius = size.minDimension * 0.075f, center = Offset(size.width * 0.34f, size.height * 0.28f), style = Stroke(width = stroke))
        drawCircle(color = color, radius = size.minDimension * 0.075f, center = Offset(size.width * 0.64f, size.height * 0.52f), style = Stroke(width = stroke))
        drawCircle(color = color, radius = size.minDimension * 0.075f, center = Offset(size.width * 0.43f, size.height * 0.76f), style = Stroke(width = stroke))
    }
}

@Composable
private fun ThinCheckIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        drawLine(color = color, start = Offset(size.width * 0.18f, size.height * 0.54f), end = Offset(size.width * 0.42f, size.height * 0.76f), strokeWidth = 2.4f)
        drawLine(color = color, start = Offset(size.width * 0.42f, size.height * 0.76f), end = Offset(size.width * 0.84f, size.height * 0.24f), strokeWidth = 2.4f)
    }
}

@Composable
private fun ThinCloseIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        drawLine(color = color, start = Offset(size.width * 0.22f, size.height * 0.22f), end = Offset(size.width * 0.78f, size.height * 0.78f), strokeWidth = 2.1f)
        drawLine(color = color, start = Offset(size.width * 0.78f, size.height * 0.22f), end = Offset(size.width * 0.22f, size.height * 0.78f), strokeWidth = 2.1f)
    }
}
