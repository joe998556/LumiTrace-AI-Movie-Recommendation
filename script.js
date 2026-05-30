/**
 * LumiTrace - Unified Frontend Logic
 * All API calls go through our own backend (no exposed API keys)
 */
const BACKEND_URL = "http://localhost:8080/api"; // Default for local dev (supports new Proxy APIs)
// const BACKEND_URL = "https://aqi123.games/api"; // Production URL

// ==========================================
// State
// ==========================================
let currentPage = 1;
let currentPlatformId = null;
let currentMode = 'trending';
let currentPlatformName = '所有趨勢';
let currentSearchQuery = '';
let isLoading = false;

// Platform ID mapping
const PLATFORM_MAP = {
    'all': { id: null, name: '所有趨勢', mode: 'trending' },
    'netflix': { id: 8, name: 'Netflix', mode: 'platform' },
    'disney': { id: 337, name: 'Disney+', mode: 'platform' },
    'prime': { id: 119, name: 'Prime Video', mode: 'platform' },
    'hbo': { id: 1899, name: 'Max', mode: 'platform' },
    'apple': { id: 350, name: 'Apple TV+', mode: 'platform' },
};

// Provider ID matching (for streaming links)
const PROVIDER_MATCH = {
    'netflix': [8], 'disney': [337], 'hbo': [1899, 384],
    'prime': [119, 9], 'apple': [350, 2], 'hulu': [15],
    'paramount': [531]
};

// ==========================================
// Initialization
// ==========================================
window.addEventListener('DOMContentLoaded', () => {
    // Prevent any accidental form submissions
    document.addEventListener('submit', (e) => e.preventDefault(), true);

    // Restore user session
    const savedUser = sessionStorage.getItem('currentUser');
    if (savedUser) {
        showUserSession(savedUser);
    }

    // Load initial movies
    fetchMoviesData(false);

    // Setup platform tabs
    setupPlatformTabs();

    // Setup AI Command Center
    setupCommandCenter();

    // Setup Chat Panel
    setupChatPanel();

    // Setup Auth
    setupAuth();

    // Setup Load More
    setupLoadMore();
});

// ==========================================
// Movie Data Fetching (via Backend Proxy)
// ==========================================
async function fetchMoviesData(isAppend = false) {
    if (isLoading) return;
    isLoading = true;

    const region = localStorage.getItem('user_region') || 'TW';
    let endpoint = '';

    if (currentMode === 'search') {
        endpoint = `tmdb/search/movie?query=${encodeURIComponent(currentSearchQuery)}&language=zh-TW&page=${currentPage}`;
    } else if (currentMode === 'platform') {
        endpoint = `tmdb/discover/movie?watch_region=${region}&with_watch_providers=${currentPlatformId}&language=zh-TW&sort_by=popularity.desc&page=${currentPage}`;
    } else {
        endpoint = `tmdb/trending/movie/week?language=zh-TW&page=${currentPage}`;
    }

    try {
        const res = await fetch(`${BACKEND_URL}/${endpoint}`);
        const data = await res.json();
        if (data.results) {
            renderMovieGrid(data.results, isAppend);
        }
    } catch (e) {
        console.error('Fetch movies error:', e);
    } finally {
        isLoading = false;
    }
}

// ==========================================
// Movie Grid Rendering
// ==========================================
function renderMovieGrid(movies, isAppend = false) {
    const grid = document.getElementById('movieGrid');
    if (!grid) return;
    if (!isAppend) grid.innerHTML = '';

    movies.forEach((movie) => {
        if (!movie.poster_path) return;

        const card = document.createElement('div');
        card.className = 'movie-card rounded-xl overflow-hidden border border-white/10';
        card.innerHTML = `
            <img src="https://image.tmdb.org/t/p/w500${movie.poster_path}" alt="${escapeHtml(movie.title)}" 
                 class="w-full h-auto aspect-[2/3] object-cover" loading="lazy">
            <div class="movie-overlay">
                <h3 class="font-bold text-sm mb-2">${escapeHtml(movie.title)}</h3>
                <div class="flex items-center justify-between mb-3">
                    <span class="flex items-center text-xs">
                        <svg class="w-4 h-4 star-rating mr-1" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                        </svg>
                        ${movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A'}
                    </span>
                    <span class="text-xs text-gray-400">${movie.release_date ? movie.release_date.split('-')[0] : ''}</span>
                </div>
                <div class="flex space-x-2">
                    <button type="button" class="play-btn flex-1 glassmorphic px-3 py-2 rounded-lg text-xs font-semibold hover:bg-white/20 transition-all flex items-center justify-center space-x-1">
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z"/>
                        </svg>
                        <span>Play</span>
                    </button>
                    <button type="button" class="fav-btn glassmorphic p-2 rounded-lg hover:bg-white/20 transition-all" data-movie-id="${movie.id}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        grid.appendChild(card);

        // Play button -> open streaming drawer
        const playBtn = card.querySelector('.play-btn');
        playBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            openStreamingDrawer(movie.id, movie.title);
        });

        // Favorite button
        const favBtn = card.querySelector('.fav-btn');
        favBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleFavorite(movie, favBtn);
        });
    });

    // Check which movies are already favorited
    checkFavorites();
}


// ==========================================
// Streaming Drawer (opens streaming links)
// ==========================================
async function openStreamingDrawer(tmdbId, title) {
    try {
        // Get watch providers and external IDs via backend proxy
        const [provRes, idRes] = await Promise.all([
            fetch(`${BACKEND_URL}/tmdb/movie/${tmdbId}/watch/providers`),
            fetch(`${BACKEND_URL}/tmdb/movie/${tmdbId}/external_ids`)
        ]);

        const provData = await provRes.json();
        const idData = await idRes.json();
        const imdbId = idData.imdb_id;
        const region = localStorage.getItem('user_region') || 'TW';
        const regData = provData.results?.[region];
        let providers = regData?.flatrate || [];

        // If no providers in user's region, try nearby regions
        if (providers.length === 0) {
            const fallbackRegions = ['HK', 'SG', 'US', 'JP'];
            for (const r of fallbackRegions) {
                const fallbackData = provData.results?.[r]?.flatrate || [];
                if (fallbackData.length > 0) {
                    providers = fallbackData;
                    break;
                }
            }
        }

        // Still no providers — try direct platform link, then Google as last resort
        if (providers.length === 0) {
            if (imdbId) {
                // Try to get streaming options from any region
                try {
                    const streamRes = await fetch(`${BACKEND_URL}/streaming/${imdbId}`);
                    if (streamRes.ok) {
                        const streamData = await streamRes.json();
                        const allRegions = ['tw', 'hk', 'sg', 'us', 'jp'];
                        for (const r of allRegions) {
                            const options = streamData.streamingOptions?.[r] || [];
                            if (options.length > 0) {
                                window.open(options[0].link, '_blank');
                                return;
                            }
                        }
                    }
                } catch (e) {
                    console.warn('Streaming API fallback for no-provider case');
                }
            }
            // Absolute last resort
            window.open(`https://www.google.com/search?q=${encodeURIComponent(title + ' 線上看')}`, '_blank');
            return;
        }

        // Try to get direct streaming links from Streaming Availability API
        let directLink = null;
        if (imdbId) {
            try {
                const streamRes = await fetch(`${BACKEND_URL}/streaming/${imdbId}`);
                if (streamRes.ok) {
                    const streamingData = await streamRes.json();
                    const tryRegions = ['tw', 'hk', 'sg', 'us', 'jp'];
                    for (const r of tryRegions) {
                        const options = streamingData.streamingOptions?.[r] || [];
                        for (const p of providers) {
                            const match = options.find(opt => matchProvider(opt.service.id, p.provider_id));
                            if (match) {
                                directLink = match.link;
                                break;
                            }
                        }
                        if (directLink) break;
                    }
                }
            } catch (e) {
                console.warn('Streaming API fallback');
            }
        }

        // Fallback: generate direct platform link from provider info
        if (!directLink) {
            directLink = generateFallbackLink(providers[0].provider_id, providers[0].provider_name, imdbId);
        }

        window.open(directLink, '_blank');

    } catch (e) {
        console.error('Streaming drawer error:', e);
        window.open(`https://www.google.com/search?q=${encodeURIComponent(title + ' 線上看')}`, '_blank');
    }
}

function matchProvider(streamingId, tmdbId) {
    for (const [key, ids] of Object.entries(PROVIDER_MATCH)) {
        if (streamingId.includes(key) && ids.includes(tmdbId)) {
            return true;
        }
    }
    return false;
}

function generateFallbackLink(providerId, providerName, imdbId) {
    const links = {
        8: imdbId ? `https://www.netflix.com/title/${imdbId.replace('tt', '')}` : 'https://www.netflix.com',
        337: 'https://www.disneyplus.com',
        1899: imdbId ? `https://play.max.com/video/watch/${imdbId}` : 'https://www.max.com',
        384: imdbId ? `https://play.max.com/video/watch/${imdbId}` : 'https://www.max.com',
        119: imdbId ? `https://www.primevideo.com/detail/${imdbId}` : 'https://www.primevideo.com',
        350: imdbId ? `https://tv.apple.com/movie/${imdbId}` : 'https://tv.apple.com'
    };
    return links[providerId] || `https://www.google.com/search?q=${encodeURIComponent(providerName)}`;
}


// ==========================================
// Favorites
// ==========================================
async function toggleFavorite(movie, btn) {
    const u = sessionStorage.getItem('currentUser');
    if (!u) {
        openAuthModal();
        return;
    }

    const isFav = btn.dataset.favorited === 'true';

    // Optimistic UI
    btn.dataset.favorited = isFav ? 'false' : 'true';
    updateFavBtnStyle(btn, !isFav);

    try {
        const endpoint = isFav ? '/remove_favorite' : '/add_favorite';
        const body = isFav
            ? { username: u, movie_id: movie.id }
            : {
                username: u,
                movie_id: movie.id,
                title: movie.title,
                overview: movie.overview || '',
                poster_path: movie.poster_path || '',
                vote_average: movie.vote_average || 0,
                genre_ids: movie.genre_ids || [],
                vote_count: movie.vote_count || 0
            };

        await fetch(`${BACKEND_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
    } catch (e) {
        console.error('Favorite API Error', e);
        // Revert on failure
        btn.dataset.favorited = isFav ? 'true' : 'false';
        updateFavBtnStyle(btn, isFav);
    }
}

function updateFavBtnStyle(btn, isFav) {
    const svg = btn.querySelector('svg');
    if (isFav) {
        svg.setAttribute('fill', '#ef4444');
        svg.setAttribute('stroke', '#ef4444');
    } else {
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
    }
}

async function checkFavorites() {
    const u = sessionStorage.getItem('currentUser');
    if (!u) return;
    try {
        const res = await fetch(`${BACKEND_URL}/get_favorites?username=${u}`);
        const favorites = await res.json();
        const favIds = new Set(favorites.map(f => f.movie_id));

        document.querySelectorAll('.fav-btn').forEach(btn => {
            const id = parseInt(btn.dataset.movieId);
            if (favIds.has(id)) {
                btn.dataset.favorited = 'true';
                updateFavBtnStyle(btn, true);
            }
        });
    } catch (e) {
        // silently fail
    }
}


// ==========================================
// Platform Tabs
// ==========================================
function setupPlatformTabs() {
    const tabs = document.querySelectorAll('.platform-tab');
    const colorMap = {
        'all': 'rgba(102, 126, 234, 0.6)',
        'netflix': 'rgba(229, 9, 20, 0.6)',
        'disney': 'rgba(17, 60, 207, 0.6)',
        'prime': 'rgba(0, 168, 225, 0.6)',
        'hbo': 'rgba(157, 52, 218, 0.6)',
        'apple': 'rgba(255, 255, 255, 0.4)',
    };

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active from all
            tabs.forEach(t => {
                t.classList.remove('active');
                t.style.boxShadow = '0 0 0 rgba(0,0,0,0)';
            });

            // Set active
            tab.classList.add('active');
            const platform = tab.dataset.platform;
            if (colorMap[platform]) {
                tab.style.boxShadow = `0 0 20px ${colorMap[platform]}`;
            }

            // Update state and fetch
            const config = PLATFORM_MAP[platform] || PLATFORM_MAP['all'];
            currentPage = 1;
            currentMode = config.mode;
            currentPlatformId = config.id;
            currentPlatformName = config.name;

            // Update hero title if exists
            const heroTitle = document.getElementById('hero-section-title');
            if (heroTitle) {
                heroTitle.textContent = config.name === '所有趨勢' ? 'Trending Now' : config.name;
            }

            fetchMoviesData(false);
        });
    });
}


// ==========================================
// AI Command Center (the center search bar)
// ==========================================
function setupCommandCenter() {
    const input = document.getElementById('aiCommandInput');
    const sendBtn = document.getElementById('aiCommandSend');

    if (!input || !sendBtn) return;

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleCommandInput(input.value.trim());
        }
    });

    sendBtn.addEventListener('click', (e) => {
        e.preventDefault();
        handleCommandInput(input.value.trim());
    });
}

function handleCommandInput(query) {
    if (!query) return;

    const u = sessionStorage.getItem('currentUser');

    // If user is logged in, open chat and send message
    if (u) {
        openChatPanel();
        sendChatMessage(query);
        document.getElementById('aiCommandInput').value = '';
    } else {
        // Not logged in - treat as movie search
        runSearch(query);
        document.getElementById('aiCommandInput').value = '';
    }
}


// ==========================================
// Search
// ==========================================
function runSearch(query) {
    currentSearchQuery = query;
    currentPage = 1;
    currentMode = 'search';
    currentPlatformName = `搜尋: ${query}`;

    // Remove active from platform tabs
    document.querySelectorAll('.platform-tab').forEach(t => {
        t.classList.remove('active');
        t.style.boxShadow = '0 0 0 rgba(0,0,0,0)';
    });

    fetchMoviesData(false);
}


// ==========================================
// Chat Panel (AI Assistant)
// ==========================================
function setupChatPanel() {
    const toggleBtn = document.getElementById('chatToggleBtn');
    const closeBtn = document.getElementById('closeChatBtn');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');

    if (toggleBtn) toggleBtn.addEventListener('click', () => openChatPanel());
    if (closeBtn) closeBtn.addEventListener('click', () => closeChatPanel());
    if (chatInput) chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendChatMessage(chatInput.value.trim());
            chatInput.value = '';
        }
    });
    if (sendBtn) sendBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (chatInput) {
            sendChatMessage(chatInput.value.trim());
            chatInput.value = '';
        }
    });
}

function openChatPanel() {
    const panel = document.getElementById('chatPanel');
    if (panel) panel.classList.add('active');
}

function closeChatPanel() {
    const panel = document.getElementById('chatPanel');
    if (panel) panel.classList.remove('active');
}

function addChatMessage(text, isUser = false) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    // Clear welcome message on first real message
    const emptyMsg = container.querySelector('.chat-welcome');
    if (emptyMsg) emptyMsg.remove();

    const div = document.createElement('div');
    div.className = `chat-message flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`;

    div.innerHTML = `
        ${!isUser ? `
            <div class="bg-gradient-to-r from-[#667eea] to-[#764ba2] p-2 rounded-lg flex-shrink-0">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                </svg>
            </div>
        ` : ''}
        <div class="glassmorphic p-3 rounded-lg flex-1 max-w-[85%] ${isUser ? 'bg-gradient-to-r from-[#667eea]/80 to-[#764ba2]/80' : ''}">
            <p class="text-sm ${isUser ? 'text-white' : 'text-gray-300'}" style="white-space: pre-wrap;">${escapeHtml(text)}</p>
        </div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    const typing = document.createElement('div');
    typing.id = 'typingIndicator';
    typing.className = 'chat-message flex items-start space-x-3';
    typing.innerHTML = `
        <div class="bg-gradient-to-r from-[#667eea] to-[#764ba2] p-2 rounded-lg flex-shrink-0">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
        </div>
        <div class="glassmorphic p-3 rounded-lg">
            <div class="flex gap-1 items-center h-5">
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </div>
        </div>
    `;
    container.appendChild(typing);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

async function sendChatMessage(message) {
    if (!message) return;

    const u = sessionStorage.getItem('currentUser');
    if (!u) {
        openAuthModal();
        return;
    }

    addChatMessage(message, true);
    showTypingIndicator();

    try {
        const response = await fetch(`${BACKEND_URL}/agent_query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: u,
                platform_name: currentPlatformName,
                view_mode: currentMode,
                model: "llama3.1:8b",
                messages: [{ role: "user", content: message }]
            })
        });

        removeTypingIndicator();
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Error: ${response.status}`);
        }

        const reply = data.message?.content || "AI 無法產生回應";
        addChatMessage(reply, false);
    } catch (error) {
        removeTypingIndicator();
        console.error('Chat error:', error);
        addChatMessage(`錯誤: ${error.message}`, false);
    }
}


// ==========================================
// Auth
// ==========================================
function setupAuth() {
    const loginBtn = document.getElementById('loginBtn');
    const navUserBtn = document.getElementById('navUserBtn');
    const navSearchBtn = document.getElementById('navSearchBtn');

    if (loginBtn) loginBtn.addEventListener('click', () => openAuthModal());
    if (navUserBtn) navUserBtn.addEventListener('click', () => {
        const u = sessionStorage.getItem('currentUser');
        if (u) {
            // Already logged in - show options
            if (confirm(`已登入: ${u}\n要登出嗎？`)) {
                logout();
            }
        } else {
            openAuthModal();
        }
    });
    if (navSearchBtn) navSearchBtn.addEventListener('click', () => {
        const input = document.getElementById('aiCommandInput');
        if (input) input.focus();
    });
}

function openAuthModal() {
    const modal = document.getElementById('authModal');
    if (modal) modal.classList.add('active');
}

function closeAuthModal() {
    const modal = document.getElementById('authModal');
    if (modal) modal.classList.remove('active');
}

async function handleLogin() {
    const user = document.getElementById('authUser').value.trim();
    const pass = document.getElementById('authPass').value.trim();
    if (!user || !pass) return;

    try {
        const res = await fetch(`${BACKEND_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();
        if (res.ok) {
            sessionStorage.setItem('currentUser', data.username);
            localStorage.setItem('user_region', data.region);
            closeAuthModal();
            showUserSession(data.username);
            checkFavorites();
        } else {
            alert(data.message || '登入失敗');
        }
    } catch (e) {
        alert('連線錯誤');
    }
}

async function handleRegister() {
    const user = document.getElementById('authUser').value.trim();
    const pass = document.getElementById('authPass').value.trim();
    if (!user || !pass) return;

    try {
        const res = await fetch(`${BACKEND_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();
        alert(data.message);
        if (res.ok) {
            // Auto-login after register
            await handleLogin();
        }
    } catch (e) {
        alert('連線錯誤');
    }
}

function showUserSession(username) {
    // Update navbar user button to show logged-in state
    const userBtn = document.getElementById('navUserBtn');
    if (userBtn) {
        userBtn.innerHTML = `
            <div class="w-7 h-7 rounded-full bg-gradient-to-r from-[#667eea] to-[#764ba2] flex items-center justify-center text-xs font-bold">
                ${username.charAt(0).toUpperCase()}
            </div>
        `;
    }

    // Show recommendations link
    const recLink = document.getElementById('recLink');
    if (recLink) recLink.classList.remove('hidden');
}

function logout() {
    sessionStorage.clear();
    location.reload();
}


// ==========================================
// Load More
// ==========================================
function setupLoadMore() {
    // Infinite scroll
    let sentinel = document.getElementById('loadMoreSentinel');
    if (!sentinel) {
        sentinel = document.createElement('div');
        sentinel.id = 'loadMoreSentinel';
        sentinel.className = 'w-full h-20 flex items-center justify-center';
        sentinel.innerHTML = `
            <button type="button" id="loadMoreBtn" class="bg-gradient-to-r from-[#667eea] to-[#764ba2] px-8 py-3 rounded-lg font-semibold hover:scale-105 transition-all">
                載入更多
            </button>
        `;
        const grid = document.getElementById('movieGrid');
        if (grid && grid.parentNode) {
            grid.parentNode.appendChild(sentinel);
        }
    }

    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', () => {
            currentPage++;
            fetchMoviesData(true);
        });
    }
}


// ==========================================
// Hero Section (dynamic featured movie)
// ==========================================
async function loadHeroMovie() {
    try {
        const res = await fetch(`${BACKEND_URL}/tmdb/trending/movie/day?language=zh-TW`);
        const data = await res.json();
        if (data.results && data.results.length > 0) {
            const featured = data.results[0];

            const heroImg = document.getElementById('heroImage');
            const heroTitle = document.getElementById('heroTitle');
            const heroRating = document.getElementById('heroRating');
            const heroYear = document.getElementById('heroYear');
            const heroOverview = document.getElementById('heroOverview');

            if (heroImg) heroImg.src = `https://image.tmdb.org/t/p/original${featured.backdrop_path || featured.poster_path}`;
            if (heroTitle) heroTitle.textContent = featured.title;
            if (heroRating) heroRating.textContent = featured.vote_average ? featured.vote_average.toFixed(1) : '';
            if (heroYear) heroYear.textContent = featured.release_date ? featured.release_date.split('-')[0] : '';
            if (heroOverview) heroOverview.textContent = featured.overview || '';
        }
    } catch (e) {
        console.warn('Hero movie load failed:', e);
    }
}

// Load hero on DOMContentLoaded
window.addEventListener('DOMContentLoaded', () => {
    loadHeroMovie();
});


// ==========================================
// Utilities
// ==========================================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Expose functions for inline HTML calls
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.closeAuthModal = closeAuthModal;
window.logout = logout;