package com.fraudshield.app.feature.onboarding

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*

enum class OnboardingDestination { Welcome, Introduction, Permissions }

/** One entry for the introductory flow; permission requests occur only on the rationale screen. */
@Composable
fun OnboardingRoute(destination: OnboardingDestination, locale: String, onLocale: (String) -> Unit,
    onStarted: () -> Unit, onPermissions: () -> Unit, onHome: () -> Unit) {
    when (destination) {
        OnboardingDestination.Welcome -> Welcome(locale, onLocale, onStarted)
        OnboardingDestination.Introduction -> Introduction(onPermissions)
        OnboardingDestination.Permissions -> PermissionWizard(onHome)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Welcome(locale: String, onLocale: (String) -> Unit, onStarted: () -> Unit) {
    ScreenList {
        item { Spacer(Modifier.height(24.dp)) }
        item {
            Icon(Icons.Outlined.Shield, stringResource(R.string.shield), tint = ShieldColors.Primary, modifier = Modifier.size(72.dp))
        }
        item {
            Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineLarge)
            Text(stringResource(R.string.promise), style = MaterialTheme.typography.titleLarge, color = ShieldColors.TextMid)
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.choose_language))
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("en" to "English", "hi" to "हिन्दी", "kn" to "ಕನ್ನಡ").forEach { (code, label) ->
                        FilterChip(locale == code, { onLocale(code) }, { Text(label) }, modifier = Modifier.heightIn(min = 48.dp))
                    }
                }
            }
        }
        item {
            ShieldCard {
                Text(stringResource(R.string.honest_scope))
                Text(stringResource(R.string.permission_choice), color = ShieldColors.TextMid)
            }
        }
        item { PrimaryButton(stringResource(R.string.get_started), onStarted) }
    }
}

@Composable
private fun Introduction(onPermissions: () -> Unit) {
    val model: OnboardingViewModel = hiltViewModel()
    val page by model.page.collectAsStateWithLifecycle()
    val titles = listOf(R.string.detect, R.string.investigate, R.string.protect)
    val bodies = listOf(R.string.detect_body, R.string.investigate_body, R.string.protect_body)
    ScreenList {
        item { SectionLabel(stringResource(R.string.step_of_three, page + 1)) }
        item {
            ShieldCard {
                Icon(Icons.Outlined.Shield, stringResource(R.string.shield), tint = ShieldColors.Primary, modifier = Modifier.size(48.dp))
                Text(stringResource(titles[page]), style = MaterialTheme.typography.headlineLarge)
                Text(stringResource(bodies[page]), color = ShieldColors.TextMid)
            }
        }
        if (page == 2) item {
            Notice(stringResource(R.string.privacy_promise))
        }
        item {
            PrimaryButton(stringResource(if (page == 2) R.string.enable_protection else R.string.continue_label),
                { if (page == 2) onPermissions() else model.next() })
        }
    }
}

