package com.lumitrace.app.recommendation

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.lumitrace.app.data.Movie
import java.io.File

internal object BundledTestCatalog {
    val catalog: LocalCatalog by lazy { loadCatalog() }
    val moviesById: Map<Int, IndexMovie> by lazy { catalog.movies.associateBy { it.id } }

    fun signal(id: Int, rating: Float): TasteSignal {
        val movie = moviesById[id] ?: error("Expected TMDB movie $id in the bundled catalog")
        return TasteSignal(movie.toMovie(), rating)
    }

    fun movie(id: Int): Movie = moviesById[id]?.toMovie()
        ?: error("Expected TMDB movie $id in the bundled catalog")

    private fun loadCatalog(): LocalCatalog {
        val root = listOf(
            File("src/main/assets/lumitrace"),
            File("app/src/main/assets/lumitrace")
        ).firstOrNull { it.isDirectory } ?: error("Bundled index directory was not found")
        val manifest = JsonParser.parseString(File(root, "manifest.json").readText()).asJsonObject
        val count = manifest["count"].asInt
        val dimension = manifest["dimension"].asInt
        val rows = JsonParser.parseString(File(root, manifest["movies"].asString).readText()).asJsonArray
        val movies = rows.mapIndexed { position, element -> element.asJsonObject.toIndexMovie(position) }
        return LocalCatalog(
            movies = movies,
            vectors = NumpyFloat16Reader.decode(
                File(root, manifest["vectors"].asString).readBytes(),
                count,
                dimension
            ),
            dimension = dimension,
            byId = movies.associate { it.id to it.position }
        )
    }

    private fun IndexMovie.toMovie(): Movie = Movie(
        id = id,
        title = title,
        releaseDate = releaseDate,
        voteAverage = voteAverage.toDouble(),
        genreIds = genreIds.toList()
    )

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
