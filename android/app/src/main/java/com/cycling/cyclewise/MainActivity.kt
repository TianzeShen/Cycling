package com.cycling.cyclewise

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.cycling.cyclewise.ui.navigation.CycleWiseApp
import com.cycling.cyclewise.ui.theme.CycleWiseTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            CycleWiseTheme {
                CycleWiseApp()
            }
        }
    }
}
