package com.cycling.cyclewise.ui.screen

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.ui.component.StaticScreen
import com.cycling.cyclewise.ui.theme.UiTokens

@Composable
fun ReportIssueScreen(
    modifier: Modifier = Modifier
) {
    StaticScreen(modifier = modifier) {
        item {
            ReportHeader()
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                LocationCard()
                SectionCard(title = "Issue type") {
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        ReportChip("Missing bike lane", selected = true)
                        ReportChip("Disconnected lane")
                        ReportChip("Unsafe crossing")
                        ReportChip("Poor visibility")
                        ReportChip("High traffic")
                    }
                }
            }
        }
        item {
            SectionCard(title = "Risk priority") {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SeverityChip("High", Color(0xFFEF4444), selected = true, modifier = Modifier.weight(1f))
                    SeverityChip("Medium", Color(0xFFF98046), modifier = Modifier.weight(1f))
                    SeverityChip("Low", Color(0xFFF2C94C), modifier = Modifier.weight(1f))
                }
            }
        }
        item {
            SectionCard(title = "Report details") {
                InfoLine("Status", "Ready to submit")
                InfoLine("Context", "Route and timestamp will be attached")
                InfoLine("Offline", "Saved locally if connection is unavailable")
            }
        }
        item {
            PremiumActionButton(
                text = "Create report",
                onClick = {},
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            )
        }
    }
}

@Composable
private fun ReportHeader() {
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
                text = "AI SAFETY REPORT",
                modifier = Modifier
                    .background(Color.White.copy(alpha = 0.66f), RoundedCornerShape(8.dp))
                    .border(1.dp, UiTokens.TechLine.copy(alpha = 0.72f), RoundedCornerShape(8.dp))
                    .padding(horizontal = 10.dp, vertical = 5.dp),
                color = MaterialTheme.colorScheme.primary,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Report a cycling issue",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = "Mark unsafe infrastructure so future riders can make safer decisions.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                HeroStat("1 tap", "capture")
                HeroStat("GPS", "attached")
                HeroStat("AI", "suggested")
            }
        }
    }
}

@Composable
private fun HeroStat(
    value: String,
    label: String
) {
    Column(
        modifier = Modifier
            .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.72f), RoundedCornerShape(8.dp))
            .border(1.dp, Color.White.copy(alpha = 0.86f), RoundedCornerShape(8.dp))
            .padding(horizontal = 10.dp, vertical = 8.dp)
            .width(82.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        Text(value, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.ExtraBold)
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun LocationCard() {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(10.dp, RoundedCornerShape(8.dp), ambientColor = Color(0x182563EB), spotColor = Color(0x222563EB)),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.90f)),
        shape = RoundedCornerShape(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        "Issue location",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        "-37.9114, 145.1340",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Text(
                    "Current",
                    modifier = Modifier
                        .background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(8.dp))
                        .border(1.dp, UiTokens.TechLine, RoundedCornerShape(8.dp))
                        .padding(horizontal = 10.dp, vertical = 6.dp),
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.labelLarge
                )
            }
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(130.dp)
                    .background(
                        Brush.linearGradient(
                            listOf(Color(0xFFEFF6FF), Color.White, Color(0xFFE0F2FE))
                        ),
                        RoundedCornerShape(8.dp)
                    )
                    .border(1.dp, UiTokens.TechLine.copy(alpha = 0.62f), RoundedCornerShape(8.dp)),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        "Clayton risk point",
                        color = MaterialTheme.colorScheme.onSurface,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        "GPS marker and report context",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }
    }
}

@Composable
private fun SectionCard(
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
private fun ReportChip(
    text: String,
    selected: Boolean = false
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.96f else 1f, label = "report_chip_scale")
    Text(
        text = text,
        modifier = Modifier
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .background(
                if (selected) {
                    Brush.horizontalGradient(listOf(Color(0xFF2563EB), Color(0xFF0EA5E9)))
                } else {
                    Brush.horizontalGradient(listOf(Color.White.copy(alpha = 0.88f), Color(0xFFEFF6FF).copy(alpha = 0.72f)))
                },
                RoundedCornerShape(8.dp)
            )
            .border(
                1.dp,
                if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant,
                RoundedCornerShape(8.dp)
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = {}
            )
            .padding(horizontal = 12.dp, vertical = 8.dp),
        color = if (selected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
        style = MaterialTheme.typography.labelLarge
    )
}

@Composable
private fun SeverityChip(
    text: String,
    color: Color,
    selected: Boolean = false,
    modifier: Modifier = Modifier
) {
    Text(
        text = text,
        modifier = modifier
            .background(
                Brush.verticalGradient(
                    listOf(
                        color.copy(alpha = if (selected) 0.24f else 0.10f),
                        Color.White.copy(alpha = 0.72f)
                    )
                ),
                RoundedCornerShape(8.dp)
            )
            .border(1.dp, color.copy(alpha = if (selected) 0.80f else 0.25f), RoundedCornerShape(8.dp))
            .padding(vertical = 10.dp, horizontal = 8.dp),
        color = color,
        style = MaterialTheme.typography.labelLarge,
        fontWeight = FontWeight.SemiBold
    )
}

@Composable
private fun InfoLine(
    label: String,
    value: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun PremiumActionButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.97f else 1f, label = "report_action_scale")

    Box(
        modifier = modifier
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .shadow(14.dp, RoundedCornerShape(8.dp), ambientColor = Color(0x442563EB), spotColor = Color(0x552563EB))
            .background(
                Brush.horizontalGradient(listOf(Color(0xFF2563EB), Color(0xFF0EA5E9), Color(0xFF38BDF8))),
                RoundedCornerShape(8.dp)
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Text(text, color = Color.White, fontWeight = FontWeight.ExtraBold)
    }
}
