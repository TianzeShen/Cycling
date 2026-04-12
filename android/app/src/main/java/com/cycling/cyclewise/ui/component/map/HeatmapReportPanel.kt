package com.cycling.cyclewise.ui.component.map

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.data.model.HeatmapReport
import com.cycling.cyclewise.data.model.RiskLevel

@Composable
fun HeatmapReportPanel(
    reports: List<HeatmapReport>,
    selectedRisk: RiskLevel?,
    onRiskChange: (RiskLevel?) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            RiskChip("All", Color(0xFF2563EB), selected = selectedRisk == null) {
                onRiskChange(null)
            }
            RiskLevel.entries.forEach { risk ->
                RiskChip(
                    label = risk.label,
                    color = risk.toComposeColor(),
                    selected = selectedRisk == risk
                ) {
                    onRiskChange(risk)
                }
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "Recent Reports",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "${reports.size} issues",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        if (reports.isEmpty()) {
            Text(
                text = "No reports match this filter.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        reports.forEach { report ->
            ReportCard(report = report)
        }
    }
}

@Composable
private fun RiskChip(
    label: String,
    color: Color,
    selected: Boolean,
    onClick: () -> Unit
) {
    Text(
        text = label,
        modifier = Modifier
            .background(
                if (selected) color else MaterialTheme.colorScheme.surfaceContainer,
                RoundedCornerShape(8.dp)
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
        color = if (selected) Color.White else MaterialTheme.colorScheme.onSurfaceVariant,
        style = MaterialTheme.typography.labelLarge,
        fontWeight = FontWeight.SemiBold
    )
}

@Composable
private fun ReportCard(
    report: HeatmapReport,
    modifier: Modifier = Modifier
) {
    val severityColor = report.riskLevel.toComposeColor()
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        text = report.title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = report.locationName,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Text(
                    text = report.status,
                    modifier = Modifier
                        .background(Color(0xFFE8F1FF), RoundedCornerShape(8.dp))
                        .padding(horizontal = 10.dp, vertical = 5.dp),
                    color = Color(0xFF2563EB),
                    style = MaterialTheme.typography.labelMedium
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    text = "${report.votes} votes",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = report.timeAgo,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = report.riskLevel.label.lowercase(),
                    modifier = Modifier
                        .background(severityColor.copy(alpha = 0.16f), RoundedCornerShape(8.dp))
                        .padding(horizontal = 8.dp, vertical = 3.dp),
                    color = severityColor,
                    style = MaterialTheme.typography.labelMedium
                )
            }
        }
    }
}

private fun RiskLevel.toComposeColor(): Color {
    return when (this) {
        RiskLevel.High -> Color(0xFFEF4444)
        RiskLevel.Medium -> Color(0xFFF98046)
        RiskLevel.Low -> Color(0xFFF2C94C)
    }
}
