package com.lumitrace.app

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

/** A zero-network entry point to the on-device Tonight flow. */
class MovieWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        appWidgetIds.forEach { widgetId ->
            val openTonight = Intent(context, MainActivity::class.java).apply {
                action = ACTION_OPEN_TONIGHT
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
            val pendingIntent = PendingIntent.getActivity(
                context,
                widgetId,
                openTonight,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            val views = RemoteViews(context.packageName, R.layout.widget_tonight).apply {
                setOnClickPendingIntent(R.id.widget_open_tonight, pendingIntent)
            }
            appWidgetManager.updateAppWidget(widgetId, views)
        }
    }

    companion object {
        const val ACTION_OPEN_TONIGHT = "com.lumitrace.app.OPEN_TONIGHT"
    }
}
