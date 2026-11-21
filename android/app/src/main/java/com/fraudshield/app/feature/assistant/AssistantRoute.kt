package com.fraudshield.app.feature.assistant

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.res.stringResource
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*
import com.fraudshield.app.core.model.UiState
import com.fraudshield.app.core.model.AssistantAnswer
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.font.FontWeight

@Composable
fun AssistantRoute() {
    val model: AssistantViewModel=hiltViewModel(); val messages by model.messages.collectAsStateWithLifecycle()
    val state by model.state.collectAsStateWithLifecycle(); val input by model.input.collectAsStateWithLifecycle(); val consent by model.consent.collectAsStateWithLifecycle()
    val caseId by model.caseId.collectAsStateWithLifecycle()
    val prompts=listOf(R.string.prompt_otp,R.string.prompt_kyc,R.string.prompt_freeze).map { stringResource(it) }
    ScreenList {
        caseId?.let{id->item{ShieldCard{Text(stringResource(R.string.case_id)+": "+id);SecondaryButton(stringResource(R.string.clear_case),model::clearCase)}}}
        if (messages.isEmpty()) item { ShieldCard { Text(stringResource(R.string.assistant_description)); prompts.forEach { prompt -> SecondaryButton(prompt,{model.input(prompt)}) } } }
        items(messages) { message -> ShieldCard { SectionLabel(stringResource(if(message.user) R.string.you else R.string.assistant)); Text(markdownLite(message.text)) } }
        if (state !is UiState.Data) item { StateContent(state,stringResource(R.string.ask_question),stringResource(R.string.assistant_description),model::retry) {} }
        if (state is UiState.Data) item { ShieldCard{val answer=(state as UiState.Data<AssistantAnswer>).value;Notice(answer.disclaimer);ActionButtons(answer.actions,stringResource(R.string.assistant),caseId)} }
        item { ShieldCard { OutlinedTextField(input,model::input,Modifier.fillMaxWidth(),label={Text(stringResource(R.string.ask_question))})
            Row { Checkbox(consent,model::consent); Text(stringResource(R.string.assistant_consent),Modifier.weight(1f)) }
            PrimaryButton(stringResource(R.string.send),model::send,consent&&input.isNotBlank()&&state!=UiState.Loading) }
        }
        item { Notice(stringResource(R.string.not_legal_advice)) }
    }
}

private fun markdownLite(value:String): AnnotatedString {
    val builder=AnnotatedString.Builder(); val parts=value.split("**")
    parts.forEachIndexed { index,part -> if(index%2==1) { builder.pushStyle(SpanStyle(fontWeight=FontWeight.Bold)); builder.append(part); builder.pop() } else builder.append(part) }
    return builder.toAnnotatedString()
}
