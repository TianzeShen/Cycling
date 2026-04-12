package com.cycling.cyclewise.ui.screen

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.cycling.cyclewise.ui.component.InfoItem
import com.cycling.cyclewise.ui.component.PageIntro
import com.cycling.cyclewise.ui.component.ScoreSummary
import com.cycling.cyclewise.ui.component.StaticScreen

@Composable
fun ProfileScreen(
    modifier: Modifier = Modifier
) {
    StaticScreen(modifier = modifier) {
        item {
            PageIntro(
                title = "Your cycling impact",
                body = "Profile, reward, and contribution data will be connected after user APIs are available."
            )
        }
        item {
            ScoreSummary(score = 64, label = "Contribution progress")
        }
        item {
            InfoItem(
                title = "Points",
                body = "420 points from reports and community validations."
            )
        }
        item {
            InfoItem(
                title = "Badges",
                body = "Gap Spotter, Route Helper, Community Validator."
            )
        }
        item {
            InfoItem(
                title = "Impact",
                body = "8 reports submitted, 5 validated, 37 cyclists informed."
            )
        }
    }
}
