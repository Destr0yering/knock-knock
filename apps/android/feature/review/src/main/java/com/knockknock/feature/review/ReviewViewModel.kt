package com.knockknock.feature.review

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.knockknock.core.model.AuditEntry
import com.knockknock.core.model.FamiliarProfile
import com.knockknock.core.model.HouseholdRole
import com.knockknock.core.model.ProfileProposal
import com.knockknock.core.model.VisitSummary
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class VisitReviewUiState(
    val visit: VisitSummary? = null,
    val profiles: List<FamiliarProfile> = emptyList(),
    val role: HouseholdRole = HouseholdRole.MEMBER,
)

class ReviewViewModel(
    private val visitId: String,
    private val repository: ReviewRepository,
) : ViewModel() {
    val state = combine(
        repository.visit(visitId),
        repository.profiles,
        repository.role,
        ::VisitReviewUiState,
    ).stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), VisitReviewUiState())

    init { viewModelScope.launch { repository.prepareDemo(visitId) } }

    fun setRole(role: HouseholdRole) = repository.setRole(role)
    fun markUnknown(personId: String) = launch { repository.markUnknown(personId) }
    fun markFaceUndetected(personId: String) = launch { repository.markFaceUndetected(personId) }
    fun confirm(personId: String, profile: FamiliarProfile) = launch {
        repository.confirmProfile(personId, profile)
    }
    fun savePhoto(personId: String) = launch { repository.savePhoto(personId) }
    fun propose(personId: String, name: String) = launch {
        repository.proposeProfile(visitId, personId, name)
    }

    private fun launch(block: suspend () -> Unit) { viewModelScope.launch { block() } }

    class Factory(
        private val visitId: String,
        private val repository: ReviewRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            ReviewViewModel(visitId, repository) as T
    }
}

data class ApprovalUiState(
    val proposals: List<ProfileProposal> = emptyList(),
    val audit: List<AuditEntry> = emptyList(),
    val role: HouseholdRole = HouseholdRole.MEMBER,
)

class ApprovalViewModel(private val repository: ReviewRepository) : ViewModel() {
    val state = combine(repository.proposals, repository.audit, repository.role, ::ApprovalUiState)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ApprovalUiState())

    fun setRole(role: HouseholdRole) = repository.setRole(role)
    fun decide(proposal: ProfileProposal, approve: Boolean) {
        viewModelScope.launch { repository.decide(proposal, approve) }
    }

    class Factory(private val repository: ReviewRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            ApprovalViewModel(repository) as T
    }
}
