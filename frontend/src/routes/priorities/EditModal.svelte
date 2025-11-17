<script lang="ts">
	import type { WeekData, Priority, DayName } from '$lib/priorities.types';
	import type { VacationDay } from '$lib/vacation-days.types';
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { dayKeys, priorityColors } from '$lib/priorities.config';
	import { getVacationDayForDate, getValidPriorities, isWeekStarted } from '$lib/dateHelpers.utils';
	import { LL } from '$i18n/i18n-svelte';

	type Props = {
		editingWeek: WeekData;
		activeWeekIndex: number;
		closeEditModal: () => void;
		saveWeek: (weekIndex: number) => Promise<void>;
		getDayDates: (weekData: WeekData) => string[];
		onWeekChange: (dayKey: DayName, priority: Priority) => void;
		vacationDaysMap: Map<string, VacationDay>;
	};
	let {
		editingWeek,
		activeWeekIndex,
		closeEditModal,
		saveWeek,
		getDayDates,
		onWeekChange,
		vacationDaysMap
	}: Props = $props();

	let saveStatus: 'idle' | 'saving' | 'saved' | 'error' = $state('idle');
	let saveTimeout: NodeJS.Timeout;
	let pendingSavePromise: Promise<void> | null = null;

	// Make vacation day lookups reactive by creating a derived helper
	let getVacation = $derived.by(() => {
		return (dateStr: string) => getVacationDayForDate(dateStr, vacationDaysMap);
	});

	let validPriorities = $derived(getValidPriorities(editingWeek, vacationDaysMap));

	// Check if the week has already started
	let weekHasStarted = $derived(isWeekStarted(editingWeek));

	// Helper function to check if week is complete (accounting for vacation days)
	function isWeekCompleteLocal(week: WeekData): boolean {
		const dayKeysList = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'] as const;
		let nonVacationDays = 0;
		let filledDays = 0;

		dayKeysList.forEach((dayKey, index) => {
			const dayDates = getDayDates(week);
			const startDateParts = week.startDate?.split('.');
			const fullDate =
				startDateParts && dayDates && dayDates[index]
					? `${dayDates[index].replace('.', '')}.${startDateParts[1]}.${startDateParts[2]}`
					: '';
			const isVacationDay = fullDate ? !!getVacation(fullDate) : false;

			if (!isVacationDay) {
				nonVacationDays++;
				if (week[dayKey] !== null && week[dayKey] !== undefined) {
					filledDays++;
				}
			}
		});

		// Get priorities for non-vacation days
		const priorities = dayKeysList
			.map((dayKey, index) => {
				const dayDates = getDayDates(week);
				const startDateParts = week.startDate?.split('.');
				const fullDate =
					startDateParts && dayDates && dayDates[index]
						? `${dayDates[index].replace('.', '')}.${startDateParts[1]}.${startDateParts[2]}`
						: '';
				const isVacationDay = fullDate ? !!getVacation(fullDate) : false;
				return isVacationDay ? null : week[dayKey];
			})
			.filter((p) => p !== null && p !== undefined);

		return filledDays === nonVacationDays && new Set(priorities).size === nonVacationDays;
	}

	async function selectEditPriority(dayKey: DayName, priority: Priority) {
		onWeekChange(dayKey, priority);

		// Auto-save with debouncing
		autoSave();
	}

	function autoSave() {
		// Clear any pending save
		if (saveTimeout) {
			clearTimeout(saveTimeout);
		}

		// Show saving status immediately
		saveStatus = 'saving';

		// Debounce the actual save by 500ms
		saveTimeout = setTimeout(() => {
			pendingSavePromise = saveWeek(activeWeekIndex)
				.then(() => {
					saveStatus = 'saved';
					// Reset status after 2 seconds
					setTimeout(() => {
						if (saveStatus === 'saved') {
							saveStatus = 'idle';
						}
					}, 2000);
				})
				.catch((error) => {
					console.error('Failed to save:', error);
					saveStatus = 'error';
					// Reset error status after 3 seconds
					setTimeout(() => {
						if (saveStatus === 'error') {
							saveStatus = 'idle';
						}
					}, 3000);
				})
				.finally(() => {
					pendingSavePromise = null;
				});
		}, 500);
	}

	async function handleClose() {
		// If there's a pending debounced save, execute it immediately
		if (saveTimeout) {
			clearTimeout(saveTimeout);
			saveStatus = 'saving';

			try {
				await saveWeek(activeWeekIndex);
			} catch (error) {
				console.error('Failed to save before closing:', error);
			}
		}

		// Wait for any in-flight save to complete
		if (pendingSavePromise) {
			await pendingSavePromise;
		}

		closeEditModal();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleClose();
		}
	}

	function handleStopPropagation(event: Event) {
		event.stopPropagation();
	}

	// Count how many non-vacation days have priorities assigned
	function getAssignedDaysCount(week: WeekData): number {
		let count = 0;
		dayKeys.forEach((dayKey, index) => {
			const dayDates = getDayDates(week);
			const startDateParts = week.startDate?.split('.');
			const fullDate =
				startDateParts && dayDates && dayDates[index]
					? `${dayDates[index].replace('.', '')}.${startDateParts[1]}.${startDateParts[2]}`
					: '';
			const isVacationDay = fullDate ? !!getVacation(fullDate) : false;

			if (!isVacationDay && week[dayKey] !== null && week[dayKey] !== undefined) {
				count++;
			}
		});
		return count;
	}

	// Count total non-vacation days
	function getTotalNonVacationDays(week: WeekData): number {
		let count = 0;
		dayKeys.forEach((dayKey, index) => {
			const dayDates = getDayDates(week);
			const startDateParts = week.startDate?.split('.');
			const fullDate =
				startDateParts && dayDates && dayDates[index]
					? `${dayDates[index].replace('.', '')}.${startDateParts[1]}.${startDateParts[2]}`
					: '';
			const isVacationDay = fullDate ? !!getVacation(fullDate) : false;

			if (!isVacationDay) {
				count++;
			}
		});
		return count;
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div
	class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4"
	transition:fade={{ duration: 200 }}
	onclick={handleClose}
	onkeydown={(e) => e.key === 'Enter' && e.stopPropagation()}
	role="button"
	tabindex="-1"
>
	<div
		class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl dark:bg-gray-800"
		transition:scale={{ duration: 300, easing: cubicOut, start: 0.9 }}
		onclick={handleStopPropagation}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				handleStopPropagation(e);
			}
		}}
		role="dialog"
		aria-modal="true"
		tabindex="0"
	>
		<!-- Header with Status -->
		<div class="mb-6 flex items-center justify-between">
			<div class="flex items-center gap-4">
				<div>
					<h3 class="text-xl font-bold text-gray-800 dark:text-white">
						{$LL.priorities.week()}
						{editingWeek.weekNumber}
						{weekHasStarted ? $LL.priorities.view() : $LL.priorities.edit()}
					</h3>
					{#if editingWeek.startDate && editingWeek.endDate}
						<p class="text-sm text-gray-500 dark:text-gray-400">
							{editingWeek.startDate} - {editingWeek.endDate}
						</p>
					{/if}
				</div>

				<!-- Save Status Indicator -->
				{#if saveStatus !== 'idle'}
					<div class="flex items-center gap-2" transition:scale={{ duration: 200 }}>
						{#if saveStatus === 'saving'}
							<div
								class="flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
							>
								<svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
									<circle
										class="opacity-25"
										cx="12"
										cy="12"
										r="10"
										stroke="currentColor"
										stroke-width="4"
									></circle>
									<path
										class="opacity-75"
										fill="currentColor"
										d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
									></path>
								</svg>
								{$LL.priorities.saving()}
							</div>
						{:else if saveStatus === 'saved'}
							<div
								class="flex items-center gap-2 rounded-full bg-green-100 px-3 py-1 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300"
							>
								<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
								{$LL.priorities.saved()}
							</div>
						{:else if saveStatus === 'error'}
							<div
								class="flex items-center gap-2 rounded-full bg-red-100 px-3 py-1 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300"
							>
								<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
										clip-rule="evenodd"
									/>
								</svg>
								{$LL.priorities.errorSaving()}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<button
				onclick={handleClose}
				aria-label={$LL.priorities.closeWindow()}
				class="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-200"
			>
				<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					></path>
				</svg>
			</button>
		</div>

		<!-- Week Started Warning -->
		{#if weekHasStarted}
			<div
				class="mb-4 rounded-lg border border-orange-200 bg-orange-50 p-3 dark:border-orange-800 dark:bg-orange-900/20"
				transition:scale={{ duration: 300 }}
			>
				<div class="flex items-center gap-2">
					<svg
						class="h-5 w-5 text-orange-600 dark:text-orange-400"
						fill="currentColor"
						viewBox="0 0 20 20"
					>
						<path
							fill-rule="evenodd"
							d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
							clip-rule="evenodd"
						/>
					</svg>
					<span class="text-sm font-medium text-orange-800 dark:text-orange-200">
						{$LL.priorities.weekStartedWarning()}
					</span>
				</div>
			</div>
		{:else if isWeekCompleteLocal(editingWeek)}
			<div
				class="mb-4 rounded-lg bg-green-50 p-3 dark:bg-green-900/20"
				transition:scale={{ duration: 300 }}
			>
				<div class="flex items-center justify-between">
					<span class="text-green-700 dark:text-green-300">
						✅ {$LL.priorities.allDaysAssigned()}
					</span>
					<button
						onclick={handleClose}
						class="rounded-lg bg-green-600 px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-green-700"
					>
						{$LL.priorities.done()}
					</button>
				</div>
			</div>
		{:else}
			<div class="mb-4">
				<div class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
					<span>{$LL.common.progress()}</span>
					<span
						>{getAssignedDaysCount(editingWeek)} / {getTotalNonVacationDays(editingWeek)}
						{$LL.common.daysCount()}</span
					>
				</div>
				<div class="mt-1 h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div
						class="h-full rounded-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-300"
						style="width: {getTotalNonVacationDays(editingWeek) > 0
							? (getAssignedDaysCount(editingWeek) / getTotalNonVacationDays(editingWeek)) * 100
							: 0}%"
					></div>
				</div>
			</div>
		{/if}

		<!-- Days List -->
		<div class="space-y-3">
			{#each dayKeys as dayKey, dayIndex (dayKey)}
				{@const dayDates = getDayDates(editingWeek)}
				{@const monthName = editingWeek.startDate
					? new Date(editingWeek.startDate.split('.').reverse().join('-')).toLocaleDateString(
							'de-DE',
							{ month: 'short' }
						)
					: ''}
				{@const currentPriority = editingWeek[dayKey]}
				{@const dayName = $LL.priorities.days[dayKey]()}
				{@const startDateParts = editingWeek.startDate?.split('.')}
				{@const fullDate =
					startDateParts && dayDates && dayDates[dayIndex]
						? `${dayDates[dayIndex].replace('.', '')}.${startDateParts[1]}.${startDateParts[2]}`
						: ''}
				{@const vacationDay = fullDate ? getVacation(fullDate) : undefined}

				<div
					class="group rounded-lg border-2 p-4 transition-all
					{currentPriority
						? 'border-purple-300 bg-purple-50 dark:border-purple-600 dark:bg-purple-900/20'
						: 'border-gray-200 hover:border-purple-200 dark:border-gray-600 dark:hover:border-purple-500'}"
				>
					<div class="mb-3 flex items-center justify-between">
						<div class="flex items-center gap-3">
							<span class="text-lg font-semibold text-gray-700 dark:text-gray-200">
								{dayName}
							</span>
							{#if dayDates && dayDates[dayIndex]}
								<span class="text-sm text-gray-500 dark:text-gray-400">
									{dayDates[dayIndex]}
									{monthName}
								</span>
							{/if}
							{#if vacationDay}
								<span
									class="rounded px-2 py-1 text-xs font-medium
									{vacationDay.type === 'vacation'
										? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
										: vacationDay.type === 'public_holiday'
											? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
											: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'}"
									title={vacationDay.description}
								>
									{vacationDay.type === 'vacation'
										? $LL.priorities.vacationDay()
										: vacationDay.type === 'public_holiday'
											? $LL.priorities.publicHoliday()
											: $LL.priorities.absent()}
								</span>
							{/if}
						</div>
						{#if currentPriority}
							<div
								class="rounded-full bg-purple-200 px-2 py-1 text-xs font-medium text-purple-700 dark:bg-purple-800 dark:text-purple-200"
							>
								{$LL.priorities.priority()}
								{currentPriority}
							</div>
						{/if}
					</div>

					<div class="flex justify-center gap-2 sm:gap-3">
						{#each validPriorities as priority (priority)}
							{@const typedPriority = priority as Priority}
							{@const isSelected = currentPriority === priority}
							{@const isUsedElsewhere =
								!isSelected &&
								dayKeys.some((day) => day !== dayKey && editingWeek[day] === typedPriority)}
							{@const usedByDay = isUsedElsewhere
								? dayKeys.find((day) => editingWeek[day] === priority)
								: null}
							{@const usedByDayName = usedByDay ? $LL.priorities.days[usedByDay]() : null}
							{@const isDisabled = !!vacationDay || weekHasStarted}

							<button
								class="relative h-12 w-12 transform rounded-full font-bold shadow-md transition-all duration-200 sm:h-14 sm:w-14
								{vacationDay
									? 'cursor-not-allowed border-2 border-gray-200 bg-gray-100 text-gray-400 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-600'
									: isSelected
										? `scale-110 ${priorityColors[typedPriority as 1 | 2 | 3 | 4 | 5]} ring-opacity-50 text-white ring-4 ${weekHasStarted ? 'cursor-not-allowed' : ''}`
										: weekHasStarted && !isSelected
											? 'cursor-not-allowed border-2 border-gray-300 bg-white text-gray-500 opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-400'
											: isUsedElsewhere
												? 'border-2 border-orange-300 bg-orange-50 text-orange-600 hover:scale-105 hover:border-orange-400 hover:shadow-lg dark:border-orange-600 dark:bg-orange-900/30 dark:text-orange-400'
												: 'border-2 border-gray-300 bg-white text-gray-700 hover:scale-105 hover:border-purple-400 hover:shadow-lg dark:border-gray-500 dark:bg-gray-700 dark:text-gray-300 dark:hover:border-purple-400'}"
								onclick={() => !isDisabled && selectEditPriority(dayKey, typedPriority)}
								disabled={isDisabled}
								title={vacationDay
									? $LL.priorities.priorityCannotBeSet()
									: weekHasStarted
										? $LL.priorities.weekAlreadyStarted()
										: isUsedElsewhere
											? $LL.priorities.swapPriority({ priority, day: usedByDayName || '' })
											: $LL.priorities.selectPriority({ priority })}
							>
								{priority}
								{#if isUsedElsewhere && !isDisabled}
									<span
										class="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-orange-500 text-xs text-white"
										title={$LL.priorities.willBeSwapped()}
									>
										⇄
									</span>
								{/if}
							</button>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</div>
</div>
