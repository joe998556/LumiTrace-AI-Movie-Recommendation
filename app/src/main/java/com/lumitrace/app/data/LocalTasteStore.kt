package com.lumitrace.app.data

import android.content.SharedPreferences
import com.google.gson.Gson

/** Stores non-secret taste data locally. The caller supplies encrypted preferences. */
class LocalTasteStore(
    private val prefs: SharedPreferences,
    private val gson: Gson
) {
    fun load(legacyEntries: List<LibraryEntry>): LocalTasteLibrary {
        val saved = prefs.getString(KEY_STATE, null)
        val restored = saved?.let {
            runCatching { gson.fromJson(it, LocalTasteState::class.java) }.getOrNull()
        }
        if (restored != null) {
            return runCatching { LocalTasteLibrary(restored) }.getOrNull()
                ?: LocalTasteLibrary(stateFromLegacy(legacyEntries))
        }
        return LocalTasteLibrary(stateFromLegacy(legacyEntries))
    }

    fun save(library: LocalTasteLibrary) {
        prefs.edit().putString(KEY_STATE, gson.toJson(library.snapshot())).apply()
    }

    fun exportJson(library: LocalTasteLibrary): String = gson.toJson(library.snapshot())

    fun importJson(json: String): LocalTasteLibrary {
        val state = runCatching { gson.fromJson(json, LocalTasteState::class.java) }.getOrNull()
            ?: error("This is not a LumiTrace backup.")
        return LocalTasteLibrary(state)
    }

    private fun stateFromLegacy(entries: List<LibraryEntry>): LocalTasteState {
        val profile = ViewingProfile(id = "default", name = "Default", entries = entries)
        return LocalTasteState(activeProfileId = profile.id, profiles = listOf(profile))
    }

    private companion object {
        const val KEY_STATE = "local_taste_state_v1"
    }
}
