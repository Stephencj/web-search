package com.websearch.tv.util

import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.TimeUnit

fun formatRelativeDate(dateString: String): String {
    val formats = listOf(
        "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
        "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",
        "yyyy-MM-dd'T'HH:mm:ss'Z'",
        "yyyy-MM-dd'T'HH:mm:ss",
        "yyyy-MM-dd"
    )

    var date: Date? = null
    for (format in formats) {
        try {
            val sdf = SimpleDateFormat(format, Locale.US)
            sdf.timeZone = TimeZone.getTimeZone("UTC")
            date = sdf.parse(dateString)
            if (date != null) break
        } catch (e: Exception) {
            continue
        }
    }

    if (date == null) return dateString

    val now = Date()
    val diffMillis = now.time - date.time

    val seconds = TimeUnit.MILLISECONDS.toSeconds(diffMillis)
    val minutes = TimeUnit.MILLISECONDS.toMinutes(diffMillis)
    val hours = TimeUnit.MILLISECONDS.toHours(diffMillis)
    val days = TimeUnit.MILLISECONDS.toDays(diffMillis)

    return when {
        seconds < 60 -> "just now"
        minutes < 60 -> "${minutes}m ago"
        hours < 24 -> "${hours}h ago"
        days < 7 -> "${days}d ago"
        days < 30 -> "${days / 7}w ago"
        days < 365 -> "${days / 30}mo ago"
        else -> "${days / 365}y ago"
    }
}

fun formatDuration(seconds: Int): String {
    val hours = seconds / 3600
    val minutes = (seconds % 3600) / 60
    val secs = seconds % 60

    return if (hours > 0) {
        String.format("%d:%02d:%02d", hours, minutes, secs)
    } else {
        String.format("%d:%02d", minutes, secs)
    }
}

fun formatViewCount(views: Int): String {
    return when {
        views >= 1_000_000 -> String.format("%.1fM views", views / 1_000_000.0)
        views >= 1_000 -> String.format("%.1fK views", views / 1_000.0)
        else -> "$views views"
    }
}
