package com.fraudshield.app.core.designsystem

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

object ShieldColors {
    val Background = Color(0xFF0B1220)
    val Surface = Color(0xFF101A2C)
    val SurfaceVariant = Color(0xFF18253F)
    val Primary = Color(0xFF34D399)
    val OnPrimary = Color(0xFF04291F)
    val Secondary = Color(0xFF38BDF8)
    val Danger = Color(0xFFF87171)
    val DangerSolid = Color(0xFFEF4444)
    val Caution = Color(0xFFFBBF24)
    val Safe = Color(0xFF4ADE80)
    val TextHigh = Color(0xFFE5EAF3)
    val TextMid = Color(0xFF94A3B8)
    val Border = Color(0xFF22314E)
}

private val ShieldScheme = darkColorScheme(
    primary = ShieldColors.Primary,
    onPrimary = ShieldColors.OnPrimary,
    secondary = ShieldColors.Secondary,
    onSecondary = ShieldColors.Background,
    background = ShieldColors.Background,
    onBackground = ShieldColors.TextHigh,
    surface = ShieldColors.Surface,
    onSurface = ShieldColors.TextHigh,
    surfaceVariant = ShieldColors.SurfaceVariant,
    onSurfaceVariant = ShieldColors.TextMid,
    error = ShieldColors.Danger,
    onError = ShieldColors.Background,
    outline = ShieldColors.Border,
)

private val ShieldTypography = Typography(
    headlineLarge = TextStyle(fontSize = 28.sp, lineHeight = 36.sp, fontWeight = FontWeight.Bold),
    titleLarge = TextStyle(fontSize = 20.sp, lineHeight = 28.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 22.sp),
    labelMedium = TextStyle(fontSize = 12.sp, lineHeight = 18.sp, fontWeight = FontWeight.Medium),
)

@Composable
fun FraudShieldTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = ShieldScheme,
        typography = ShieldTypography,
        shapes = Shapes(medium = RoundedCornerShape(20.dp), large = RoundedCornerShape(20.dp)),
        content = content,
    )
}
