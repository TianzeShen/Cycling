package com.cycling.cyclewise.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.ui.component.StaticScreen
import com.cycling.cyclewise.ui.theme.UiTokens

@Composable
fun ProfileScreen(
    modifier: Modifier = Modifier
) {
    StaticScreen(modifier = modifier) {
        item {
            ProfileHeader()
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StatCard("420", "points", Modifier.weight(1f))
                StatCard("8", "reports", Modifier.weight(1f))
                StatCard("37", "riders helped", Modifier.weight(1f))
            }
        }
        item {
            CardSection(title = "Badges") {
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    BadgeChip("Gap Spotter", Color(0xFF2F6F3E))
                    BadgeChip("Route Helper", Color(0xFF006A67))
                    BadgeChip("Validator", Color(0xFFB3261E))
                }
            }
        }
        item {
            CardSection(title = "Contribution impact") {
                ActivityLine("Reports submitted", "8")
                ActivityLine("Reports validated", "5")
                ActivityLine("Warnings generated", "14")
            }
        }
        item {
            CardSection(title = "Recent activity") {
                ActivityLine("Missing bike lane reported", "2h ago")
                ActivityLine("Unsafe crossing validated", "5h ago")
                ActivityLine("Route alert helped riders", "1d ago")
            }
        }
    }
}

@Composable
private fun ProfileHeader() {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(16.dp, RoundedCornerShape(8.dp), ambientColor = Color(0x332563EB), spotColor = Color(0x442563EB)),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier
                .background(
                    Brush.linearGradient(
                        listOf(Color.White, Color(0xFFEFF6FF), Color(0xFFE0F2FE))
                    )
                )
                .border(1.dp, Color.White.copy(alpha = 0.88f), RoundedCornerShape(8.dp))
                .padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "RIDER IMPACT",
                modifier = Modifier
                    .background(Color.White.copy(alpha = 0.66f), RoundedCornerShape(8.dp))
                    .border(1.dp, UiTokens.TechLine.copy(alpha = 0.72f), RoundedCornerShape(8.dp))
                    .padding(horizontal = 10.dp, vertical = 5.dp),
                color = MaterialTheme.colorScheme.primary,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                "Your cycling impact",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                "Track reports, validations, and the safety value your contributions create.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ImpactBadge("Level 4", "Contributor")
                ImpactBadge("92%", "Trusted")
            }
        }
    }
}

@Composable
private fun ImpactBadge(
    value: String,
    label: String
) {
    Column(
        modifier = Modifier
            .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.72f), RoundedCornerShape(8.dp))
            .border(1.dp, Color.White.copy(alpha = 0.86f), RoundedCornerShape(8.dp))
            .padding(horizontal = 12.dp, vertical = 9.dp)
            .width(112.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        Text(value, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.ExtraBold)
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun StatCard(
    value: String,
    label: String,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .shadow(10.dp, RoundedCornerShape(8.dp), ambientColor = Color(0x182563EB), spotColor = Color(0x262563EB)),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier
                .background(
                    Brush.verticalGradient(
                        listOf(Color.White, Color(0xFFEFF6FF).copy(alpha = 0.82f))
                    )
                )
                .border(1.dp, Color.White.copy(alpha = 0.82f), RoundedCornerShape(8.dp))
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                value,
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.primary
            )
            Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun CardSection(
    title: String,
    content: @Composable ColumnScope.() -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(8.dp, RoundedCornerShape(8.dp), ambientColor = Color(0x142563EB), spotColor = Color(0x202563EB)),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.92f)),
        shape = RoundedCornerShape(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            content()
        }
    }
}

@Composable
private fun BadgeChip(
    text: String,
    color: Color
) {
    Text(
        text = text,
        modifier = Modifier
            .background(
                Brush.horizontalGradient(
                    listOf(color.copy(alpha = 0.18f), Color.White.copy(alpha = 0.72f))
                ),
                RoundedCornerShape(8.dp)
            )
            .border(1.dp, color.copy(alpha = 0.22f), RoundedCornerShape(8.dp))
            .padding(horizontal = 12.dp, vertical = 8.dp),
        color = color,
        style = MaterialTheme.typography.labelLarge,
        fontWeight = FontWeight.SemiBold
    )
}

@Composable
private fun ActivityLine(
    label: String,
    value: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.horizontalGradient(
                    listOf(Color(0xFFF8FAFC), Color(0xFFEFF6FF).copy(alpha = 0.78f))
                ),
                RoundedCornerShape(8.dp)
            )
            .border(1.dp, UiTokens.TechLine.copy(alpha = 0.44f), RoundedCornerShape(8.dp))
            .padding(horizontal = 12.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontWeight = FontWeight.Medium)
    }
}
