package com.lumitrace.app.recommendation

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.lumitrace.app.data.Movie
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.BeforeClass
import org.junit.Test

class BundledRecommendationScenarioTest {
    @Test
    fun scienceFictionTasteReturnsCoherentUnwatchedPicks() {
        val seeds = listOf(
            signal(329865, 9f), // Arrival
            signal(157336, 9f), // Interstellar
            signal(27205, 8.5f), // Inception
            signal(348, 2f) // Alien: explicit negative preference
        )

        val result = LocalRecommendationRanker.rank(catalog, seeds, requestedTopK = 20)
        val titles = result.movies.joinToString { it.title }
        println("SCI_FI_SCENARIO=$titles")

        assertEquals(20, result.movies.size)
        assertFalse("Seeds leaked into recommendations: $titles", result.movies.any { movie -> seeds.any { it.movie.id == movie.id } })
        assertTrue(
            "Expected a clear science-fiction signal, got: $titles",
            result.movies.count { 878 in it.genreIds } >= 8
        )
        assertTrue(result.movies.all { it.reason.orEmpty().startsWith("Semantically close to") })
        assertEquals(result.movies.map { it.id }.toSet(), result.traces.keys)
    }

    @Test
    fun familyTasteKeepsFamilyAndAnimationProminent() {
        val seeds = listOf(signal(862, 9f), signal(12, 9f)) // Toy Story, Finding Nemo

        val result = LocalRecommendationRanker.rank(catalog, seeds, requestedTopK = 12)
        val titles = result.movies.joinToString { it.title }
        val familyGenres = setOf(16, 10751)
        println("FAMILY_SCENARIO=$titles")

        assertFalse(result.movies.any { movie -> seeds.any { it.movie.id == movie.id } })
        assertTrue(
            "Expected family or animation picks, got: $titles",
            result.movies.count { movie -> movie.genreIds.any { it in familyGenres } } >= 6
        )
    }

    @Test
    fun crimeDramaTasteReturnsGenreRelevantCandidates() {
        val seeds = listOf(
            signal(238, 9.5f), // The Godfather
            signal(680, 9f), // Pulp Fiction
            signal(155, 8.5f) // The Dark Knight
        )

        val result = LocalRecommendationRanker.rank(catalog, seeds, requestedTopK = 12)
        val titles = result.movies.joinToString { it.title }
        val relatedGenres = setOf(80, 18, 53)
        println("CRIME_SCENARIO=$titles")

        assertFalse(result.movies.any { movie -> seeds.any { it.movie.id == movie.id } })
        assertTrue(
            "Expected crime, drama, or thriller picks, got: $titles",
            result.movies.count { movie -> movie.genreIds.any { it in relatedGenres } } >= 8
        )
    }

    @Test
    fun explicitLowRatingCreatesARealPostRankingPenalty() {
        val seeds = listOf(signal(329865, 9f), signal(348, 1f)) // Arrival liked, Alien disliked

        val result = LocalRecommendationRanker.rank(catalog, seeds, requestedTopK = 100)
        val strongestPenalty = result.traces.values.maxOf { it.negativePreferencePenalty }

        assertTrue("Expected the disliked Alien signal to penalize a nearby candidate.", strongestPenalty > 0.05f)
        assertTrue(result.traces.values.all { it.finalScore <= it.baseScore + 0.0001f })
    }

    companion object {
        private lateinit var catalog: LocalCatalog
        private lateinit var moviesById: Map<Int, IndexMovie>

        @JvmStatic
        @BeforeClass
        fun loadBundledCatalog() {
            val root = listOf(
                File("src/main/assets/lumitrace"),
                File("app/src/main/assets/lumitrace")
            ).firstOrNull { it.isDirectory } ?: error("Bundled index directory was not found")
            val manifest = JsonParser.parseString(File(root, "manifest.json").readText()).asJsonObject
            val count = manifest["count"].asInt
            val dimension = manifest["dimension"].asInt
            val rows = JsonParser.parseString(File(root, manifest["movies"].asString).readText()).asJsonArray
            val movies = rows.mapIndexed { position, element -> element.asJsonObject.toIndexMovie(position) }
            catalog = LocalCatalog(
                movies = movies,
                vectors = NumpyFloat16Reader.decode(
                    File(root, manifest["vectors"].asString).readBytes(),
                    count,
                    dimension
                ),
                dimension = dimension,
                byId = movies.associate { it.id to it.position }
            )
            moviesById = movies.associateBy { it.id }
        }

        private fun signal(id: Int, rating: Float): TasteSignal {
            val movie = moviesById[id] ?: error("Expected TMDB movie $id in the bundled catalog")
            return TasteSignal(
                movie = Movie(
                    id = movie.id,
                    title = movie.title,
                    releaseDate = movie.releaseDate,
                    voteAverage = movie.voteAverage.toDouble(),
                    genreIds = movie.genreIds.toList()
                ),
                rating = rating
            )
        }

        private fun JsonObject.toIndexMovie(position: Int): IndexMovie = IndexMovie(
            id = get("id").asInt,
            title = get("title").asString,
            releaseDate = get("release_date").asString,
            voteAverage = get("vote_average").asFloat,
            voteCount = get("vote_count").asInt,
            genreIds = getAsJsonArray("genre_ids").map { it.asInt }.toIntArray(),
            position = position
        )
    }
}
