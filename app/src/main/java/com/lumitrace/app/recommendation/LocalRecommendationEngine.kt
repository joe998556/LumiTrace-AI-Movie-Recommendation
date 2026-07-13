package com.lumitrace.app.recommendation

import android.content.res.AssetManager
import android.util.JsonReader
import com.lumitrace.app.data.Movie
import java.io.ByteArrayInputStream
import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import kotlin.math.abs
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.sqrt
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

data class TasteSignal(
    val movie: Movie,
    val rating: Float
)

data class LocalRecommendationResult(
    val movies: List<Movie>,
    val title: String,
    val summary: String,
    /** Per-movie local score components for the recommendation trace UI. */
    val traces: Map<Int, RecommendationTrace> = emptyMap()
)

data class RecommendationTrace(
    val semanticSimilarity: Float,
    val genreAffinity: Float,
    val qualityPrior: Float,
    val negativePreferencePenalty: Float,
    val diversityAdjustment: Float,
    val baseScore: Float,
    val finalScore: Float
)

internal data class IndexMovie(
    val id: Int,
    val title: String,
    val releaseDate: String,
    val voteAverage: Float,
    val voteCount: Int,
    val genreIds: IntArray,
    val position: Int
)

internal data class LocalCatalog(
    val movies: List<IndexMovie>,
    val vectors: FloatArray,
    val dimension: Int,
    val byId: Map<Int, Int>
)

private data class Candidate(
    val movie: IndexMovie,
    val score: Float,
    val semantic: Float,
    val genre: Float,
    val quality: Float,
    val negativePenalty: Float = 0f,
    val diversityAdjustment: Float = 0f,
    val refreshAdjustment: Float = 0f
)

/** Optional hard filters applied before taste ranking (used by Tonight). */
data class RecommendationConstraints(
    /** Each group is OR within the set; groups are AND-ed across the list. */
    val requiredGenreGroups: List<Set<Int>> = emptyList(),
    val minYear: Int? = null,
    val maxYear: Int? = null,
    /** Genre-overlap diversity penalty strength (lower = keep more same-mood films). */
    val diversifyStrength: Float = 0.08f
)

internal data class RankingWeights(
    val semantic: Float = 0.64f,
    val genre: Float = 0.22f,
    val quality: Float = 0.14f,
    val negativePenalty: Float = 0.32f,
    val refreshSpread: Float = 0.04f
) {
    init {
        require(kotlin.math.abs(semantic + genre + quality - 1f) < 0.0001f)
        require(negativePenalty in 0f..0.75f)
        require(refreshSpread in 0f..0.08f)
    }
}

class LocalRecommendationEngine(private val assets: AssetManager) {
    @Volatile
    private var cachedCatalog: LocalCatalog? = null

    suspend fun recommend(
        signals: List<TasteSignal>,
        topK: Int,
        constraints: RecommendationConstraints = RecommendationConstraints(),
        variationSeed: Long = 0L
    ): LocalRecommendationResult = withContext(Dispatchers.Default) {
        LocalRecommendationRanker.rank(loadCatalog(), signals, topK, constraints, variationSeed)
    }

    private fun loadCatalog(): LocalCatalog {
        cachedCatalog?.let { return it }
        return synchronized(this) {
            cachedCatalog ?: readCatalog().also { cachedCatalog = it }
        }
    }

    private fun readCatalog(): LocalCatalog {
        val manifest = JSONObject(readAssetText("$ASSET_ROOT/manifest.json"))
        val count = manifest.getInt("count")
        val dimension = manifest.getInt("dimension")
        require(count > 0 && dimension > 0) { "The bundled recommendation index is empty." }
        require(manifest.optString("dtype") == "float16") {
            "Unsupported recommendation index format."
        }

        val moviesName = manifest.getString("movies")
        val vectorsName = manifest.getString("vectors")
        val movies = readMovies("$ASSET_ROOT/$moviesName", count)
        val vectors = assets.open("$ASSET_ROOT/$vectorsName").use { input ->
            NumpyFloat16Reader.decode(input, count, dimension)
        }
        return LocalCatalog(
            movies = movies,
            vectors = vectors,
            dimension = dimension,
            byId = movies.associate { it.id to it.position }
        )
    }

    private fun readAssetText(path: String): String {
        return assets.open(path).bufferedReader(Charsets.UTF_8).use { it.readText() }
    }

    private fun readMovies(path: String, expectedCount: Int): List<IndexMovie> {
        val movies = ArrayList<IndexMovie>(expectedCount)
        assets.open(path).bufferedReader(Charsets.UTF_8).use { input ->
            JsonReader(input).use { reader ->
                reader.beginArray()
                while (reader.hasNext()) {
                    var id = 0
                    var title = ""
                    var releaseDate = ""
                    var voteAverage = 0f
                    var voteCount = 0
                    var genreIds = IntArray(0)
                    reader.beginObject()
                    while (reader.hasNext()) {
                        when (reader.nextName()) {
                            "id" -> id = reader.nextInt()
                            "title" -> title = reader.nextString()
                            "release_date" -> releaseDate = reader.nextString()
                            "vote_average" -> voteAverage = reader.nextDouble().toFloat()
                            "vote_count" -> voteCount = reader.nextDouble().toInt()
                            "genre_ids" -> {
                                val genres = ArrayList<Int>(4)
                                reader.beginArray()
                                while (reader.hasNext()) genres += reader.nextInt()
                                reader.endArray()
                                genreIds = genres.toIntArray()
                            }
                            else -> reader.skipValue()
                        }
                    }
                    reader.endObject()
                    require(id > 0) { "The bundled recommendation index contains an invalid movie ID." }
                    movies += IndexMovie(
                        id = id,
                        title = title.ifBlank { "Untitled" },
                        releaseDate = releaseDate,
                        voteAverage = voteAverage,
                        voteCount = voteCount,
                        genreIds = genreIds,
                        position = movies.size
                    )
                }
                reader.endArray()
            }
        }
        require(movies.size == expectedCount) { "Movie metadata and vector counts do not match." }
        return movies
    }

    private companion object {
        const val ASSET_ROOT = "lumitrace"
    }
}

internal object NumpyFloat16Reader {
    fun decode(bytes: ByteArray, count: Int, dimension: Int): FloatArray {
        return ByteArrayInputStream(bytes).use { input -> decode(input, count, dimension) }
    }

    fun decode(source: InputStream, count: Int, dimension: Int): FloatArray {
        val input = source.buffered(64 * 1024)
        val prefix = ByteArray(8)
        input.readFully(prefix)
        val magic = byteArrayOf(0x93.toByte(), 'N'.code.toByte(), 'U'.code.toByte(), 'M'.code.toByte(), 'P'.code.toByte(), 'Y'.code.toByte())
        require(prefix.copyOfRange(0, magic.size).contentEquals(magic)) {
            "The bundled vector file is not a NumPy array."
        }

        val majorVersion = prefix[6].toInt() and 0xff
        val headerLength = if (majorVersion == 1) {
            val lengthBytes = ByteArray(2)
            input.readFully(lengthBytes)
            (lengthBytes[0].toInt() and 0xff) or ((lengthBytes[1].toInt() and 0xff) shl 8)
        } else {
            val lengthBytes = ByteArray(4)
            input.readFully(lengthBytes)
            ByteBuffer.wrap(lengthBytes).order(ByteOrder.LITTLE_ENDIAN).int
        }

        require(headerLength > 0) { "The bundled vector header is invalid." }
        val headerBytes = ByteArray(headerLength)
        input.readFully(headerBytes)
        val header = String(headerBytes, Charsets.US_ASCII)
        require(header.contains("'descr': '<f2'") && header.contains("'fortran_order': False")) {
            "The bundled vectors must be little-endian float16 rows."
        }
        require(header.contains("($count, $dimension)")) {
            "The bundled vector header does not match its manifest."
        }
        val valueCount = Math.multiplyExact(count, dimension)
        val vectors = FloatArray(valueCount)
        val chunk = ByteArray(64 * 1024)
        var vectorIndex = 0
        while (vectorIndex < valueCount) {
            val bytesToRead = minOf(chunk.size, (valueCount - vectorIndex) * 2)
            input.readFully(chunk, bytesToRead)
            var offset = 0
            while (offset < bytesToRead) {
                val half = (chunk[offset].toInt() and 0xff) or
                    ((chunk[offset + 1].toInt() and 0xff) shl 8)
                vectors[vectorIndex++] = halfToFloat(half)
                offset += 2
            }
        }
        return vectors
    }

    private fun InputStream.readFully(buffer: ByteArray, length: Int = buffer.size) {
        var offset = 0
        while (offset < length) {
            val read = read(buffer, offset, length - offset)
            require(read >= 0) { "The bundled vector file is truncated." }
            offset += read
        }
    }

    private fun halfToFloat(half: Int): Float {
        val sign = (half and 0x8000) shl 16
        val exponent = (half ushr 10) and 0x1f
        var mantissa = half and 0x03ff
        val bits = when (exponent) {
            0 -> {
                if (mantissa == 0) {
                    sign
                } else {
                    var unbiasedExponent = -14
                    while ((mantissa and 0x0400) == 0) {
                        mantissa = mantissa shl 1
                        unbiasedExponent--
                    }
                    mantissa = mantissa and 0x03ff
                    sign or ((unbiasedExponent + 127) shl 23) or (mantissa shl 13)
                }
            }
            0x1f -> sign or 0x7f800000 or (mantissa shl 13)
            else -> sign or ((exponent + 112) shl 23) or (mantissa shl 13)
        }
        return Float.fromBits(bits)
    }
}

internal object LocalRecommendationRanker {
    fun rank(
        catalog: LocalCatalog,
        rawSignals: List<TasteSignal>,
        requestedTopK: Int,
        constraints: RecommendationConstraints = RecommendationConstraints(),
        variationSeed: Long = 0L,
        weights: RankingWeights = RankingWeights()
    ): LocalRecommendationResult {
        val signals = rawSignals
            .filter { it.movie.id > 0 }
            .distinctBy { it.movie.id }
        require(signals.isNotEmpty()) { "Mark at least one movie as watched before requesting recommendations." }

        val topK = requestedTopK.coerceIn(1, minOf(300, catalog.movies.size))
        val excludedIds = signals.mapTo(HashSet()) { it.movie.id }
        val genreWeights = buildGenreWeights(signals)
        val genreScale = if (genreWeights.isEmpty()) 1f else genreWeights.values.maxOf { abs(it) }.coerceAtLeast(1f)
        val profile = buildTasteProfile(catalog, signals)
        val hasSemanticProfile = profile.any { it != 0f }
        val genreGroups = constraints.requiredGenreGroups.filter { it.isNotEmpty() }
        val poolMultiplier = if (genreGroups.isEmpty()) 6 else 10
        val minimumCandidatePool = if (catalog.movies.size >= 10_000) 1_000 else 100
        val diversifyStrength = constraints.diversifyStrength.coerceIn(0f, 0.2f)

        val candidates = catalog.movies.asSequence()
            .filterNot { it.id in excludedIds }
            .filter { movie -> matchesGenreGroups(movie.genreIds, genreGroups) }
            .filter { movie -> matchesYear(movie.releaseDate, constraints.minYear, constraints.maxYear) }
            .filter { movie -> movie.voteCount < 50 || movie.voteAverage >= 5f }
            .map { movie ->
                val semantic = if (hasSemanticProfile) dot(catalog, movie.position, profile) else 0f
                val genre = genreAffinity(movie.genreIds, genreWeights, genreScale)
                val quality = qualityPrior(movie)
                val score = if (hasSemanticProfile) {
                    semantic * weights.semantic + genre * weights.genre + quality * weights.quality
                } else {
                    genre * 0.72f + quality * 0.28f
                }
                Candidate(movie, score, semantic, genre, quality)
            }
            .sortedByDescending { it.score }
            .take(max(minimumCandidatePool, topK * poolMultiplier))
            .toList()

        val negativeSeeds = signals.mapNotNull { signal ->
            val rating = signal.rating.takeIf { it > 0f } ?: return@mapNotNull null
            if (rating >= 5f) return@mapNotNull null
            val position = catalog.byId[signal.movie.id] ?: return@mapNotNull null
            position to ((5f - rating) / 4f).coerceIn(0f, 1f)
        }

        val penalized = candidates.map { candidate ->
            val penalty = negativeSeeds.maxOfOrNull { (negativePosition, strength) ->
                max(0f, vectorSimilarity(catalog, candidate.movie.position, negativePosition)) * strength
            } ?: 0f
            val weightedPenalty = penalty * weights.negativePenalty
            candidate.copy(score = candidate.score - weightedPenalty, negativePenalty = weightedPenalty)
        }.sortedByDescending { it.score }

        val refreshed = penalized.map { candidate ->
            candidate.copy(
                refreshAdjustment = refreshAdjustment(candidate.movie.id, variationSeed, weights.refreshSpread)
            )
        }
        val selected = diversify(refreshed, topK, diversifyStrength)
        val positiveSignals = signals.filter { it.rating <= 0f || it.rating >= 5f }
        val movies = selected.map { candidate ->
            Movie(
                id = candidate.movie.id,
                title = candidate.movie.title,
                releaseDate = candidate.movie.releaseDate,
                voteAverage = candidate.movie.voteAverage.toDouble(),
                genreIds = candidate.movie.genreIds.toList(),
                reason = recommendationReason(catalog, candidate, positiveSignals, genreWeights)
            )
        }

        val ratedCount = signals.count { it.rating > 0f }
        return LocalRecommendationResult(
            movies = movies,
            title = "Recommended on this device",
            summary = "Built locally from ${signals.size} watched movies${if (ratedCount > 0) " and $ratedCount ratings" else ""}. Refresh explores near-tied matches without changing your taste scores.",
            traces = selected.associate { candidate ->
                candidate.movie.id to RecommendationTrace(
                    semanticSimilarity = candidate.semantic,
                    genreAffinity = candidate.genre,
                    qualityPrior = candidate.quality,
                    negativePreferencePenalty = candidate.negativePenalty,
                    diversityAdjustment = candidate.diversityAdjustment,
                    baseScore = candidate.score + candidate.negativePenalty,
                    finalScore = candidate.score - candidate.diversityAdjustment
                )
            }
        )
    }

    private fun matchesGenreGroups(genreIds: IntArray, groups: List<Set<Int>>): Boolean {
        if (groups.isEmpty()) return true
        if (genreIds.isEmpty()) return false
        return groups.all { group -> genreIds.any { it in group } }
    }

    private fun matchesYear(releaseDate: String, minYear: Int?, maxYear: Int?): Boolean {
        if (minYear == null && maxYear == null) return true
        val year = releaseDate.take(4).toIntOrNull() ?: return false
        if (minYear != null && year < minYear) return false
        if (maxYear != null && year > maxYear) return false
        return true
    }

    private fun buildTasteProfile(catalog: LocalCatalog, signals: List<TasteSignal>): FloatArray {
        val profile = FloatArray(catalog.dimension)
        var totalWeight = 0f
        for (signal in signals) {
            val position = catalog.byId[signal.movie.id] ?: continue
            val weight = when {
                signal.rating <= 0f -> 1f
                signal.rating < 5f -> 0f
                else -> (signal.rating - 4f).coerceAtLeast(0.5f)
            }
            if (weight <= 0f) continue
            val offset = position * catalog.dimension
            for (dimension in 0 until catalog.dimension) {
                profile[dimension] += catalog.vectors[offset + dimension] * weight
            }
            totalWeight += weight
        }
        if (totalWeight <= 0f) return profile

        var squaredNorm = 0f
        for (value in profile) squaredNorm += value * value
        val norm = sqrt(squaredNorm).coerceAtLeast(1e-8f)
        for (index in profile.indices) profile[index] /= norm
        return profile
    }

    private fun buildGenreWeights(signals: List<TasteSignal>): Map<Int, Float> {
        val weights = mutableMapOf<Int, Float>()
        for (signal in signals) {
            val strength = when {
                signal.rating <= 0f -> 1f
                signal.rating == 5f -> 0.5f
                else -> signal.rating - 5f
            }
            for (genre in signal.movie.genreIds) {
                weights[genre] = (weights[genre] ?: 0f) + strength
            }
        }
        return weights
    }

    private fun genreAffinity(genres: IntArray, weights: Map<Int, Float>, scale: Float): Float {
        if (genres.isEmpty() || weights.isEmpty()) return 0f
        var sum = 0.0
        for (i in genres.indices) {
            sum += (weights[genres[i]] ?: 0f).toDouble()
        }
        return (sum.toFloat() / (scale * genres.size.coerceAtLeast(1))).coerceIn(-1f, 1f)
    }

    private fun qualityPrior(movie: IndexMovie): Float {
        val votes = movie.voteCount.coerceAtLeast(0).toFloat()
        val rating = movie.voteAverage.coerceIn(0f, 10f)
        val adjustedRating = (votes * rating + 1_000f * 6.2f) / (votes + 1_000f)
        val confidence = (ln(1f + votes) / ln(20_001f)).coerceIn(0f, 1f)
        return (adjustedRating / 10f) * 0.80f + confidence * 0.20f
    }

    private fun diversify(
        candidates: List<Candidate>,
        topK: Int,
        strength: Float = 0.08f
    ): List<Candidate> {
        if (strength <= 0f) return candidates.take(topK)
        val remaining = candidates.toMutableList()
        val selected = ArrayList<Candidate>(topK)
        while (remaining.isNotEmpty() && selected.size < topK) {
            val best = remaining.maxByOrNull { candidate ->
                val overlap = selected.maxOfOrNull { chosen -> genreOverlap(candidate.movie.genreIds, chosen.movie.genreIds) } ?: 0f
                candidate.score + candidate.refreshAdjustment - overlap * strength
            } ?: break
            val overlap = selected.maxOfOrNull { chosen -> genreOverlap(best.movie.genreIds, chosen.movie.genreIds) } ?: 0f
            selected += best.copy(diversityAdjustment = overlap * strength)
            remaining.remove(best)
        }
        return selected
    }

    private fun refreshAdjustment(movieId: Int, variationSeed: Long, spread: Float): Float {
        if (variationSeed == 0L) return 0f
        var mixed = variationSeed xor (movieId.toLong() * -7046029254386353131L)
        mixed = (mixed xor (mixed ushr 30)) * -4658895280553007687L
        mixed = (mixed xor (mixed ushr 27)) * -7723592293110705685L
        mixed = mixed xor (mixed ushr 31)
        val unit = ((mixed ushr 40) and 0xFFFFFFL).toFloat() / 0xFFFFFFL.toFloat()
        return (unit - 0.5f) * spread.coerceIn(0f, 0.08f)
    }

    private fun genreOverlap(first: IntArray, second: IntArray): Float {
        if (first.isEmpty() || second.isEmpty()) return 0f
        val intersection = first.count { it in second }
        val union = first.size + second.size - intersection
        return if (union == 0) 0f else intersection.toFloat() / union
    }

    private fun recommendationReason(
        catalog: LocalCatalog,
        candidate: Candidate,
        positiveSignals: List<TasteSignal>,
        genreWeights: Map<Int, Float>
    ): String {
        val closest = positiveSignals.mapNotNull { signal ->
            val position = catalog.byId[signal.movie.id] ?: return@mapNotNull null
            signal to vectorSimilarity(catalog, candidate.movie.position, position)
        }.maxByOrNull { it.second }

        if (closest != null) {
            val (signal, _) = closest
            val rating = signal.rating.takeIf { it > 0f }?.let {
                " (${String.format(Locale.US, "%.1f", it)}/10)"
            }.orEmpty()
            return "Semantically close to ${signal.movie.title}$rating, balanced with your ratings and list variety."
        }

        val genre = candidate.movie.genreIds
            .maxByOrNull { genreWeights[it] ?: Float.NEGATIVE_INFINITY }
            ?.let { GENRE_NAMES[it] }
        return if (genre != null) {
            "Matches your $genre preference and is ranked entirely on this device."
        } else {
            "A strong MovieLens starter pick, ranked entirely on this device."
        }
    }

    private fun dot(catalog: LocalCatalog, position: Int, vector: FloatArray): Float {
        val offset = position * catalog.dimension
        var total = 0f
        for (dimension in 0 until catalog.dimension) {
            total += catalog.vectors[offset + dimension] * vector[dimension]
        }
        return total
    }

    private fun vectorSimilarity(catalog: LocalCatalog, first: Int, second: Int): Float {
        val firstOffset = first * catalog.dimension
        val secondOffset = second * catalog.dimension
        var total = 0f
        for (dimension in 0 until catalog.dimension) {
            total += catalog.vectors[firstOffset + dimension] * catalog.vectors[secondOffset + dimension]
        }
        return total
    }

    private val GENRE_NAMES = mapOf(
        12 to "Adventure",
        14 to "Fantasy",
        16 to "Animation",
        18 to "Drama",
        27 to "Horror",
        28 to "Action",
        35 to "Comedy",
        36 to "History",
        37 to "Western",
        53 to "Thriller",
        80 to "Crime",
        99 to "Documentary",
        878 to "Science Fiction",
        9648 to "Mystery",
        10402 to "Music",
        10749 to "Romance",
        10751 to "Family",
        10752 to "War"
    )
}
