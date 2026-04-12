package com.cycling.cyclewise.ui.component.map

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.data.model.PlaceCandidate

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
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedTextField(
                value = startPoint,
                onValueChange = onStartPointChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Start point") },
                placeholder = { Text("Current location or search start") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next)
            )
            SuggestionList(
                suggestions = startSuggestions,
                onSuggestionClick = onStartSuggestionClick
            )
            OutlinedTextField(
                value = destination,
                onValueChange = onDestinationChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Destination") },
                placeholder = { Text("Search a place") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done)
            )
            SuggestionList(
                suggestions = destinationSuggestions,
                onSuggestionClick = onDestinationSuggestionClick
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                FilledTonalButton(
                    modifier = Modifier.weight(1f),
                    onClick = onUseCurrentLocation
                ) {
                    Text("Locate me")
                }
                Button(
                    modifier = Modifier.weight(1f),
                    onClick = onEvaluate,
                    enabled = !isEvaluating
                ) {
                    Text(if (isEvaluating) "Evaluating..." else "Evaluate")
                }
            }
            Text(
                text = locationStatus,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun SuggestionList(
    suggestions: List<PlaceCandidate>,
    onSuggestionClick: (PlaceCandidate) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        suggestions.forEach { suggestion ->
            Text(
                text = suggestion.displayName,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onSuggestionClick(suggestion) }
                    .padding(horizontal = 8.dp, vertical = 6.dp),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
