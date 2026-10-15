package com.websearch.tv.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.websearch.tv.ui.theme.AppColors

@Composable
fun PlatformBadge(
    platform: String,
    modifier: Modifier = Modifier
) {
    val color = AppColors.platformColor(platform)
    val icon = getPlatformIcon(platform)

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(50))
            .background(color.copy(alpha = 0.2f))
            .padding(horizontal = 10.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = platform,
            modifier = Modifier.size(14.dp),
            tint = color
        )
        Text(
            text = platform.replaceFirstChar { it.uppercase() },
            style = MaterialTheme.typography.labelSmall,
            color = color
        )
    }
}

private fun getPlatformIcon(platform: String): ImageVector {
    return when (platform.lowercase()) {
        "youtube" -> Icons.Default.PlayArrow
        "rumble" -> Icons.Default.PlayCircle
        "odysee" -> Icons.Default.Circle
        "podcast" -> Icons.Default.Mic
        "redbar" -> Icons.Default.Radio
        else -> Icons.Default.Tv
    }
}
