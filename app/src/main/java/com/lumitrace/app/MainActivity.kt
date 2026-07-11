package com.lumitrace.app

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.PageSize
import androidx.compose.foundation.pager.rememberPagerState
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
import androidx.compose.runtime.mutableIntStateOf
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil.compose.AsyncImage
import com.lumitrace.app.data.Movie
import com.lumitrace.app.data.FeedbackKind
import com.lumitrace.app.data.ViewingContext
import com.lumitrace.app.data.ViewingProfile
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
import com.lumitrace.app.ui.TraktUiState
import com.lumitrace.app.ui.TonightUiState
import com.lumitrace.app.recommendation.RecommendationTrace
import java.util.Locale
import kotlinx.coroutines.delay
import kotlin.math.absoluteValue

private val HeavyEase = CubicBezierEasing(0.22f, 1f, 0.36f, 1f)
private val SpringEase = CubicBezierEasing(0.32f, 0.72f, 0f, 1f)
private val ShellShape = RoundedCornerShape(34.dp)
private val CoreShape = RoundedCornerShape(28.dp)
private val CardShape = RoundedCornerShape(26.dp)

private enum class AppDestination {
    Home,
    Settings,
    Recommendation,
    TasteInput,
    Library,
    Tonight,
    Insights
}

class MainActivity : ComponentActivity() {
    private val viewModel: MovieViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AppTheme {
                Surface(color = Ink, modifier = Modifier.fillMaxSize()) {
                    MovieScreen(viewModel, openTonight = intent?.action == MovieWidgetProvider.ACTION_OPEN_TONIGHT)
                }
            }
        }
    }
}

@Composable
fun MovieScreen(viewModel: MovieViewModel, openTonight: Boolean = false) {
    val uiState by viewModel.uiState.collectAsState()
    val categories by viewModel.categories.collectAsState()
    val homeMessage by viewModel.homeMessage.collectAsState()
    val homeLoading by viewModel.homeLoading.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val tmdbApiKey by viewModel.tmdbApiKey.collectAsState()
    val journalEntries by viewModel.journalEntries.collectAsState()
    val watchlistMovies by viewModel.watchlistMovies.collectAsState()
    val localTasteState by viewModel.localTasteState.collectAsState()
    val tonightUiState by viewModel.tonightUiState.collectAsState()
    val traktClientId by viewModel.traktClientId.collectAsState()
    val traktClientSecret by viewModel.traktClientSecret.collectAsState()
    val traktUiState by viewModel.traktUiState.collectAsState()
    var selectedMovie by remember { mutableStateOf<Movie?>(null) }
    val watchedMovies by viewModel.watchedMovies.collectAsState()
    var apiKeyInput by remember { mutableStateOf(tmdbApiKey) }
    var traktClientIdInput by remember { mutableStateOf(traktClientId) }
    var traktClientSecretInput by remember { mutableStateOf(traktClientSecret) }
    var destination by remember(openTonight) { mutableStateOf(if (openTonight) AppDestination.Tonight else AppDestination.Home) }
    var heroIndex by remember { mutableIntStateOf(0) }
    // Handle back button press
    BackHandler(destination != AppDestination.Home) {
        destination = AppDestination.Home
    }

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

    LaunchedEffect(traktClientId, traktClientSecret) {
        if (traktClientIdInput != traktClientId) traktClientIdInput = traktClientId
        if (traktClientSecretInput != traktClientSecret) traktClientSecretInput = traktClientSecret
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
                            traktClientId = traktClientIdInput,
                            traktClientSecret = traktClientSecretInput,
                            traktUiState = traktUiState,
                            onApiKeyChange = { apiKeyInput = it },
                            onTraktClientIdChange = { traktClientIdInput = it },
                            onTraktClientSecretChange = { traktClientSecretInput = it },
                            onSave = {
                                viewModel.saveTmdbApiKey(apiKeyInput)
                            },
                            onClear = {
                                apiKeyInput = ""
                                viewModel.clearTmdbApiKey()
                            },
                            onConnectTrakt = {
                                viewModel.connectTrakt(traktClientIdInput, traktClientSecretInput)
                            },
                            onImportTrakt = viewModel::importFromTrakt,
                            onUploadTrakt = viewModel::uploadToTrakt,
                            onDisconnectTrakt = { viewModel.disconnectTrakt(clearCredentials = false) },
                            onClearTrakt = {
                                traktClientIdInput = ""
                                traktClientSecretInput = ""
                                viewModel.disconnectTrakt(clearCredentials = true)
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
                            onRun = { viewModel.searchSemanticMovies(watchedMovies.toList()) },
                            onOpenTasteInput = { destination = AppDestination.TasteInput },
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
                                    seedCount = watchedMovies.size
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
                                    StatusPanel(message = "Local recommendation is unavailable: ${state.message}")
                                    if (watchedMovies.isNotEmpty()) {
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
                                Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                                    SectionHeader(
                                        eyebrow = "On-device matches",
                                        title = state.aiTitle ?: "Recommended for you",
                                        copy = state.aiSummary ?: "Scroll down for more locally ranked matches."
                                    )
                                }
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
                            MovieGridRow(
                                row = row,
                                watchedMovieIds = watchedMovieIds,
                                onToggleWatched = onToggleWatched,
                                onSelect = { selectedMovie = it },
                                posterImageSize = "w342"
                            )
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
            } else if (destination == AppDestination.Library) {
                item {
                    Reveal(index = 1) {
                        LocalLibraryScreen(
                            watchlist = watchlistMovies,
                            watched = watchedMovies.toList(),
                            onMarkWatched = viewModel::toggleWatched,
                            onRemove = { movie -> viewModel.removeFromLibrary(movie.id) },
                            onBackHome = { destination = AppDestination.Home }
                        )
                    }
                }
            } else if (destination == AppDestination.Insights) {
                item {
                    Reveal(index = 1) {
                        InsightsScreen(
                            profileName = localTasteState.profiles.first { it.id == localTasteState.activeProfileId }.name,
                            profiles = localTasteState.profiles,
                            activeProfileId = localTasteState.activeProfileId,
                            watchedCount = watchedMovies.size,
                            queuedCount = watchlistMovies.size,
                            eventCount = localTasteState.profiles.first { it.id == localTasteState.activeProfileId }.events.size,
                            onCreateProfile = viewModel::createViewingProfile,
                            onRenameProfile = viewModel::renameViewingProfile,
                            onSelectProfile = viewModel::selectViewingProfile,
                            onDeleteProfile = viewModel::deleteViewingProfile,
                            onExportBackup = viewModel::exportLocalBackup,
                            onImportBackup = viewModel::importLocalBackup,
                            onBackHome = { destination = AppDestination.Home }
                        )
                    }
                }
            } else if (destination == AppDestination.Tonight) {
                item {
                    Reveal(index = 1) {
                        TonightScreen(
                            state = tonightUiState,
                            watchedMovieIds = watchedMovieIds,
                            onBuild = viewModel::buildTonight,
                            onMarkWatched = viewModel::toggleWatched,
                            onSelect = { selectedMovie = it }
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
                item {
                    Reveal(index = 2) {
                        LocalToolsPanel(
                            queuedCount = watchlistMovies.size,
                            profileName = localTasteState.profiles.first { it.id == localTasteState.activeProfileId }.name,
                            onOpenLibrary = { destination = AppDestination.Library },
                            onOpenTonight = { destination = AppDestination.Tonight },
                            onOpenInsights = { destination = AppDestination.Insights }
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
                                    eyebrow = "TMDB search",
                                    title = "Results for your movie title",
                                    copy = "Live movie data loaded directly from TMDB with your own key."
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
            recommendationTrace = (uiState as? UiState.Success)?.recommendationTraces?.get(movie.id),
            onWatchedClick = { onToggleWatched(movie) },
            onQueueClick = { viewModel.addToWatchlist(movie) },
            onFeedback = { kind -> viewModel.recordRecommendationFeedback(movie, kind) },
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
    traktClientId: String,
    traktClientSecret: String,
    traktUiState: TraktUiState,
    onApiKeyChange: (String) -> Unit,
    onTraktClientIdChange: (String) -> Unit,
    onTraktClientSecretChange: (String) -> Unit,
    onSave: () -> Unit,
    onClear: () -> Unit,
    onConnectTrakt: () -> Unit,
    onImportTrakt: () -> Unit,
    onUploadTrakt: () -> Unit,
    onDisconnectTrakt: () -> Unit,
    onClearTrakt: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        SectionHeader(
            eyebrow = "Settings",
            title = "Your TMDB connection",
            copy = "One key unlocks browsing and posters. Your taste profile and recommendation calculations stay on this phone."
        )
        ApiKeyPanel(
            value = apiKey,
            onValueChange = onApiKeyChange,
            onSave = onSave,
            hasSavedKey = savedApiKey.isNotBlank()
        )
        TraktPanel(
            clientId = traktClientId,
            clientSecret = traktClientSecret,
            state = traktUiState,
            onClientIdChange = onTraktClientIdChange,
            onClientSecretChange = onTraktClientSecretChange,
            onConnect = onConnectTrakt,
            onImport = onImportTrakt,
            onUpload = onUploadTrakt,
            onDisconnect = onDisconnectTrakt,
            onClear = onClearTrakt
        )
        DoubleBezel {
            Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Eyebrow("Local privacy")
                Text("No LumiTrace backend", color = LumiText, style = MaterialTheme.typography.headlineSmall)
                Text(
                    "Watched movies, 1-10 ratings, and journal notes stay in app-private storage, encrypted when Android Keystore is available. Trakt receives them only when you explicitly tap Import or Upload. Recommendation ranking never leaves this phone.",
                    color = LumiTextSoft,
                    style = MaterialTheme.typography.bodyLarge
                )
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                    LumiPillButton(
                        label = "Save TMDB key",
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
        DoubleBezel {
            Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Eyebrow("Data credits")
                Row(
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Image(
                        painter = painterResource(R.drawable.tmdb_logo),
                        contentDescription = "TMDB",
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.width(66.dp)
                    )
                    Text(
                        "This product uses the TMDB API but is not endorsed or certified by TMDB.",
                        color = LumiTextSoft,
                        style = MaterialTheme.typography.bodyLarge,
                        modifier = Modifier.weight(1f)
                    )
                }
                Text(
                    "The bundled semantic starter index is derived from MovieLens Latest Small. Its data notice is packaged with the app.",
                    color = Muted,
                    fontSize = 12.sp,
                    lineHeight = 18.sp
                )
                Text(
                    "Optional account synchronization is powered by Trakt and runs only when you explicitly import or upload.",
                    color = Muted,
                    fontSize = 12.sp,
                    lineHeight = 18.sp
                )
            }
        }
    }
}

@Composable
private fun TraktPanel(
    clientId: String,
    clientSecret: String,
    state: TraktUiState,
    onClientIdChange: (String) -> Unit,
    onClientSecretChange: (String) -> Unit,
    onConnect: () -> Unit,
    onImport: () -> Unit,
    onUpload: () -> Unit,
    onDisconnect: () -> Unit,
    onClear: () -> Unit
) {
    val uriHandler = LocalUriHandler.current

    DoubleBezel {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Eyebrow("Optional sync")
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Connect Trakt", color = LumiText, fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
                }
                StatusDot(active = state.isConnected)
            }
            Text(
                "Create your own Trakt API application and use redirect URI urn:ietf:wg:oauth:2.0:oob. The Client Secret and OAuth tokens stay in encrypted app-private storage; LumiTrace ships no shared Trakt secret.",
                color = Muted,
                fontSize = 12.sp,
                lineHeight = 18.sp
            )
            LumiTextField(
                value = clientId,
                onValueChange = onClientIdChange,
                placeholder = "Trakt Client ID",
                trailing = { StatusDot(active = clientId.isNotBlank()) }
            )
            LumiTextField(
                value = clientSecret,
                onValueChange = onClientSecretChange,
                placeholder = "Trakt Client Secret",
                secret = true,
                trailing = { StatusDot(active = clientSecret.isNotBlank()) }
            )

            if (state.isBusy) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), color = Teal, strokeWidth = 2.dp)
                    Text(state.message, color = LumiTextSoft, fontSize = 12.sp, lineHeight = 17.sp, modifier = Modifier.weight(1f))
                }
            } else {
                Text(state.message, color = LumiTextSoft, fontSize = 12.sp, lineHeight = 18.sp)
            }

            if (state.userCode.isNotBlank() && state.activationUrl.isNotBlank()) {
                DoubleBezel(radius = 24.dp, innerRadius = 18.dp, outerPadding = 4.dp) {
                    Column(modifier = Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Eyebrow("Activation code")
                        Text(
                            state.userCode,
                            color = Teal2,
                            fontSize = 26.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.ExtraBold
                        )
                        LumiPillButton(
                            label = "Open Trakt activation",
                            onClick = { runCatching { uriHandler.openUri(state.activationUrl) } }
                        )
                    }
                }
            }

            if (state.isConnected) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                    LumiPillButton(
                        label = "Import",
                        enabled = !state.isBusy,
                        onClick = onImport,
                        modifier = Modifier.weight(1f)
                    )
                    LumiPillButton(
                        label = "Upload",
                        enabled = !state.isBusy,
                        onClick = onUpload,
                        modifier = Modifier.weight(1f)
                    )
                }
                Text(
                    "Import merges Trakt watched movies and fills missing ratings. Upload adds only new watched movies and changed ratings; Trakt ratings are whole numbers, while local decimal scores are preserved.",
                    color = Muted,
                    fontSize = 11.sp,
                    lineHeight = 17.sp
                )
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                    LumiPillButton(
                        label = "Disconnect",
                        secondary = true,
                        onClick = onDisconnect,
                        modifier = Modifier.weight(1f)
                    )
                    LumiPillButton(
                        label = "Clear credentials",
                        secondary = true,
                        onClick = onClear,
                        modifier = Modifier.weight(1.25f)
                    )
                }
            } else if (!state.isBusy) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                    LumiPillButton(
                        label = "Connect Trakt",
                        enabled = clientId.isNotBlank() && clientSecret.isNotBlank(),
                        onClick = onConnect,
                        modifier = Modifier.weight(1.2f)
                    )
                    if (state.credentialsSaved) {
                        LumiPillButton(
                            label = "Clear",
                            secondary = true,
                            onClick = onClear,
                            modifier = Modifier.weight(0.8f)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun RecommendationScreen(
    seedMovies: List<Movie>,
    onRun: () -> Unit,
    onOpenTasteInput: () -> Unit,
    onBackHome: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        SectionHeader(
            eyebrow = "Recommendation",
            title = "Your private taste engine",
            copy = "The bundled semantic index ranks movies on this phone. Only poster and movie-detail requests go directly to TMDB."
        )

        RecommendationControlPanel(
            seedCount = seedMovies.size,
            onOpenTasteInput = onOpenTasteInput,
            onRun = onRun,
            onBackHome = onBackHome
        )
    }
}

@Composable
private fun RecommendationControlPanel(
    seedCount: Int,
    onOpenTasteInput: () -> Unit,
    onRun: () -> Unit,
    onBackHome: () -> Unit
) {
    val canRun = seedCount > 0
    DoubleBezel {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Eyebrow("On-device controls")
            Text(
                text = if (seedCount == 0) "Recommendation room" else "$seedCount watched movies queued",
                color = LumiText,
                style = MaterialTheme.typography.headlineSmall
            )
            Text(
                text = if (canRun) {
                    "Your watched movies and 1-10 ratings are ready. Ranking runs locally from the bundled semantic index."
                } else {
                    "Open Taste input or browse Home and mark at least one movie as watched. Ratings make the result more precise."
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
private fun RecommendationIdlePanel(seedCount: Int) {
    val canRun = seedCount > 0
    DoubleBezel(radius = 26.dp, innerRadius = 20.dp) {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Eyebrow("Ready")
            Text(
                text = if (canRun) "Local recommendation is ready" else "Waiting for your first taste signal",
                color = LumiText,
                style = MaterialTheme.typography.headlineSmall
            )
            Text(
                text = if (canRun) {
                    "Run recommendation now. Computation stays on this device and uses no LumiTrace server."
                } else {
                    "Mark a movie as watched, then add a 1-10 rating for a stronger result."
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
private fun LocalToolsPanel(
    queuedCount: Int,
    profileName: String,
    onOpenLibrary: () -> Unit,
    onOpenTonight: () -> Unit,
    onOpenInsights: () -> Unit
) {
    DoubleBezel {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Eyebrow("Local taste tools")
            Text("Choose with intent.", color = LumiText, fontSize = 22.sp, fontWeight = FontWeight.Bold)
            Text("$profileName is active. Everything below stays on this phone.", color = LumiTextSoft, fontSize = 13.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                LumiPillButton(label = "Queue $queuedCount", onClick = onOpenLibrary, modifier = Modifier.weight(1f))
                LumiPillButton(label = "Tonight", onClick = onOpenTonight, modifier = Modifier.weight(1f))
            }
            LumiPillButton(label = "Taste insights", onClick = onOpenInsights, modifier = Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun LocalLibraryScreen(
    watchlist: List<Movie>,
    watched: List<Movie>,
    onMarkWatched: (Movie) -> Unit,
    onRemove: (Movie) -> Unit,
    onBackHome: () -> Unit
) {
    DoubleBezel {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Eyebrow("Your local library")
            Text("Watch Queue", color = LumiText, fontSize = 28.sp, fontWeight = FontWeight.Bold)
            Text("Queued films do not change your recommendation taste until you mark them watched.", color = LumiTextSoft, fontSize = 13.sp)
            if (watchlist.isEmpty()) {
                StatusPanel("No queued films yet. Use the Queue action from a movie detail card.")
            } else {
                watchlist.forEach { movie ->
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(movie.title, color = LumiText, fontWeight = FontWeight.SemiBold)
                            Text(movie.releaseDate.take(4), color = Dim, fontSize = 12.sp)
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            LumiPillButton(label = "Watched", onClick = { onMarkWatched(movie) })
                            LumiPillButton(label = "Remove", onClick = { onRemove(movie) })
                        }
                    }
                }
            }
            Text("${watched.size} watched films are currently allowed to shape on-device recommendations.", color = LumiTextSoft, fontSize = 12.sp)
            LumiPillButton(label = "Back to home", onClick = onBackHome, modifier = Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun InsightsScreen(
    profileName: String,
    profiles: List<ViewingProfile>,
    activeProfileId: String,
    watchedCount: Int,
    queuedCount: Int,
    eventCount: Int,
    onCreateProfile: (String) -> Unit,
    onRenameProfile: (String, String) -> Unit,
    onSelectProfile: (String) -> Unit,
    onDeleteProfile: (String) -> Unit,
    onExportBackup: () -> String,
    onImportBackup: (String) -> Result<Unit>,
    onBackHome: () -> Unit
) {
    var newProfileName by remember { mutableStateOf("") }
    var renameValue by remember(profileName) { mutableStateOf(profileName) }
    val context = LocalContext.current
    val exportBackup = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        runCatching {
            context.contentResolver.openOutputStream(uri)?.bufferedWriter()?.use { it.write(onExportBackup()) }
                ?: error("Could not write the selected file.")
        }.onSuccess {
            Toast.makeText(context, "Backup saved without API keys or account tokens.", Toast.LENGTH_SHORT).show()
        }.onFailure { error ->
            Toast.makeText(context, error.message ?: "Backup could not be saved.", Toast.LENGTH_SHORT).show()
        }
    }
    val importBackup = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        runCatching {
            context.contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() }
                ?: error("Could not read the selected file.")
        }.fold(
            onSuccess = { json ->
                onImportBackup(json).onSuccess {
                    Toast.makeText(context, "Backup restored on this device.", Toast.LENGTH_SHORT).show()
                }.onFailure { error ->
                    Toast.makeText(context, error.message ?: "This backup is not valid.", Toast.LENGTH_SHORT).show()
                }
            },
            onFailure = { error -> Toast.makeText(context, error.message ?: "Backup could not be opened.", Toast.LENGTH_SHORT).show() }
        )
    }
    DoubleBezel {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Eyebrow("Private taste insights")
            Text(profileName, color = LumiText, fontSize = 28.sp, fontWeight = FontWeight.Bold)
            Text("Recorded activity only — LumiTrace never invents watch history.", color = LumiTextSoft, fontSize = 13.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                MetricCard(watchedCount.toString(), "watched", Modifier.weight(1f))
                MetricCard(queuedCount.toString(), "queued", Modifier.weight(1f))
                MetricCard(eventCount.toString(), "events", Modifier.weight(1f))
            }
            Eyebrow("Viewing Profiles")
            profiles.forEach { profile ->
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text(if (profile.id == activeProfileId) "● ${profile.name}" else profile.name, color = LumiTextSoft, fontSize = 13.sp)
                    SmallTextButton(if (profile.id == activeProfileId) "Active" else "Switch") { onSelectProfile(profile.id) }
                }
            }
            BasicTextField(
                value = newProfileName,
                onValueChange = { newProfileName = it.take(40) },
                textStyle = TextStyle(color = LumiText, fontSize = 13.sp),
                cursorBrush = SolidColor(Teal),
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Color.White.copy(alpha = 0.06f)).padding(12.dp),
                decorationBox = { inner -> if (newProfileName.isBlank()) Text("New profile name", color = Dim, fontSize = 13.sp); inner() }
            )
            LumiPillButton(label = "Create profile", secondary = true, enabled = newProfileName.isNotBlank(), onClick = { onCreateProfile(newProfileName); newProfileName = "" }, modifier = Modifier.fillMaxWidth())
            BasicTextField(
                value = renameValue,
                onValueChange = { renameValue = it.take(40) },
                textStyle = TextStyle(color = LumiText, fontSize = 13.sp),
                cursorBrush = SolidColor(Teal),
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Color.White.copy(alpha = 0.06f)).padding(12.dp),
                decorationBox = { inner -> if (renameValue.isBlank()) Text("Rename active profile", color = Dim, fontSize = 13.sp); inner() }
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                LumiPillButton(label = "Rename", secondary = true, enabled = renameValue.isNotBlank(), onClick = { onRenameProfile(activeProfileId, renameValue) }, modifier = Modifier.weight(1f))
                LumiPillButton(label = "Delete", secondary = true, enabled = profiles.size > 1, onClick = { onDeleteProfile(activeProfileId) }, modifier = Modifier.weight(1f))
            }
            Eyebrow("Portable backup")
            Text("Profiles, queue, ratings and feedback only. Your TMDB key and optional Trakt credentials stay on this phone.", color = LumiTextSoft, fontSize = 12.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                LumiPillButton(label = "Export", secondary = true, onClick = { exportBackup.launch("lumitrace-backup.json") }, modifier = Modifier.weight(1f))
                LumiPillButton(label = "Import", secondary = true, onClick = { importBackup.launch(arrayOf("application/json", "text/plain")) }, modifier = Modifier.weight(1f))
            }
            LumiPillButton(label = "Back to home", onClick = onBackHome, modifier = Modifier.fillMaxWidth())
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TonightScreen(
    state: TonightUiState,
    watchedMovieIds: Set<Int>,
    onBuild: (ViewingContext) -> Unit,
    onMarkWatched: (Movie) -> Unit,
    onSelect: (Movie) -> Unit
) {
    var maxRuntime by remember { mutableStateOf("") }
    var minYear by remember { mutableStateOf("") }
    var mood by remember { mutableStateOf<String?>(null) }
    var pace by remember { mutableStateOf<String?>(null) }
    var companion by remember { mutableStateOf<String?>(null) }
    var language by remember { mutableStateOf<String?>(null) }
    var genreIds by remember { mutableStateOf(setOf<Int>()) }

    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        SectionHeader(
            eyebrow = "Tonight",
            title = "Choose the feeling, not the feed.",
            copy = "Set only what matters. LumiTrace combines those choices with your local taste profile."
        )

        DoubleBezel(
            modifier = Modifier.testTag("tonight_filters"),
            radius = 30.dp,
            innerRadius = 24.dp
        ) {
            Column(
                modifier = Modifier.padding(18.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    TonightNumberField(
                        label = "Runtime",
                        hint = "e.g. 120 min",
                        value = maxRuntime,
                        maxLength = 3,
                        onValueChange = { maxRuntime = it },
                        modifier = Modifier.weight(1f)
                    )
                    TonightNumberField(
                        label = "From year",
                        hint = "e.g. 2010",
                        value = minYear,
                        maxLength = 4,
                        onValueChange = { minYear = it },
                        modifier = Modifier.weight(1f)
                    )
                }

                TonightChoiceGroup(
                    label = "Mood",
                    options = listOf("warm" to "Warm", "tense" to "Tense", "light" to "Light", "cerebral" to "Cerebral"),
                    selected = mood,
                    onSelect = { mood = it }
                )
                TonightChoiceGroup(
                    label = "Language",
                    options = listOf("en" to "English", "ja" to "Japanese", "ko" to "Korean", "zh" to "Chinese"),
                    selected = language,
                    onSelect = { language = it }
                )
                TonightChoiceGroup(
                    label = "Pace",
                    options = listOf("fast" to "Fast", "slow" to "Slow"),
                    selected = pace,
                    onSelect = { pace = it }
                )
                TonightChoiceGroup(
                    label = "Company",
                    options = listOf("solo" to "Solo", "date" to "Date", "family" to "Family", "friends" to "Friends"),
                    selected = companion,
                    onSelect = { companion = it }
                )

                Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    TonightFilterLabel("Genre", "Choose more than one")
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        listOf(28 to "Action", 35 to "Comedy", 18 to "Drama", 878 to "Sci-fi").forEach { (id, label) ->
                            TonightChoiceChip(
                                label = label,
                                selected = id in genreIds,
                                onClick = {
                                    genreIds = if (id in genreIds) genreIds - id else genreIds + id
                                }
                            )
                        }
                    }
                }

                LumiPillButton(
                    label = if (state == TonightUiState.Loading) "Building shortlist" else "Draw three local picks",
                    enabled = state != TonightUiState.Loading,
                    onClick = {
                        onBuild(
                            ViewingContext(
                                maxRuntimeMinutes = maxRuntime.toIntOrNull(),
                                minYear = minYear.toIntOrNull(),
                                language = language,
                                genreIds = genreIds,
                                mood = mood,
                                pace = pace,
                                companion = companion
                            )
                        )
                    },
                    modifier = Modifier.fillMaxWidth()
                )

                when (state) {
                    TonightUiState.Idle -> Text(
                        "No filters are required. Draw whenever your taste profile is ready.",
                        color = Dim,
                        fontSize = 11.sp,
                        lineHeight = 16.sp
                    )
                    TonightUiState.Loading -> LoadingPanel()
                    is TonightUiState.Error -> StatusPanel(state.message)
                    is TonightUiState.Success -> Unit
                }
            }
        }

        if (state is TonightUiState.Success) {
            TonightPickDeck(
                movies = state.movies,
                watchedMovieIds = watchedMovieIds,
                onMarkWatched = onMarkWatched,
                onSelect = onSelect
            )
        }
    }
}

@Composable
private fun TonightNumberField(
    label: String,
    hint: String,
    value: String,
    maxLength: Int,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(7.dp)) {
        Text(label, color = Teal2, fontSize = 9.sp, fontWeight = FontWeight.ExtraBold)
        BasicTextField(
            value = value,
            onValueChange = { onValueChange(it.filter(Char::isDigit).take(maxLength)) },
            textStyle = TextStyle(color = LumiText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold),
            cursorBrush = SolidColor(Teal),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number, imeAction = ImeAction.Next),
            singleLine = true,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
                .clip(RoundedCornerShape(14.dp))
                .background(Color.White.copy(alpha = 0.055f))
                .padding(horizontal = 13.dp, vertical = 14.dp),
            decorationBox = { inner ->
                if (value.isBlank()) Text(hint, color = Dim, fontSize = 11.sp)
                inner()
            }
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TonightChoiceGroup(
    label: String,
    options: List<Pair<String, String>>,
    selected: String?,
    onSelect: (String?) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
        TonightFilterLabel(label, "Choose one")
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            options.forEach { (value, display) ->
                TonightChoiceChip(
                    label = display,
                    selected = selected == value,
                    onClick = { onSelect(if (selected == value) null else value) }
                )
            }
        }
    }
}

@Composable
private fun TonightFilterLabel(label: String, helper: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, color = LumiText, fontSize = 12.sp, fontWeight = FontWeight.ExtraBold)
        Text(helper, color = Dim, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
    }
}

@Composable
private fun TonightChoiceChip(label: String, selected: Boolean, onClick: () -> Unit) {
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.96f else if (selected) 1.02f else 1f,
        animationSpec = tween(300, easing = SpringEase),
        label = "tonightChoiceScale"
    )
    Row(
        modifier = Modifier
            .scale(scale)
            .clip(RoundedCornerShape(999.dp))
            .background(if (selected) Teal.copy(alpha = 0.18f) else Color.White.copy(alpha = 0.055f))
            .clickable(interactionSource = source, indication = null, onClick = onClick)
            .padding(start = 13.dp, top = 9.dp, end = if (selected) 10.dp else 13.dp, bottom = 9.dp),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, color = if (selected) Teal2 else LumiTextSoft, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        if (selected) {
            Box(
                modifier = Modifier
                    .size(19.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(Teal.copy(alpha = 0.22f)),
                contentAlignment = Alignment.Center
            ) {
                ThinCheckIcon(color = Teal2, modifier = Modifier.size(11.dp))
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun TonightPickDeck(
    movies: List<Movie>,
    watchedMovieIds: Set<Int>,
    onMarkWatched: (Movie) -> Unit,
    onSelect: (Movie) -> Unit
) {
    val pagerState = rememberPagerState(pageCount = { movies.size })
    val movieKey = movies.joinToString("-") { it.id.toString() }
    LaunchedEffect(movieKey) {
        if (movies.isNotEmpty()) pagerState.scrollToPage(0)
    }

    Column(
        modifier = Modifier.testTag("tonight_pick_deck"),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Bottom
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Eyebrow("Your draw")
                Text("Three ways tonight could go.", color = LumiText, fontSize = 21.sp, fontWeight = FontWeight.ExtraBold)
            }
            Text("Swipe", color = Teal2, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
        }

        HorizontalPager(
            state = pagerState,
            pageSize = PageSize.Fixed(306.dp),
            contentPadding = PaddingValues(horizontal = 12.dp),
            pageSpacing = 12.dp,
            beyondViewportPageCount = 1,
            modifier = Modifier.fillMaxWidth().height(492.dp)
        ) { page ->
            val signedOffset = (pagerState.currentPage - page) + pagerState.currentPageOffsetFraction
            val distance = signedOffset.absoluteValue.coerceIn(0f, 1f)
            TonightPickCard(
                movie = movies[page],
                index = page,
                total = movies.size,
                isWatched = movies[page].id in watchedMovieIds,
                onMarkWatched = { onMarkWatched(movies[page]) },
                onSelect = { onSelect(movies[page]) },
                modifier = Modifier.graphicsLayer {
                    scaleX = 1f - distance * 0.065f
                    scaleY = 1f - distance * 0.065f
                    alpha = 1f - distance * 0.24f
                    rotationZ = signedOffset * -2.2f
                    translationY = distance * 10.dp.toPx()
                }
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            movies.indices.forEach { index ->
                val selected = pagerState.currentPage == index
                Box(
                    modifier = Modifier
                        .padding(horizontal = 4.dp)
                        .size(8.dp)
                        .scale(if (selected) 1.25f else 0.8f)
                        .alpha(if (selected) 1f else 0.35f)
                        .clip(RoundedCornerShape(4.dp))
                        .background(if (selected) Teal2 else LumiTextSoft)
                )
            }
        }
    }
}

@Composable
private fun TonightPickCard(
    movie: Movie,
    index: Int,
    total: Int,
    isWatched: Boolean,
    onMarkWatched: () -> Unit,
    onSelect: () -> Unit,
    modifier: Modifier = Modifier
) {
    DoubleBezel(modifier = modifier, radius = 30.dp, innerRadius = 24.dp, outerPadding = 5.dp) {
        Column(modifier = Modifier.fillMaxSize()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(326.dp)
                    .clickable(onClickLabel = "Open ${movie.title} details", onClick = onSelect)
            ) {
                MoviePoster(movie = movie, imageSize = "w500", modifier = Modifier.fillMaxSize())
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(
                            Brush.verticalGradient(
                                listOf(Color.Transparent, Color.Transparent, PanelStrong.copy(alpha = 0.96f))
                            )
                        )
                )
                Row(
                    modifier = Modifier.fillMaxWidth().padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(999.dp))
                            .background(PanelStrong.copy(alpha = 0.88f))
                            .padding(horizontal = 11.dp, vertical = 7.dp)
                    ) {
                        Text("PICK ${index + 1} / $total", color = Teal2, fontSize = 9.sp, fontWeight = FontWeight.ExtraBold)
                    }
                    RatingPill(movie.voteAverage)
                }
                Column(
                    modifier = Modifier.align(Alignment.BottomStart).padding(start = 16.dp, end = 16.dp, bottom = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Text(
                        movie.title,
                        color = LumiText,
                        fontSize = 23.sp,
                        lineHeight = 25.sp,
                        fontWeight = FontWeight.ExtraBold,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        movie.releaseDate.take(4).ifBlank { "Tap for details" },
                        color = LumiTextSoft,
                        fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace
                    )
                }
            }

            Column(
                modifier = Modifier.padding(start = 16.dp, top = 10.dp, end = 16.dp, bottom = 14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    movie.reason?.takeIf { it.isNotBlank() } ?: movie.overview.ifBlank { "A local taste match for tonight." },
                    color = LumiTextSoft,
                    fontSize = 11.sp,
                    lineHeight = 16.sp,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                LumiPillButton(
                    label = watchedActionLabel(isWatched),
                    secondary = isWatched,
                    onClick = onMarkWatched,
                    modifier = Modifier.fillMaxWidth()
                )
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
                MetricCard("1k", "starter index", Modifier.weight(1f))
                MetricCard("local", "taste engine", Modifier.weight(1f))
                MetricCard("private", "your data", Modifier.weight(1f))
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
                "Your key is encrypted in app-private storage and used only for direct TMDB requests. Watched movies and ratings never leave this device.",
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
private fun SearchPanel(
    query: String,
    onQueryChange: (String) -> Unit,
    onSearch: () -> Unit,
    onClear: () -> Unit
) {
    DoubleBezel {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Eyebrow("Find a movie")
                Spacer(modifier = Modifier.weight(1f))
                Text("TMDB direct", color = Teal2, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
            }
            LumiTextField(
                value = query,
                onValueChange = onQueryChange,
                placeholder = "Search by movie title...",
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
    onSelect: (Movie) -> Unit,
    posterImageSize: String = "w342"
) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
        row.forEach { movie ->
            Box(modifier = Modifier.weight(1f)) {
                MovieCard(
                    movie = movie,
                    isWatched = movie.id in watchedMovieIds,
                    onToggleWatched = { onToggleWatched(movie) },
                    onClick = { onSelect(movie) },
                    posterImageSize = posterImageSize
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
    onClick: () -> Unit,
    posterImageSize: String = "w342"
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
                        MoviePoster(movie = movie, imageSize = posterImageSize, modifier = Modifier.fillMaxSize())
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
                    movie.reason?.takeIf { it.isNotBlank() }?.let { reason ->
                        Text(
                            text = reason,
                            color = LumiTextSoft,
                            fontSize = 11.sp,
                            lineHeight = 15.sp,
                            maxLines = 3,
                            overflow = TextOverflow.Ellipsis
                        )
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

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MovieDetailDialog(
    movie: Movie,
    isWatched: Boolean,
    journalEntry: MovieJournalEntry,
    recommendationTrace: RecommendationTrace?,
    onWatchedClick: () -> Unit,
    onQueueClick: () -> Unit,
    onFeedback: (FeedbackKind) -> Unit,
    onRatingChange: (Float) -> Unit,
    onNoteChange: (String) -> Unit,
    onDismiss: () -> Unit
) {
    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.72f))
                .padding(horizontal = 12.dp, vertical = 18.dp),
            contentAlignment = Alignment.Center
        ) {
            DoubleBezel(
                modifier = Modifier.fillMaxWidth().fillMaxHeight(0.96f),
                radius = 34.dp,
                innerRadius = 28.dp,
                outerPadding = 5.dp
            ) {
                Column(
                    modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(0.dp)
                ) {
                    MovieDetailHero(movie = movie, onDismiss = onDismiss)

                    Column(
                        modifier = Modifier.padding(start = 18.dp, top = 18.dp, end = 18.dp, bottom = 26.dp),
                        verticalArrangement = Arrangement.spacedBy(18.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            DetailWatchedButton(
                                isWatched = isWatched,
                                onClick = onWatchedClick,
                                modifier = Modifier.weight(1f)
                            )
                            LumiPillButton(
                                label = "Watch queue",
                                secondary = true,
                                onClick = onQueueClick,
                                modifier = Modifier.weight(0.92f).height(56.dp)
                            )
                        }

                        movie.reason?.takeIf { it.isNotBlank() }?.let { reason ->
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                Box(
                                    modifier = Modifier
                                        .width(3.dp)
                                        .height(58.dp)
                                        .clip(RoundedCornerShape(2.dp))
                                        .background(Teal)
                                )
                                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                    Eyebrow("Why this")
                                    Text(reason, color = LumiTextSoft, fontSize = 13.sp, lineHeight = 19.sp)
                                }
                            }
                        }

                        recommendationTrace?.let { trace ->
                            Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                                TonightFilterLabel("Local score trace", "Transparent ranking")
                                FlowRow(
                                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                                    verticalArrangement = Arrangement.spacedBy(7.dp)
                                ) {
                                    TraceMetric("Semantic", trace.semanticSimilarity)
                                    TraceMetric("Genre", trace.genreAffinity)
                                    TraceMetric("Quality", trace.qualityPrior)
                                    TraceMetric("Dislike", -trace.negativePreferencePenalty)
                                    TraceMetric("Variety", -trace.diversityAdjustment)
                                    TraceMetric("Final", trace.finalScore, emphasized = true)
                                }
                            }
                        }

                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Eyebrow("Story")
                            Text(
                                movie.overview.ifBlank { "No synopsis is available from TMDB." },
                                color = LumiTextSoft,
                                fontSize = 14.sp,
                                lineHeight = 21.sp
                            )
                        }

                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            TonightFilterLabel("Recommendation feedback", "Optional local signal")
                            FlowRow(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                SmallTextButton("More like this") { onFeedback(FeedbackKind.MORE_LIKE_THIS) }
                                SmallTextButton("Less like this") { onFeedback(FeedbackKind.LESS_LIKE_THIS) }
                                SmallTextButton("Not tonight") { onFeedback(FeedbackKind.NOT_TONIGHT) }
                                SmallTextButton("Already seen") { onFeedback(FeedbackKind.ALREADY_SEEN) }
                                SmallTextButton("Too long") { onFeedback(FeedbackKind.TOO_LONG) }
                                SmallTextButton("Unavailable") { onFeedback(FeedbackKind.UNAVAILABLE) }
                            }
                        }

                        MovieJournalPanel(
                            entry = journalEntry,
                            onRatingChange = onRatingChange,
                            onNoteChange = onNoteChange
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MovieDetailHero(movie: Movie, onDismiss: () -> Unit) {
    Box(modifier = Modifier.fillMaxWidth().height(300.dp)) {
        MoviePoster(movie = movie, imageSize = "w780", modifier = Modifier.fillMaxSize())
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        listOf(Color.Black.copy(alpha = 0.08f), Color.Transparent, PanelStrong.copy(alpha = 0.98f))
                    )
                )
        )
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Eyebrow("Movie detail")
            RoundIconButton(label = "Close", secondary = true, onClick = onDismiss) {
                ThinCloseIcon(color = LumiTextSoft, modifier = Modifier.size(16.dp))
            }
        }
        Column(
            modifier = Modifier.align(Alignment.BottomStart).padding(start = 18.dp, end = 18.dp, bottom = 17.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp)
        ) {
            Text(
                text = movie.title,
                color = LumiText,
                fontSize = 30.sp,
                lineHeight = 31.sp,
                fontWeight = FontWeight.ExtraBold,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                RatingPill(movie.voteAverage)
                movie.releaseDate.take(4).takeIf { it.isNotBlank() }?.let { year ->
                    Text(year, color = LumiTextSoft, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                }
                movie.originalLanguage.takeIf { it.isNotBlank() }?.let { language ->
                    Text(language.uppercase(Locale.US), color = Teal2, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun TraceMetric(label: String, value: Float, emphasized: Boolean = false) {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(if (emphasized) Teal.copy(alpha = 0.17f) else Color.White.copy(alpha = 0.05f))
            .padding(horizontal = 10.dp, vertical = 7.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, color = if (emphasized) Teal2 else LumiTextSoft, fontSize = 9.sp, fontWeight = FontWeight.Bold)
        Text(value.formatTrace(), color = LumiText, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
    }
}

private fun Float.formatTrace(): String = String.format(Locale.US, "%.2f", this)

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

internal fun watchedActionLabel(isWatched: Boolean): String = if (isWatched) "Watched" else "Mark watched"

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
            text = watchedActionLabel(isWatched),
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
            Text(String.format(Locale.US, "%.1f", score), color = LumiText, fontSize = 11.sp, fontWeight = FontWeight.Bold)
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
    enabled: Boolean = true,
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
            .alpha(if (enabled) 1f else 0.45f)
            .clip(RoundedCornerShape(999.dp))
            .then(
                if (secondary) {
                    Modifier.background(Color.White.copy(alpha = 0.055f))
                } else {
                    Modifier.background(Brush.linearGradient(listOf(Teal, Teal2)))
                }
            )
            .clickable(interactionSource = source, indication = null, enabled = enabled, onClick = onClick)
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
            .semantics { contentDescription = label }
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
