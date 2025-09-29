<script lang="ts">
	import type { WeekData, Priority, DayPriorities } from '$lib/types/priorities';
	import { dayNames } from '$lib/config/priorities';
	import { scale } from 'svelte/transition';
	import { isWeekComplete } from '$lib/utils/dateHelpers';
	type Props = {
		week: WeekData;
		weekIndex: number;
		selectPriority: (weekIndex: number, day: keyof DayPriorities, priority: Priority) => void;
		saveWeek: (weekIndex: number) => Promise<void>;
		getDayDates: (weekData: WeekData) => string[];
	};

	// Destructure with defaults as needed
	let { week, weekIndex, selectPriority, saveWeek, getDayDates }: Props = $props();

	let saving = $state(false);
	let saveStatus: 'idle' | 'saving' | 'saved' | 'error' = $state('idle');
	let saveTimeout: NodeJS.Timeout;

	let weekCompleted = $derived(isWeekComplete(week));

	async function handlePrioritySelect(dayKey: string, priority: Priority) {
		if (saving) return;

		const oldPriority = week.priorities[dayKey as keyof DayPriorities];

		// Check if this priority is already used elsewhere
		const dayUsingPriority = Object.entries(week.priorities).find(
			([day, p]) => day !== dayKey && p === priority
		);

		// Update the priority for the selected day
		selectPriority(weekIndex, dayKey as keyof DayPriorities, priority);

		// If this priority was used elsewhere, swap the priorities
		if (dayUsingPriority) {
			const [otherDay] = dayUsingPriority;
			// Give the other day the old priority of the current day (swap)
			if (oldPriority) {
				selectPriority(weekIndex, otherDay as keyof DayPriorities, oldPriority);
			}
		}

		// Auto-save with debouncing
		await autoSave();
	}

	async function autoSave() {
		// Clear any pending save
		if (saveTimeout) {
			clearTimeout(saveTimeout);
		}

		// Show saving status immediately
		saveStatus = 'saving';
		saving = true;

		// Debounce the actual save by 500ms
		saveTimeout = setTimeout(async () => {
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
				saving = false;
			}
		}, 500);
	}

	function getCompletedDaysCount() {
		return Object.values(week.priorities).filter((p) => p !== null && p !== undefined).length;
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
						? `${getCompletedDaysCount()}/${Object.keys(week.priorities).length}`
						: 'Offen'}
			</span>
		</div>
	</div>

	<!-- Progress Bar -->
	{#if !weekCompleted}
		<div class="mb-4">
			<div class="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
				<div
					class="h-full rounded-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-300"
					style="width: {(getCompletedDaysCount() / Object.keys(week.priorities).length) * 100}%"
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
		{#each Object.entries(dayNames) as [dayKey, dayName], dayIndex (dayKey)}
			{@const dayDates = getDayDates(week)}
			{@const monthName = new Date(
				week.startDate.split('.').reverse().join('-')
			).toLocaleDateString('de-DE', { month: 'short' })}
			{@const currentPriority = week.priorities[dayKey as keyof DayPriorities]}

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
							{dayDates[dayIndex]}. {monthName}
						</span>
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
					{#each [1, 2, 3, 4, 5] as priority (priority)}
						{@const typedPriority = priority as Priority}
						{@const isSelected = currentPriority === priority}
						{@const isUsedElsewhere =
							!isSelected && Object.values(week.priorities).includes(typedPriority)}
						{@const usedByDay = isUsedElsewhere
							? Object.entries(week.priorities).find(([_, p]) => p === priority)?.[0]
							: null}
						{@const usedByDayName = usedByDay ? dayNames[usedByDay as keyof typeof dayNames] : null}

						<button
							class="relative h-10 w-10 transform rounded-full text-sm font-bold shadow transition-all
							{isSelected
								? 'scale-110 bg-gradient-to-r from-purple-600 to-blue-600 text-white ring-2 ring-purple-300 dark:ring-purple-700'
								: isUsedElsewhere
									? 'border border-orange-300 bg-orange-50 text-orange-600 hover:scale-105 dark:border-orange-600 dark:bg-orange-900 dark:text-orange-400'
									: 'border border-gray-300 bg-white text-gray-700 hover:scale-105 hover:border-purple-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300'}"
							onclick={() => handlePrioritySelect(dayKey, typedPriority)}
							disabled={saving}
							title={isUsedElsewhere ? `Tauschen mit ${usedByDayName}` : `Priorität ${priority}`}
						>
							{priority}
							{#if isUsedElsewhere}
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

