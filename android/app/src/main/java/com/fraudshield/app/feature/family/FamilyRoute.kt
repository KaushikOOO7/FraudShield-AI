package com.fraudshield.app.feature.family

import android.content.Intent
import android.provider.ContactsContract
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.res.stringResource
import com.fraudshield.app.R
import com.fraudshield.app.core.designsystem.*

@Composable
fun FamilyRoute() {
    val model:FamilyViewModel=hiltViewModel();val members by model.members.collectAsStateWithLifecycle();val state by model.state.collectAsStateWithLifecycle()
    val name by model.name.collectAsStateWithLifecycle();val memberId by model.memberId.collectAsStateWithLifecycle();val consent by model.consent.collectAsStateWithLifecycle();val caseId by model.caseId.collectAsStateWithLifecycle()
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()){result->result.data?.data?.let{model.contact(it)}}
    ScreenList{
        item{Notice(stringResource(R.string.family_consent))}
        if(members.isEmpty())item{ShieldCard{Text(stringResource(R.string.no_family));Text(stringResource(R.string.family_description))}}
        members.forEach{member->item{ShieldCard{Text(member.name);Row{Text(stringResource(R.string.share_alerts),Modifier.weight(1f));Switch(member.shareAlerts,{model.toggle(member,it)})};SecondaryButton(stringResource(R.string.remove_member),{model.remove(member)})}}}
        item{ShieldCard{
            OutlinedTextField(name,model::name,Modifier.fillMaxWidth(),label={Text(stringResource(R.string.member_name))})
            OutlinedTextField(memberId,model::id,Modifier.fillMaxWidth(),label={Text(stringResource(R.string.member_id))})
            SecondaryButton(stringResource(R.string.choose_contact),{picker.launch(Intent(Intent.ACTION_PICK,ContactsContract.CommonDataKinds.Phone.CONTENT_URI))})
            Row{Checkbox(consent,model::consent);Text(stringResource(R.string.member_consent),Modifier.weight(1f))}
            PrimaryButton(stringResource(R.string.add_member),model::add,consent&&name.isNotBlank())
        }}
        item{ShieldCard{
            OutlinedTextField(caseId.orEmpty(),model::caseId,Modifier.fillMaxWidth(),label={Text(stringResource(R.string.case_id))})
            if(!model.ready)Notice(stringResource(R.string.family_enrollment_pending))
            PrimaryButton(stringResource(R.string.warn_family),model::send,model.ready&&caseId!=null&&members.any{it.shareAlerts&&it.memberId!=null})
        }}
        item{StateContent(state,stringResource(R.string.no_shared_alerts),stringResource(R.string.family_description),model::send){receipt->ShieldCard{Text(stringResource(R.string.family_result,receipt.sent.size,receipt.failed.size))}}}
    }
}
