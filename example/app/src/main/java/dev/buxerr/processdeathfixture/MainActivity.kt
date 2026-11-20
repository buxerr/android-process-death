package dev.buxerr.processdeathfixture

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.util.UUID

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val marker = rememberSaveable { UUID.randomUUID().toString() }
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    Column(modifier = Modifier.padding(24.dp)) {
                        Text("Compose process-death fixture", style = MaterialTheme.typography.titleLarge)
                        Text("Saved marker: $marker", modifier = Modifier.padding(top = 16.dp))
                        Text("Use background-kill mode, then compare the captured marker.", modifier = Modifier.padding(top = 8.dp))
                    }
                }
            }
        }
    }
}
