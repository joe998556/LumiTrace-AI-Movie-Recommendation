package com.lumitrace.app.recommendation

import com.lumitrace.app.data.Movie
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalRecommendationRankerTest {
    @Test
    fun numpyFloat16ReaderDecodesBundledVectorFormat() {
        val header = "{'descr': '<f2', 'fortran_order': False, 'shape': (2, 2), }\n".toByteArray()
        val bytes = ByteBuffer.allocate(10 + header.size + 8)
            .order(ByteOrder.LITTLE_ENDIAN)
            .put(byteArrayOf(0x93.toByte(), 'N'.code.toByte(), 'U'.code.toByte(), 'M'.code.toByte(), 'P'.code.toByte(), 'Y'.code.toByte()))
            .put(1.toByte())
            .put(0.toByte())
            .putShort(header.size.toShort())
            .put(header)
            .putShort(0x3c00.toShort())
            .putShort(0xc000.toShort())
            .putShort(0x3800.toShort())
            .putShort(0)
            .array()

        val decoded = NumpyFloat16Reader.decode(bytes, count = 2, dimension = 2)

        assertEquals(1f, decoded[0], 0.0001f)
        assertEquals(-2f, decoded[1], 0.0001f)
        assertEquals(0.5f, decoded[2], 0.0001f)
        assertEquals(0f, decoded[3], 0.0001f)
    }

    @Test
    fun highRatingBoostsSimilarMoviesAndLowRatingPenalizesNearbyCandidates() {
        val catalog = catalogOf(
            indexedMovie(1, "Positive seed", intArrayOf(878)) to floatArrayOf(1f, 0f),
            indexedMovie(2, "Semantic match", intArrayOf(878)) to normalized(0.99f, 0.1f),
            indexedMovie(3, "Negative seed", intArrayOf(27)) to floatArrayOf(0f, 1f),
            indexedMovie(4, "Near disliked", intArrayOf(27)) to normalized(0.1f, 0.99f),
            indexedMovie(5, "Mixed candidate", intArrayOf(18)) to normalized(0.7f, 0.7f)
        )

        val result = LocalRecommendationRanker.rank(
            catalog = catalog,
            rawSignals = listOf(
                TasteSignal(Movie(id = 1, title = "Positive seed", genreIds = listOf(878)), 9f),
                TasteSignal(Movie(id = 3, title = "Negative seed", genreIds = listOf(27)), 1f)
            ),
            requestedTopK = 3
        )

        assertEquals(2, result.movies.first().id)
        assertFalse(result.movies.any { it.id == 1 || it.id == 3 })
        assertTrue(result.movies.first().reason.orEmpty().contains("Positive seed"))
        val trace = result.traces.getValue(2)
        assertTrue(trace.semanticSimilarity > 0f)
        assertTrue(trace.negativePreferencePenalty >= 0f)
        assertTrue(trace.finalScore <= trace.baseScore)
    }

    @Test
    fun movieOutsideSemanticIndexStillDrivesGenreFallback() {
        val catalog = catalogOf(
            indexedMovie(10, "Comedy candidate", intArrayOf(35)) to floatArrayOf(1f, 0f),
            indexedMovie(11, "Drama candidate", intArrayOf(18)) to floatArrayOf(0f, 1f)
        )

        val result = LocalRecommendationRanker.rank(
            catalog = catalog,
            rawSignals = listOf(
                TasteSignal(Movie(id = 999, title = "Unindexed comedy", genreIds = listOf(35)), 9f)
            ),
            requestedTopK = 2
        )

        assertEquals(10, result.movies.first().id)
        assertTrue(result.movies.first().reason.orEmpty().contains("Comedy"))
    }

    @Test
    fun genreConstraintsFilterCatalogBeforeTasteRanking() {
        val catalog = catalogOf(
            indexedMovie(1, "Seed", intArrayOf(878)) to floatArrayOf(1f, 0f),
            indexedMovie(2, "Sci-fi hit", intArrayOf(878)) to normalized(0.95f, 0.1f),
            indexedMovie(3, "Comedy only", intArrayOf(35)) to normalized(0.99f, 0.05f),
            indexedMovie(4, "Thriller", intArrayOf(53)) to normalized(0.9f, 0.2f)
        )

        val result = LocalRecommendationRanker.rank(
            catalog = catalog,
            rawSignals = listOf(
                TasteSignal(Movie(id = 1, title = "Seed", genreIds = listOf(878)), 9f)
            ),
            requestedTopK = 5,
            constraints = RecommendationConstraints(
                requiredGenreGroups = listOf(setOf(53, 27, 9648, 80))
            )
        )

        assertEquals(listOf(4), result.movies.map { it.id })
        assertFalse(result.movies.any { it.id == 3 })
    }

    @Test
    fun refreshSeedChangesNearTiedPicksButKeepsStrongTasteAnchors() {
        val rows = buildList {
            add(indexedMovie(1, "Taste seed", intArrayOf(878)) to floatArrayOf(1f, 0f))
            add(indexedMovie(2, "Strong anchor", intArrayOf(878)) to normalized(0.999f, 0.04f))
            repeat(30) { index ->
                add(
                    indexedMovie(100 + index, "Near-tied candidate $index", intArrayOf(878)) to
                        normalized(0.82f, 0.57f)
                )
            }
        }
        val catalog = catalogOf(*rows.toTypedArray())
        val signals = listOf(TasteSignal(Movie(id = 1, title = "Taste seed", genreIds = listOf(878)), 9f))

        val first = LocalRecommendationRanker.rank(catalog, signals, requestedTopK = 10, variationSeed = 0L)
        val refreshed = LocalRecommendationRanker.rank(catalog, signals, requestedTopK = 10, variationSeed = 1L)
        val repeated = LocalRecommendationRanker.rank(catalog, signals, requestedTopK = 10, variationSeed = 1L)

        assertEquals(2, first.movies.first().id)
        assertEquals(2, refreshed.movies.first().id)
        assertEquals(refreshed.movies.map { it.id }, repeated.movies.map { it.id })
        assertFalse(first.movies.map { it.id }.toSet() == refreshed.movies.map { it.id }.toSet())
        assertTrue(first.movies.map { it.id }.toSet().intersect(refreshed.movies.map { it.id }.toSet()).size >= 3)
    }

    private fun indexedMovie(id: Int, title: String, genres: IntArray): IndexMovie {
        return IndexMovie(
            id = id,
            title = title,
            releaseDate = "2020-01-01",
            voteAverage = 8f,
            voteCount = 200,
            genreIds = genres,
            position = 0
        )
    }

    private fun catalogOf(vararg rows: Pair<IndexMovie, FloatArray>): LocalCatalog {
        val dimension = rows.first().second.size
        val movies = rows.mapIndexed { index, (movie, _) -> movie.copy(position = index) }
        val vectors = FloatArray(rows.size * dimension)
        rows.forEachIndexed { index, (_, vector) ->
            vector.copyInto(vectors, index * dimension)
        }
        return LocalCatalog(
            movies = movies,
            vectors = vectors,
            dimension = dimension,
            byId = movies.associate { it.id to it.position }
        )
    }

    private fun normalized(first: Float, second: Float): FloatArray {
        val length = kotlin.math.sqrt(first * first + second * second)
        return floatArrayOf(first / length, second / length)
    }
}
