package com.cycling.cyclewise.ui.component.map

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.data.model.PlaceCandidate
import com.cycling.cyclewise.ui.theme.UiTokens

@Composable
fun LocationSearchOverlay(
    startPoint: String,
    onStartPointChange: (String) -> Unit,
    startSuggestions: List<PlaceCandidate>,
    onStartSuggestionClick: (PlaceCandidate) -> Unit,
    destination: String,
    onDestinationChange: (String) -> Unit,
    destinationSuggestions: List<PlaceCandidate>,
    onDestinationSuggestionClick: (PlaceCandidate) -> Unit,
    locationStatus: String,
    onUseCurrentLocation: () -> Unit,
    onEvaluate: () -> Unit,
    isEvaluating: Boolean,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .shadow(22.dp, RoundedCornerShape(8.dp), ambientColor = Color(0x552563EB), spotColor = Color(0x332563EB)),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.78f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(
                    Brush.verticalGradient(
                        listOf(
                            Color.White.copy(alpha = 0.92f),
                            Color(0xFFEFF6FF).copy(alpha = 0.76f)
                        )
                    )
                )
                .border(
                    1.dp,
                    Brush.linearGradient(
                        listOf(
                            Color.White.copy(alpha = 0.95f),
                            Color(0xFF93C5FD).copy(alpha = 0.58f)
                        )
                    ),
                    RoundedCornerShape(8.dp)
                )
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "AI route decision",
                    color = MaterialTheme.colorScheme.onSurface,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.ExtraBold
                )
                Text(
                    "OSM live",
                    modifier = Modifier
                        .background(Color.White.copy(alpha = 0.58f), RoundedCornerShape(8.dp))
                        .border(1.dp, UiTokens.TechLine.copy(alpha = 0.75f), RoundedCornerShape(8.dp))
                        .padding(horizontal = 8.dp, vertical = 4.dp),
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold
                )
            }
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(3.dp)
                    .background(
                        Brush.horizontalGradient(
                            listOf(Color(0xFF2563EB), Color(0xFF0EA5E9), Color(0xFF93C5FD))
                        ),
                        RoundedCornerShape(8.dp)
                    )
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                CompactSearchField(
                    value = startPoint,
                    onValueChange = onStartPointChange,
                    placeholder = "Start point",
                    dotColor = Color(0xFF2F80ED),
                    keyboardImeAction = ImeAction.Next,
                    modifier = Modifier.weight(1f)
                )
                LocateButton(onClick = onUseCurrentLocation)
            }
            SuggestionList(
                suggestions = startSuggestions,
                onSuggestionClick = onStartSuggestionClick
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                CompactSearchField(
                    value = destination,
                    onValueChange = onDestinationChange,
                    placeholder = "Destination",
                    dotColor = Color(0xFFB96AF7),
                    keyboardImeAction = ImeAction.Done,
                    modifier = Modifier.weight(1f)
                )
                GradientActionButton(
                    modifier = Modifier
                        .height(48.dp)
                        .width(126.dp),
                    onClick = onEvaluate,
                    enabled = !isEvaluating,
                    text = if (isEvaluating) "..." else "Evaluate"
                )
            }
            SuggestionList(
                suggestions = destinationSuggestions,
                onSuggestionClick = onDestinationSuggestionClick
            )
            Text(
                text = locationStatus,
                modifier = Modifier
                    .background(Color.White.copy(alpha = 0.08f), RoundedCornerShape(8.dp))
                    .border(1.dp, UiTokens.TechLine.copy(alpha = 0.72f), RoundedCornerShape(8.dp))
                    .padding(horizontal = 10.dp, vertical = 5.dp),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun CompactSearchField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    dotColor: Color,
    keyboardImeAction: ImeAction,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .height(48.dp)
            .background(Color.White.copy(alpha = 0.64f), RoundedCornerShape(8.dp))
            .border(1.dp, Color.White.copy(alpha = 0.92f), RoundedCornerShape(8.dp))
            .padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .border(2.dp, dotColor, RoundedCornerShape(8.dp))
        )
        Box(Modifier.width(10.dp))
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.weight(1f),
            singleLine = true,
            textStyle = MaterialTheme.typography.bodyLarge,
            keyboardOptions = KeyboardOptions(imeAction = keyboardImeAction),
            decorationBox = { innerTextField ->
                Box(contentAlignment = Alignment.CenterStart) {
                    if (value.isEmpty()) {
                        Text(
                            text = placeholder,
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    innerTextField()
                }
            }
        )
    }
}

@Composable
private fun LocateButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.92f else 1f, label = "locate_scale")
    IconButton(
        onClick = onClick,
        modifier = modifier
            .size(48.dp)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .shadow(14.dp, RoundedCornerShape(24.dp), ambientColor = Color(0x332563EB), spotColor = Color(0x442563EB))
            .background(Color.White.copy(alpha = 0.82f), RoundedCornerShape(24.dp))
            .border(1.dp, UiTokens.TechLine.copy(alpha = 0.82f), RoundedCornerShape(24.dp)),
        interactionSource = interactionSource
    ) {
        LocateIcon()
    }
}

@Composable
private fun LocateIcon(
    modifier: Modifier = Modifier
) {
    val color = MaterialTheme.colorScheme.onSurface
    Canvas(modifier = modifier.size(22.dp)) {
        val stroke = 2.2.dp.toPx()
        drawCircle(
            color = color,
            radius = size.minDimension * 0.28f,
            style = androidx.compose.ui.graphics.drawscope.Stroke(width = stroke)
        )
        drawLine(
            color = color,
            start = center.copy(x = 0f),
            end = center.copy(x = size.width * 0.24f),
            strokeWidth = stroke,
            cap = StrokeCap.Round
        )
        drawLine(
            color = color,
            start = center.copy(x = size.width * 0.76f),
            end = center.copy(x = size.width),
            strokeWidth = stroke,
            cap = StrokeCap.Round
        )
        drawLine(
            color = color,
            start = center.copy(y = 0f),
            end = center.copy(y = size.height * 0.24f),
            strokeWidth = stroke,
            cap = StrokeCap.Round
        )
        drawLine(
            color = color,
            start = center.copy(y = size.height * 0.76f),
            end = center.copy(y = size.height),
            strokeWidth = stroke,
            cap = StrokeCap.Round
        )
    }
}

@Composable
private fun SuggestionList(
    suggestions: List<PlaceCandidate>,
    onSuggestionClick: (PlaceCandidate) -> Unit,
    modifier: Modifier = Modifier
) {
    if (suggestions.isNotEmpty()) {
        Column(
            modifier = modifier
                .fillMaxWidth()
                .shadow(12.dp, RoundedCornerShape(8.dp), ambientColor = Color(0x222563EB), spotColor = Color(0x332563EB))
                .background(Color.White.copy(alpha = 0.92f), RoundedCornerShape(8.dp))
                .border(1.dp, UiTokens.TechLine.copy(alpha = 0.70f), RoundedCornerShape(8.dp))
                .padding(vertical = 4.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            suggestions.forEach { suggestion ->
                Text(
                    text = suggestion.displayName,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onSuggestionClick(suggestion) }
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
        }
    }
}

@Composable
private fun GradientActionButton(
    text: String,
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.96f else 1f, label = "evaluate_scale")

    Box(
        modifier = modifier
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                alpha = if (enabled) 1f else 0.62f
            }
            .shadow(14.dp, RoundedCornerShape(8.dp), ambientColor = Color(0x552563EB), spotColor = Color(0x662563EB))
            .background(
                Brush.horizontalGradient(
                    listOf(Color(0xFF2563EB), Color(0xFF0EA5E9), Color(0xFF38BDF8))
                ),
                RoundedCornerShape(8.dp)
            )
            .clickable(
                enabled = enabled,
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text,
            color = Color.White,
            fontWeight = FontWeight.ExtraBold,
            style = MaterialTheme.typography.labelLarge
        )
    }
}
