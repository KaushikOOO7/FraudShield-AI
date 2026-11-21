package com.fraudshield.app

import android.net.Uri
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.ui.Alignment
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.QrCodeScanner
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.fraudshield.app.core.designsystem.Notice
import com.fraudshield.app.feature.alerts.AlertsDestination
import com.fraudshield.app.feature.alerts.AlertsRoute
import com.fraudshield.app.feature.assistant.AssistantRoute
import com.fraudshield.app.feature.emergency.EmergencyRoute
import com.fraudshield.app.feature.family.FamilyRoute
import com.fraudshield.app.feature.history.HistoryRoute
import com.fraudshield.app.feature.home.HomeRoute
import com.fraudshield.app.feature.onboarding.OnboardingDestination
import com.fraudshield.app.feature.onboarding.OnboardingRoute
import com.fraudshield.app.feature.scan.ScanRoute
import com.fraudshield.app.feature.settings.SettingsRoute
import com.fraudshield.app.feature.trends.TrendsRoute
import com.fraudshield.app.navigation.Destination

@Composable
fun FraudShieldApp(pendingCaseId: String? = null, onCaseConsumed: () -> Unit = {}) {
    val model: AppViewModel = hiltViewModel()
    val language by model.locale.collectAsStateWithLifecycle()
    val protection by model.protection.collectAsStateWithLifecycle()
    val health by model.health.collectAsStateWithLifecycle()
    val erasureEpoch by model.erasureEpoch.collectAsStateWithLifecycle()
    val owner = LocalLifecycleOwner.current
    LaunchedEffect(owner, model) {
        owner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (isActive) { model.refreshHealth(); delay(5_000) }
        }
    }
    LaunchedEffect(language) {
        val requested = LocaleListCompat.forLanguageTags(language)
        if (AppCompatDelegate.getApplicationLocales() != requested) {
            AppCompatDelegate.setApplicationLocales(requested)
        }
    }
    AppNavigation(language, model::setLocale, protection.onboardingComplete, health.revoked.isNotEmpty(), pendingCaseId, onCaseConsumed,model::selectCase,erasureEpoch)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AppNavigation(locale: String, onLocale: (String) -> Unit, onboardingComplete: Boolean,
    permissionRevoked: Boolean, pendingCaseId: String?, onCaseConsumed: () -> Unit,onSelectCase:(String?)->Unit,erasureEpoch:Int) {
    val nav = rememberNavController()
    LaunchedEffect(erasureEpoch){if(erasureEpoch>0)nav.navigate("welcome"){popUpTo(nav.graph.id)}}
    val start = remember { if (onboardingComplete) Destination.Home.route else Destination.Welcome.route }
    var previousCompletion by remember{mutableStateOf(onboardingComplete)}
    LaunchedEffect(onboardingComplete){if(previousCompletion&&!onboardingComplete){nav.navigate("welcome"){popUpTo(nav.graph.id)}};previousCompletion=onboardingComplete}
    val entry by nav.currentBackStackEntryAsState()
    val current = Destination.entries.firstOrNull { it.route == entry?.destination?.route } ?: Destination.Welcome
    val largeType = LocalConfiguration.current.fontScale >= 1.5f
    val navigate: (String) -> Unit = { route -> nav.navigate(route) { launchSingleTop = true } }
    val openCase: (String) -> Unit = { id -> onSelectCase(id);navigate("alert/${Uri.encode(id)}") }
    val home: () -> Unit = {
        nav.navigate(Destination.Home.route) {
            popUpTo(nav.graph.id)
            launchSingleTop = true
        }
    }
    LaunchedEffect(pendingCaseId) {
        pendingCaseId?.let { home(); openCase(it); onCaseConsumed() }
    }
    Scaffold(
        topBar = {
            Column {
                if (current != Destination.Welcome) {
                    Surface{Row(Modifier.fillMaxWidth().padding(horizontal=20.dp,vertical=12.dp),verticalAlignment=Alignment.CenterVertically){
                        if (!current.bottomTab) IconButton(onClick = { nav.popBackStack() }) {
                            Icon(Icons.AutoMirrored.Outlined.ArrowBack, stringResource(R.string.back))
                        }
                        Text(stringResource(current.title),style=MaterialTheme.typography.titleLarge,modifier=Modifier.weight(1f))
                    }}
                }
                if (BuildConfig.DEBUG && BuildConfig.DEMO_MODE) Notice(stringResource(R.string.demo_banner), caution = true)
                if (permissionRevoked) {
                    Notice(stringResource(R.string.permission_revoked), caution = true)
                    TextButton({ navigate("permissions") }) { Text(stringResource(R.string.reenable)) }
                }
            }
        },
        bottomBar = {
            if (current.bottomTab) {
                NavigationBar(Modifier.heightIn(min = if (largeType) 128.dp else 80.dp)) {
                    val tabs = listOf(Destination.Home to Icons.Outlined.Home, Destination.Scan to Icons.Outlined.QrCodeScanner,
                        Destination.History to Icons.Outlined.History, Destination.Settings to Icons.Outlined.Settings)
                    tabs.forEach { (destination, icon) ->
                        val label = stringResource(destination.title)
                        NavigationBarItem(selected = current == destination, onClick = {
                            nav.navigate(if (destination == Destination.Scan) "scan?tab=text" else destination.route) {
                                popUpTo(Destination.Home.route) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        }, icon = { Icon(icon, label) }, label = { Text(label) })
                    }
                }
            }
        },
    ) { padding ->
        NavHost(nav, start, Modifier.padding(padding)) {
            composable(Destination.Welcome.route) {
                OnboardingRoute(OnboardingDestination.Welcome, locale, onLocale, { navigate("onboarding") }, { navigate("permissions") }, home)
            }
            composable(Destination.Onboarding.route) {
                OnboardingRoute(OnboardingDestination.Introduction, locale, onLocale, { navigate("onboarding") }, { navigate("permissions") }, home)
            }
            composable(Destination.Permissions.route) {
                OnboardingRoute(OnboardingDestination.Permissions, locale, onLocale, { navigate("onboarding") }, { navigate("permissions") }, home)
            }
            composable(Destination.Home.route) { HomeRoute(navigate, openCase) }
            composable(Destination.Alert.route, arguments = listOf(navArgument("caseId") { type = NavType.StringType })) {
                AlertsRoute(AlertsDestination.Detail, { navigate("graph/${Uri.encode(it)}") }, { navigate("family") }, { navigate("emergency") })
            }
            composable(Destination.History.route) { HistoryRoute(openCase,{id->onSelectCase(id);navigate("report")}) }
            composable(Destination.Scan.route, arguments = listOf(navArgument("tab") { type = NavType.StringType; defaultValue = "text" })) {
                ScanRoute(locale, openCase)
            }
            composable(Destination.Graph.route, arguments = listOf(navArgument("caseId") { type = NavType.StringType })) {
                AlertsRoute(AlertsDestination.Graph, {}, { navigate("family") }, { navigate("emergency") })
            }
            composable(Destination.Assistant.route) { AssistantRoute() }
            composable(Destination.Trends.route) { TrendsRoute() }
            composable(Destination.Emergency.route) { EmergencyRoute() }
            composable(Destination.Family.route) { FamilyRoute() }
            composable(Destination.Settings.route) { SettingsRoute(locale, onLocale, navigate) }
            composable(Destination.Report.route) { AlertsRoute(AlertsDestination.Report, {}, { navigate("family") }, { navigate("emergency") }) }
        }
    }
}
