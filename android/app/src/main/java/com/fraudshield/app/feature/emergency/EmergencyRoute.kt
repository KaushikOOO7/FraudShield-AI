package com.fraudshield.app.feature.emergency

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*

@Composable
fun EmergencyRoute() {
    val context = LocalContext.current
    var actionFailed by remember { mutableStateOf(false) }
    ScreenList {
        item { Notice(stringResource(R.string.emergency_calm)) }
        if (actionFailed) item { Notice(stringResource(R.string.external_action_failed), caution = true) }
        item {
            ShieldCard {
                Text(stringResource(R.string.act_promptly), style = MaterialTheme.typography.headlineLarge)
                Button(onClick = { actionFailed = !openExternal(context, "tel:1930") },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = ShieldColors.DangerSolid)) {
                    Text(stringResource(R.string.call_1930_now))
                }
                Text(stringResource(R.string.dialer_explanation), color = ShieldColors.TextMid)
            }
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.freeze_account))
                Text(stringResource(R.string.freeze_steps))
                SecondaryButton(stringResource(R.string.open_ncrp), { actionFailed = !openExternal(context, "https://cybercrime.gov.in/") })
            }
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.evidence_checklist))
                Text(stringResource(R.string.evidence_steps))
                Text(stringResource(R.string.never_credentials), color = ShieldColors.Caution)
            }
        }
        item {
            ShieldCard {
                SectionLabel(stringResource(R.string.loan_harassment))
                Text(stringResource(R.string.loan_steps))
                SecondaryButton(stringResource(R.string.open_sachet), { actionFailed = !openExternal(context, "https://sachet.rbi.org.in/") })
            }
        }
    }
}
