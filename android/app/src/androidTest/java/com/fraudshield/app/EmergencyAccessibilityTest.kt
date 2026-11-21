package com.fraudshield.app

import androidx.compose.ui.test.assertHasClickAction
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.platform.app.InstrumentationRegistry
import com.fraudshield.app.core.designsystem.FraudShieldTheme
import com.fraudshield.app.feature.emergency.EmergencyRoute
import org.junit.Rule
import org.junit.Test

class EmergencyAccessibilityTest {
    @get:Rule val compose = createComposeRule()

    @Test
    fun emergencyDialActionHasReadableTextAndClickSemantics() {
        val label = InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.call_1930_now)
        compose.setContent { FraudShieldTheme { EmergencyRoute() } }
        compose.onNodeWithText(label).assertIsDisplayed().assertHasClickAction()
    }
}
