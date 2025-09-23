<script lang="ts">
	import type { WeekData, Priority, DayPriorities } from '$lib/types/priorities';
	import { dayNames } from '$lib/config/priorities';

	export let editingWeek: WeekData;
	export let activeWeekIndex: number;
	export let closeEditModal: () => void;
	export let saveWeek: (weekIndex: number) => void;
	export let weeks: WeekData[];
	export let getDayDates: (weekData: WeekData) => string[];

	function selectEditPriority(dayKey: string, priority: Priority) {
		if (!editingWeek) return;

		// Set the priority for the selected day
		editingWeek.priorities[dayKey as keyof DayPriorities] = priority;

		// Remove this priority from other days
		Object.keys(editingWeek.priorities).forEach((d) => {
			if (d !== dayKey && editingWeek.priorities[d as keyof DayPriorities] === priority) {
				editingWeek.priorities[d as keyof DayPriorities] = null;
			}
		});
	}

	function handleSave() {
		if (!editingWeek) return;
		weeks[activeWeekIndex] = { ...editingWeek };
		saveWeek(activeWeekIndex);
	}
</script>

<div class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4">
	<div
		class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 dark:bg-gray-800"
	>
		<div class="mb-6 flex items-center justify-between">
			<div>
				<h3 class="text-xl font-bold text-gray-800 dark:text-white">
					Woche {editingWeek.weekNumber} bearbeiten
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					{editingWeek.startDate} - {editingWeek.endDate}
				</p>
			</div>
			<button
				onclick={closeEditModal}
				aria-label="Fenster schliessen"
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
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

		<div class="space-y-4">
			{#each Object.entries(dayNames) as [dayKey, dayName], dayIndex (dayKey)}
				{@const dayDates = getDayDates(editingWeek)}
				{@const monthName = editingWeek.startDate.split('.')[1]}
				<div
					class="rounded-lg border-2 border-gray-200 p-4 transition hover:border-purple-300 dark:border-gray-600 dark:hover:border-purple-500"
				>
					<div class="mb-3 flex items-center justify-between">
						<span class="text-lg font-semibold text-gray-700 dark:text-gray-200">
							{dayName}, {dayDates[dayIndex]}{monthName}
						</span>
					</div>
					<div class="flex justify-center gap-3">
						{#each [1, 2, 3, 4, 5] as priority (priority)}
							<button
								class="h-14 w-14 transform rounded-full font-bold shadow transition
								{editingWeek.priorities[dayKey as keyof DayPriorities] === priority
									? 'scale-110 bg-gradient-to-r from-purple-600 to-blue-600 text-white'
									: 'border-2 border-gray-300 bg-white text-gray-700 hover:scale-105 dark:border-gray-500 dark:bg-gray-700 dark:text-gray-300'}"
								onclick={() => selectEditPriority(dayKey, priority as Priority)}
							>
								{priority}
							</button>
						{/each}
					</div>
				</div>
			{/each}
		</div>

		<!-- Validation Message -->
		{#if editingWeek && Object.values(editingWeek.priorities).some((p) => p === null)}
			<div
				class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
			>
				<span class="font-semibold">Hinweis:</span> Bitte vergeben Sie für jeden Tag eine unterschiedliche
				Priorität von 1-5
			</div>
		{/if}

		<div class="mt-6 flex gap-3">
			<button
				class="flex-1 rounded-xl bg-gray-200 py-3 font-semibold text-gray-700 transition hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
				onclick={closeEditModal}
			>
				Abbrechen
			</button>
			<button
				class="flex-1 transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 py-3 font-semibold text-white shadow-lg transition hover:scale-105"
				onclick={handleSave}
			>
				Speichern
			</button>
		</div>
	</div>
</div>
