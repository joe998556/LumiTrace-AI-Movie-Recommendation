package com.lumitrace.app.recommendation

import com.google.gson.JsonParser
import java.io.File
import kotlin.math.sqrt
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BundledIndexContractTest {
    @Test
    fun bundledIndexMatchesItsManifestAndContainsKnownTmdbSeeds() {
        val root = listOf(
            File("src/main/assets/lumitrace"),
            File("app/src/main/assets/lumitrace")
        ).firstOrNull { it.isDirectory } ?: error("Bundled index directory was not found")

        val manifest = JsonParser.parseString(File(root, "manifest.json").readText()).asJsonObject
        val count = manifest["count"].asInt
        val dimension = manifest["dimension"].asInt
        val movies = JsonParser.parseString(File(root, manifest["movies"].asString).readText()).asJsonArray
        val vectors = NumpyFloat16Reader.decode(
            File(root, manifest["vectors"].asString).readBytes(),
            count,
            dimension
        )

        assertEquals(30_000, count)
        assertEquals(768, dimension)
        assertEquals("AventIQ-AI/bert-movie-recommendation-system", manifest["model"].asString)
        assertEquals(count, movies.size())
        assertEquals(count * dimension, vectors.size)

        val ids = movies.map { it.asJsonObject["id"].asInt }.toSet()
        assertTrue(329865 in ids) // Arrival
        assertTrue(27205 in ids) // Inception

        var squaredNorm = 0f
        for (index in 0 until dimension) squaredNorm += vectors[index] * vectors[index]
        assertEquals(1f, sqrt(squaredNorm), 0.01f)
        assertTrue(File(root, manifest["data_notice"].asString).isFile)
    }
}
