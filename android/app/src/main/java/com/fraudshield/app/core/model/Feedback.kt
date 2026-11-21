package com.fraudshield.app.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class FeedbackRequest(@SerialName("case_id") val caseId: String, val feedback: String = "mark_safe")
@Serializable
data class FeedbackReceipt(@SerialName("feedback_id") val feedbackId: String, val status: String)
