package com.fraudshield.app.feature.alerts

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*
import com.fraudshield.app.core.model.*
import com.fraudshield.app.core.network.toUiError
import com.fraudshield.app.data.repository.*
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel class ReportViewModel @Inject constructor(private val data:ClientDataRepository, private val context:CaseContextStore):ViewModel() {
    val caseId=context.caseId
    private val mutableType=MutableStateFlow("sms"); val type=mutableType.asStateFlow()
    private val mutableNote=MutableStateFlow(""); val note=mutableNote.asStateFlow()
    private val mutableRefs=MutableStateFlow(""); val refs=mutableRefs.asStateFlow()
    private val mutableAttachment=MutableStateFlow<Uri?>(null); val attachment=mutableAttachment.asStateFlow()
    private val mutableConsent=MutableStateFlow(false); val consent=mutableConsent.asStateFlow()
    private val mutable=MutableStateFlow<UiState<ReportSubmission>>(UiState.Empty); val state=mutable.asStateFlow()
    val evidenceReady get()=data.evidenceReady
    fun clearCase(){context.select(null)}
    fun type(v:String) {mutableType.value=v; mutableConsent.value=false}
    fun note(v:String) {mutableNote.value=v; mutableConsent.value=false}
    fun refs(v:String) {mutableRefs.value=v; mutableConsent.value=false}
    fun attachment(v:Uri?) {mutableAttachment.value=v; mutableConsent.value=false}
    fun consent(v:Boolean) {mutableConsent.value=v}
    fun submit() {if(!consent.value||state.value==UiState.Loading)return
        viewModelScope.launch {mutable.value=UiState.Loading
            runCatching { val evidence=refs.value.split(',').map{it.trim()}.filter{it.isNotBlank()}.toMutableList()
                attachment.value?.let { evidence+=data.upload(it) }
                data.report(ReportRequest(caseId.value,type.value,evidence,ManualCheck.redactOtp(note.value.take(4000)).takeIf{it.isNotBlank()}))
            }.onSuccess {mutable.value=UiState.Data(it);mutableConsent.value=false}.onFailure {mutable.value=it.toUiError()}
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable internal fun ReportScreen() {
    val model:ReportViewModel=hiltViewModel(); val state by model.state.collectAsStateWithLifecycle()
    val type by model.type.collectAsStateWithLifecycle(); val note by model.note.collectAsStateWithLifecycle();val refs by model.refs.collectAsStateWithLifecycle()
    val attachment by model.attachment.collectAsStateWithLifecycle(); val consent by model.consent.collectAsStateWithLifecycle()
    val caseId by model.caseId.collectAsStateWithLifecycle()
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()){model.attachment(it)}
    ScreenList {
        item {Notice(stringResource(R.string.never_credentials))}
        caseId?.let{id->item{ShieldCard{Text(stringResource(R.string.case_id)+": "+id);SecondaryButton(stringResource(R.string.clear_case),model::clearCase)}}}
        item {ShieldCard {
            FlowRow {listOf("sms","call","url","qr","screenshot","apk","upi").forEach{value->FilterChip(type==value,{model.type(value)},{Text(value)})}}
            OutlinedTextField(refs,model::refs,Modifier.fillMaxWidth(),label={Text(stringResource(R.string.evidence_refs))})
            OutlinedTextField(note,model::note,Modifier.fillMaxWidth(),label={Text(stringResource(R.string.report_note))},minLines=3)
            SecondaryButton(stringResource(R.string.attach_evidence),{picker.launch(arrayOf("image/*","application/vnd.android.package-archive"))})
            if(attachment!=null)Text(stringResource(R.string.attachment_selected))
            if(attachment!=null&&!model.evidenceReady)Notice(stringResource(R.string.upload_pending),true)
            Row{Checkbox(consent,model::consent);Text(stringResource(R.string.report_consent),Modifier.weight(1f))}
            PrimaryButton(stringResource(R.string.submit_report),model::submit,consent&&(attachment==null||model.evidenceReady)&&state!=UiState.Loading)
        }}
        item{StateContent(state,stringResource(R.string.report_empty),stringResource(R.string.report_description),model::submit){submission->ShieldCard{
            submission.queuedId?.let{Text(stringResource(R.string.report_queued));Text(it)}
            submission.receipt?.let{Text(stringResource(R.string.report_received));Text(it.reportId);Text(it.status)}
        }}}
    }
}
