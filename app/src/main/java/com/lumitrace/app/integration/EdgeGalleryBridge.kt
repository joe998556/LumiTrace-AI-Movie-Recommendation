package com.lumitrace.app.integration

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import com.lumitrace.app.data.Movie
import com.lumitrace.app.ui.MovieJournalEntry

object EdgeGalleryBridge {
    const val PACKAGE_NAME = "com.google.ai.edge.gallery"
    const val PREFERRED_MODEL_NAME = "Gemma-4-E4B-it"

    enum class LaunchResult {
        Opened,
        StoreOpened,
        Unavailable
    }

    fun openRecommendationExplanation(
        context: Context,
        watchedMovies: List<Movie>,
        journalEntries: Map<Int, MovieJournalEntry>,
        recommendations: List<Movie>
    ): LaunchResult {
        val prompt = buildRecommendationPrompt(watchedMovies, journalEntries, recommendations)
        val uri = Uri.Builder()
            .scheme(PACKAGE_NAME)
            .authority("model")
            .appendPath("llm_chat")
            .appendPath(PREFERRED_MODEL_NAME)
            .appendQueryParameter("query", prompt)
            .build()
        val galleryIntent = Intent(Intent.ACTION_VIEW, uri).apply {
            setPackage(PACKAGE_NAME)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }

        return try {
            context.startActivity(galleryIntent)
            LaunchResult.Opened
        } catch (_: ActivityNotFoundException) {
            openStore(context)
        } catch (_: SecurityException) {
            LaunchResult.Unavailable
        }
    }

    fun isInstalled(context: Context): Boolean {
        return context.packageManager.getLaunchIntentForPackage(PACKAGE_NAME) != null
    }

    fun buildRecommendationPrompt(
        watchedMovies: List<Movie>,
        journalEntries: Map<Int, MovieJournalEntry>,
        recommendations: List<Movie>
    ): String {
        val watched = watchedMovies
            .sortedByDescending { journalEntries[it.id]?.rating ?: 0f }
            .take(MAX_WATCHED_CONTEXT)
            .joinToString("\n") { movie ->
                val score = journalEntries[movie.id]?.rating?.takeIf { it > 0f }
                "- ${movie.title}${score?.let { " (${formatScore(it)}/10)" }.orEmpty()}"
            }
            .ifBlank { "- No watched films were supplied." }

        val matches = recommendations.take(MAX_RECOMMENDATION_CONTEXT).joinToString("\n") { movie ->
            val reason = movie.reason.orEmpty().trim().take(MAX_REASON_LENGTH)
            val overview = movie.overview.trim().take(MAX_OVERVIEW_LENGTH)
            buildString {
                append("- ${movie.title}")
                if (reason.isNotBlank()) append(" | LumiTrace signal: $reason")
                if (overview.isNotBlank()) append(" | Plot: $overview")
            }
        }.ifBlank { "- No recommendation candidates were supplied." }

        return """
            You are the private on-device explanation layer for LumiTrace. Explain why the supplied recommendations fit the user's movie taste.

            Watched and rated films:
            $watched

            LumiTrace recommendations:
            $matches

            Reply in the user's language. Rank the best five choices, give one concise reason for each, and mention meaningful contrasts when helpful. Use only the supplied titles, ratings, plot text, and LumiTrace signals. Do not invent actors, directors, awards, availability, or facts that are not present. State clearly when the supplied evidence is insufficient.
        """.trimIndent()
    }

    private fun openStore(context: Context): LaunchResult {
        val marketIntent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse("market://details?id=$PACKAGE_NAME")
        ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        return try {
            context.startActivity(marketIntent)
            LaunchResult.StoreOpened
        } catch (_: ActivityNotFoundException) {
            val webIntent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse("https://play.google.com/store/apps/details?id=$PACKAGE_NAME")
            ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            try {
                context.startActivity(webIntent)
                LaunchResult.StoreOpened
            } catch (_: ActivityNotFoundException) {
                LaunchResult.Unavailable
            }
        }
    }

    private fun formatScore(value: Float): String {
        return if (value % 1f == 0f) value.toInt().toString() else "%.1f".format(value)
    }

    private const val MAX_WATCHED_CONTEXT = 12
    private const val MAX_RECOMMENDATION_CONTEXT = 8
    private const val MAX_REASON_LENGTH = 180
    private const val MAX_OVERVIEW_LENGTH = 220
}
