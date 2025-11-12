<script lang="ts">
	import type { WeekData, Priority, DayName } from '$lib/priorities.types';
	import type { VacationDay } from '$lib/vacation-days.types';
	import { dayNames, dayKeys, priorityColors } from '$lib/priorities.config';
	import { scale } from 'svelte/transition';
	import {
		isWeekComplete,
		getVacationDayForDate,
		getValidPriorities,
		isWeekStarted
	} from '$lib/dateHelpers.utils';

	type Props = {
		week: WeekData;
		weekIndex: number;
		selectPriority: (weekIndex: number, day: DayName, priority: Priority) => void;
		saveWeek: (weekIndex: number) => Promise<void>;
		getDayDates: (weekData: WeekData) => string[];
		vacationDaysMap: Map<string, VacationDay>;
	};

	let { week, weekIndex, selectPriority, saveWeek, getDayDates, vacationDaysMap }: Props = $props();

	let saveStatus: 'idle' | 'saving' | 'saved' | 'error' = $state('idle');
	let saveTimeout: NodeJS.Timeout;
	let isSaveInFlight = false;

	let weekCompleted = $derived(isWeekComplete(week, vacationDaysMap));
	let validPriorities = $derived(getValidPriorities(week, vacationDaysMap));
	let weekHasStarted = $derived(isWeekStarted(week));

	// Make vacation day lookups reactive by creating a derived helper
	let getVacation = $derived.by(() => {
		return (dateStr: string) => getVacationDayForDate(dateStr, vacationDaysMap);
	});

	async function handlePrioritySelect(dayKey: DayName, priority: Priority) {
		const oldPriority = week[dayKey];

		// Check if this priority is already used elsewhere
		const dayUsingPriority = dayKeys.find((day) => day !== dayKey && week[day] === priority);

		// Update the priority for the selected day (optimistic update)
		selectPriority(weekIndex, dayKey, priority);

		// If this priority was used elsewhere, swap the priorities
		if (dayUsingPriority && oldPriority) {
			selectPriority(weekIndex, dayUsingPriority, oldPriority);
		}

		// Auto-save with debouncing
		autoSave();
	}

	function autoSave() {
		// Clear any pending save
		if (saveTimeout) {
			clearTimeout(saveTimeout);
		}

		// Show saving status immediately (but don't block UI)
		saveStatus = 'saving';

		// Debounce the actual save by 800ms to allow rapid selections
		saveTimeout = setTimeout(async () => {
			// Prevent concurrent save requests
			if (isSaveInFlight) {
				return;
			}

			isSaveInFlight = true;

			try {
				await saveWeek(weekIndex);
				saveStatus = 'saved';

				// Reset status after 2 seconds
				setTimeout(() => {
					if (saveStatus === 'saved') {
						saveStatus = 'idle';
					}
				}, 2000);
			} catch (error) {
				console.error('Failed to save:', error);
				saveStatus = 'error';

				// Reset error status after 3 seconds
				setTimeout(() => {
					if (saveStatus === 'error') {
						saveStatus = 'idle';
					}
				}, 3000);
			} finally {
				isSaveInFlight = false;
			}
		}, 800);
	}

	function getCompletedDaysCount() {
		// Count only non-vacation days that have priorities
		let count = 0;
		dayKeys.forEach((dayKey, index) => {
			const dayDates = getDayDates(week);
			const startDateParts = week.startDate?.split('.');
			const fullDate =
				startDateParts && dayDates[index]
					? `${dayDates[index].replace('.', '')}.${startDateParts[1]}.${startDateParts[2]}`
					: '';
			const isVacationDay = fullDate ? !!getVacation(fullDate) : false;

			if (!isVacationDay && week[dayKey] !== null && week[dayKey] !== undefined) {
				count++;
			}
		});
		return count;
	}

	function getTotalNonVacationDays() {
		// Count total non-vacation days
		let count = 0;
		dayKeys.forEach((dayKey, index) => {
			const dayDates = getDayDates(week);
			const startDateParts = week.startDate?.split('.');
			const fullDate =
				startDateParts && dayDates[index]
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

<div class="rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
	<!-- Header with Status -->
	<div class="mb-4 flex items-center justify-between">
		<div>
			<h3 class="text-lg font-bold text-gray-800 dark:text-white">
				Woche {week.weekNumber}
			</h3>
			<p class="text-xs text-gray-500 dark:text-gray-400">
				{week.startDate} - {week.endDate}
			</p>
		</div>

		<!-- Status Badge and Save Indicator -->
		<div class="flex items-center gap-2">
			{#if saveStatus !== 'idle'}
				<span
					class="flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-all"
					transition:scale={{ duration: 200 }}
					class:bg-blue-100={saveStatus === 'saving'}
					class:text-blue-700={saveStatus === 'saving'}
					class:dark:bg-blue-900={saveStatus === 'saving'}
					class:dark:text-blue-300={saveStatus === 'saving'}
					class:bg-green-100={saveStatus === 'saved'}
					class:text-green-700={saveStatus === 'saved'}
					class:dark:bg-green-900={saveStatus === 'saved'}
					class:dark:text-green-300={saveStatus === 'saved'}
					class:bg-red-100={saveStatus === 'error'}
					class:text-red-700={saveStatus === 'error'}
					class:dark:bg-red-900={saveStatus === 'error'}
					class:dark:text-red-300={saveStatus === 'error'}
				>
					{#if saveStatus === 'saving'}
						<svg class="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
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
						Speichern...
					{:else if saveStatus === 'saved'}
						✓ Gespeichert
					{:else if saveStatus === 'error'}
						✗ Fehler
					{/if}
				</span>
			{/if}

			<span
				class="rounded-full px-3 py-1 text-sm
				{weekCompleted
					? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
					: getCompletedDaysCount() > 0
						? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
						: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}"
			>
				{weekCompleted
					? '✓ Fertig'
					: getCompletedDaysCount() > 0
						? `${getCompletedDaysCount()}/${getTotalNonVacationDays()}`
						: 'Offen'}
			</span>
		</div>
	</div>

	<!-- Week Started Warning -->
	{#if weekHasStarted}
		<div
			class="mb-3 rounded-lg border border-orange-200 bg-orange-50 p-2 text-xs text-orange-800 dark:border-orange-800 dark:bg-orange-900/20 dark:text-orange-200"
			transition:scale={{ duration: 300 }}
		>
			⚠️ Diese Woche hat bereits begonnen und kann nicht mehr bearbeitet werden.
		</div>
	{/if}

	<!-- Progress Bar -->
	{#if !weekCompleted}
		<div class="mb-4">
			<div class="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
				<div
					class="h-full rounded-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-300"
					style="width: {getTotalNonVacationDays() > 0
						? (getCompletedDaysCount() / getTotalNonVacationDays()) * 100
						: 0}%"
				></div>
			</div>
		</div>
	{:else}
		<div
			class="mb-4 rounded-lg bg-green-50 p-2 text-center text-sm text-green-700 dark:bg-green-900 dark:text-green-300"
		>
			✅ Alle Tage haben eine Priorität!
		</div>
	{/if}

	<!-- Days List -->
	<div class="space-y-3">
		{#each dayKeys as dayKey, dayIndex (dayKey)}
			{@const dayDates = getDayDates(week)}
			{@const monthName = week.startDate
				? new Date(week.startDate.split('.').reverse().join('-')).toLocaleDateString('de-DE', {
						month: 'short'
					})
				: ''}
			{@const currentPriority = week[dayKey]}
			{@const dayName = dayNames[dayKey]}
			{@const startDateParts = week.startDate?.split('.')}
			{@const fullDate =
				startDateParts && dayDates[dayIndex]
					? `${dayDates[dayIndex].replace('.', '')}.${startDateParts[1]}.${startDateParts[2]}`
					: ''}
			{@const vacationDay = fullDate ? getVacation(fullDate) : undefined}

			<div
				class="rounded-lg p-3 transition-all
				{currentPriority
					? 'bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900 dark:to-blue-900'
					: 'bg-gray-50 dark:bg-gray-700'}"
			>
				<div class="mb-2 flex items-center justify-between">
					<div class="flex items-center gap-2">
						<span class="font-semibold text-gray-700 dark:text-gray-200">{dayName}</span>
						<span class="text-xs text-gray-500 dark:text-gray-400">
							{dayDates[dayIndex]}
							{monthName}
						</span>
						{#if vacationDay}
							<span
								class="rounded px-1.5 py-0.5 text-xs font-medium
								{vacationDay.type === 'vacation'
									? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
									: vacationDay.type === 'public_holiday'
										? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
										: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'}"
								title={vacationDay.description}
							>
								{vacationDay.type === 'vacation'
									? '🏖️ Urlaub'
									: vacationDay.type === 'public_holiday'
										? '🎉 Feiertag'
										: '📋 Abwesend'}
							</span>
						{/if}
					</div>
					{#if currentPriority}
						<span
							class="rounded-full bg-purple-200 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-800 dark:text-purple-200"
						>
							P{currentPriority}
						</span>
					{/if}
				</div>

				<div class="flex justify-center gap-1.5">
					{#each validPriorities as priority (priority)}
						{@const typedPriority = priority as Priority}
						{@const isSelected = currentPriority === priority}
						{@const isUsedElsewhere =
							!isSelected && dayKeys.some((day) => day !== dayKey && week[day] === typedPriority)}
						{@const usedByDay = isUsedElsewhere
							? dayKeys.find((day) => week[day] === priority)
							: null}
						{@const usedByDayName = usedByDay ? dayNames[usedByDay] : null}
						{@const isDisabled = !!vacationDay || weekHasStarted}

						<button
							class="relative h-10 w-10 transform rounded-full text-sm font-bold shadow transition-all
							{vacationDay
								? 'cursor-not-allowed border border-gray-200 bg-gray-100 text-gray-400 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-600'
								: isSelected
									? `scale-110 ${priorityColors[typedPriority as 1 | 2 | 3 | 4 | 5]} ring-opacity-50 text-white ring-2 ${weekHasStarted ? 'cursor-not-allowed' : ''}`
									: weekHasStarted && !isSelected
										? 'cursor-not-allowed border border-gray-300 bg-white text-gray-500 opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-400'
										: isUsedElsewhere
											? 'border border-orange-300 bg-orange-50 text-orange-600 hover:scale-105 dark:border-orange-600 dark:bg-orange-900 dark:text-orange-400'
											: 'border border-gray-300 bg-white text-gray-700 hover:scale-105 hover:border-purple-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300'}"
							onclick={() => !isDisabled && handlePrioritySelect(dayKey, typedPriority)}
							disabled={isDisabled}
							title={vacationDay
								? 'Prioritäten können nicht für Abwesenheitstage gesetzt werden'
								: weekHasStarted
									? 'Diese Woche hat bereits begonnen'
									: isUsedElsewhere
										? `Tauschen mit ${usedByDayName}`
										: `Priorität ${priority}`}
						>
							{priority}
							{#if isUsedElsewhere && !isDisabled}
								<span
									class="absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-orange-500 text-[8px] text-white"
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
