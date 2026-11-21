package com.fraudshield.app.feature.family

import android.content.Context
import android.net.Uri
import android.provider.ContactsContract
import androidx.lifecycle.*
import com.fraudshield.app.core.model.*
import com.fraudshield.app.core.network.*
import com.fraudshield.app.data.repository.*
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import java.util.UUID
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@HiltViewModel class FamilyViewModel @Inject constructor(private val data:ClientDataRepository,
    private val fraud:FraudRepository, private val preferences:PreferencesRepository, private val selection:CaseContextStore,
    @ApplicationContext private val context:Context, private val dispatchers:DispatcherProvider):ViewModel(){
    private val mutable=MutableStateFlow<UiState<FamilyAlertReceipt>>(UiState.Empty);val state=mutable.asStateFlow()
    val members=data.members().catch{mutable.value=it.toUiError();emit(emptyList())}.stateIn(viewModelScope,SharingStarted.Eagerly,emptyList())
    val caseId=selection.caseId
    val ready get()=data.familyReady
    private val mutableName=MutableStateFlow("");val name=mutableName.asStateFlow()
    private val mutableId=MutableStateFlow("");val memberId=mutableId.asStateFlow()
    private val mutableConsent=MutableStateFlow(false);val consent=mutableConsent.asStateFlow()
    fun name(v:String){mutableName.value=v};fun id(v:String){mutableId.value=v};fun consent(v:Boolean){mutableConsent.value=v}
    fun caseId(v:String){selection.select(v.takeIf{it.isNotBlank()})}
    fun add(){if(name.value.isBlank()||!consent.value)return
        viewModelScope.launch{runCatching{val id=UUID.randomUUID().toString()
            data.members(members.value+FamilyMember(id,name.value.take(100),memberId=memberId.value.takeIf{it.isNotBlank()}?:if(fraud.isDemo)"DEMO-$id" else null,consent=true))
            mutableName.value="";mutableId.value="";mutableConsent.value=false
        }.onFailure{mutable.value=it.toUiError()}}
    }
    fun contact(uri:Uri){viewModelScope.launch{runCatching{withContext(dispatchers.io){
        context.contentResolver.query(uri,arrayOf(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME),null,null,null)?.use{cursor->
            if(cursor.moveToFirst())mutableName.value=cursor.getString(0).orEmpty()
        }
    }}.onFailure{mutable.value=it.toUiError()}}}
    fun toggle(member:FamilyMember,enabled:Boolean){viewModelScope.launch{runCatching{data.members(members.value.map{if(it.localId==member.localId)it.copy(shareAlerts=enabled)else it})}.onFailure{mutable.value=it.toUiError()}}}
    fun remove(member:FamilyMember){viewModelScope.launch{runCatching{data.members(members.value.filter{it.localId!=member.localId})}.onFailure{mutable.value=it.toUiError()}}}
    fun send(){val id=caseId.value?:return;val ids=members.value.filter{it.consent&&it.shareAlerts}.mapNotNull{it.memberId};if(ids.isEmpty()||!ready)return
        preferences.cloudConsent();viewModelScope.launch{mutable.value=UiState.Loading
            runCatching{fraud.familyAlert(FamilyAlertRequest(ids,id,true))}.onSuccess{mutable.value=UiState.Data(it)}.onFailure{mutable.value=it.toUiError()}}
    }
}
