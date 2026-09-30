package com.knockknock.feature.timeline

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.knockknock.core.model.TimelineFilter
import com.knockknock.core.model.VisitSummary
import com.knockknock.core.model.matches
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class TimelineUiState(
    val visits: List<VisitSummary> = emptyList(),
    val selectedFilter: TimelineFilter = TimelineFilter.ALL,
    val isOffline: Boolean = false,
    val isLoading: Boolean = false,
    val message: String? = null,
)

class TimelineViewModel(private val repository: TimelineRepository) : ViewModel() {
    private val filter = MutableStateFlow(TimelineFilter.ALL)
    private val offline = MutableStateFlow(false)
    private val loading = MutableStateFlow(false)
    private val message = MutableStateFlow<String?>(null)

    val uiState: StateFlow<TimelineUiState> = combine(
        repository.visits,
        filter,
        offline,
        loading,
        message,
    ) { visits, selectedFilter, isOffline, isLoading, currentMessage ->
        TimelineUiState(
            visits = filterVisits(visits, selectedFilter),
            selectedFilter = selectedFilter,
            isOffline = isOffline,
            isLoading = isLoading,
            message = currentMessage,
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = TimelineUiState(isLoading = true),
    )

    init {
        refresh()
    }

    fun selectFilter(value: TimelineFilter) {
        filter.value = value
    }

    fun refresh() {
        viewModelScope.launch {
            loading.value = true
            apply(repository.refresh())
            loading.value = false
        }
    }

    fun runDemo() {
        viewModelScope.launch {
            loading.value = true
            apply(repository.runDemo())
            loading.value = false
        }
    }

    fun dismissMessage() {
        message.value = null
    }

    private fun apply(result: SyncResult) {
        offline.value = result.offline
        message.value = result.message
    }

    class Factory(private val repository: TimelineRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(TimelineViewModel::class.java))
            return TimelineViewModel(repository) as T
        }
    }
}

internal fun filterVisits(
    visits: List<VisitSummary>,
    filter: TimelineFilter,
): List<VisitSummary> = visits.filter { it.matches(filter) }
