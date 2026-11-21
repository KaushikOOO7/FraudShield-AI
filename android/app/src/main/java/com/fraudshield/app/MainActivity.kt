package com.fraudshield.app

import android.os.Bundle
import android.content.Intent
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import com.fraudshield.app.core.designsystem.FraudShieldTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.MutableStateFlow
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@AndroidEntryPoint
class MainActivity : AppCompatActivity() {
    private val pendingCase = MutableStateFlow<String?>(null)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        readCase(intent)
        setContent {
            val caseId by pendingCase.collectAsStateWithLifecycle()
            FraudShieldTheme { FraudShieldApp(caseId) { pendingCase.value = null } }
        }
    }
    override fun onNewIntent(intent: Intent) { super.onNewIntent(intent); setIntent(intent); readCase(intent) }
    private fun readCase(intent: Intent?) {
        pendingCase.value = intent?.getStringExtra(EXTRA_CASE_ID)?.takeIf {
            it.isNotBlank() && it.length <= 256 && it.none { character -> character.isISOControl() }
        }
    }
    companion object { const val EXTRA_CASE_ID = "fraudshield_case_id" }
}
