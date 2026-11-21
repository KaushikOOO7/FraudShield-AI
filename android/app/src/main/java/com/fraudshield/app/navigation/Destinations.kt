package com.fraudshield.app.navigation

import com.fraudshield.app.R

/** Stable route patterns. Tab selection is an optional argument rather than a second scan destination. */
enum class Destination(val route: String, val title: Int, val bottomTab: Boolean = false) {
    Welcome("welcome", R.string.app_name),
    Onboarding("onboarding", R.string.get_started),
    Permissions("permissions", R.string.permissions_title),
    Home("home", R.string.nav_home, true),
    Alert("alert/{caseId}", R.string.alert_detail),
    History("history", R.string.nav_history, true),
    Scan("scan?tab={tab}", R.string.nav_scan, true),
    Graph("graph/{caseId}", R.string.investigation_graph),
    Assistant("assistant", R.string.assistant),
    Trends("trends", R.string.trends),
    Emergency("emergency", R.string.emergency),
    Family("family", R.string.family),
    Settings("settings", R.string.nav_settings, true),
    Report("report", R.string.submit_report),
}
