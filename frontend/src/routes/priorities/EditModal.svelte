<script lang="ts">
	import type { WeekData, Priority, DayPriorities } from '$lib/types/priorities';
	import { dayNames } from '$lib/config/priorities';
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { isWeekComplete } from '$lib/utils/dateHelpers';

	type Props = {
		editingWeek: WeekData;
		activeWeekIndex: number;
		closeEditModal: () => void;
		saveWeek: (weekIndex: number) => Promise<void>;
		weeks: WeekData[];
		getDayDates: (weekData: WeekData) => string[];
	};
	let { editingWeek, activeWeekIndex, closeEditModal, saveWeek, weeks, getDayDates }: Props =
		$props();

	let saveStatus: 'idle' | 'saving' | 'saved' | 'error' = $state('idle');
	let saveTimeout: NodeJS.Timeout;
	let pendingSavePromise: Promise<void> | null = null;

	async function selectEditPriority(dayKey: string, priority: Priority) {
		if (!editingWeek) return; // Remove the saving check

		// Optimistically update the UI
		const oldPriority = editingWeek.priorities[dayKey as keyof DayPriorities];

		// Check if this priority is already used elsewhere
		const dayUsingPriority = Object.entries(editingWeek.priorities).find(
			([day, p]) => day !== dayKey && p === priority
		);

		// Set the priority for the selected day
		editingWeek.priorities[dayKey as keyof DayPriorities] = priority;

		// If this priority was used elsewhere, swap the priorities
		if (dayUsingPriority) {
			const [otherDay] = dayUsingPriority;
			editingWeek.priorities[otherDay as keyof DayPriorities] = oldPriority;
		}

		// Update the main weeks array
		weeks[activeWeekIndex] = { ...editingWeek };

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
						Woche {editingWeek.weekNumber} bearbeiten
					</h3>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						{editingWeek.startDate} - {editingWeek.endDate}
					</p>
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
								Speichere...
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
								Gespeichert
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
								Fehler beim Speichern
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<button
				onclick={handleClose}
				aria-label="Fenster schließen"
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

		<!-- Completion Progress -->
		{#if isWeekComplete(editingWeek)}
			<div
				class="mb-4 rounded-lg bg-green-50 p-3 dark:bg-green-900/20"
				transition:scale={{ duration: 300 }}
			>
				<div class="flex items-center justify-between">
					<span class="text-green-700 dark:text-green-300">
						✅ Alle Tage haben eine Priorität zugewiesen!
					</span>
					<button
						onclick={handleClose}
						class="rounded-lg bg-green-600 px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-green-700"
					>
						Fertig
					</button>
				</div>
			</div>
		{:else}
			<div class="mb-4">
				<div class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
					<span>Fortschritt</span>
					<span
						>{Object.values(editingWeek.priorities).filter((p) => p !== null).length} / 5 Tage</span
					>
				</div>
				<div class="mt-1 h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div
						class="h-full rounded-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-300"
						style="width: {(Object.values(editingWeek.priorities).filter((p) => p !== null).length /
							5) *
							100}%"
					></div>
				</div>
			</div>
		{/if}

		<!-- Days List -->
		<div class="space-y-3">
			{#each Object.entries(dayNames) as [dayKey, dayName], dayIndex (dayKey)}
				{@const dayDates = getDayDates(editingWeek)}
				{@const monthName = new Date(
					editingWeek.startDate.split('.').reverse().join('-')
				).toLocaleDateString('de-DE', { month: 'short' })}
				{@const currentPriority = editingWeek.priorities[dayKey as keyof DayPriorities]}

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
							<span class="text-sm text-gray-500 dark:text-gray-400">
								{dayDates[dayIndex]}. {monthName}
							</span>
						</div>
						{#if currentPriority}
							<div
								class="rounded-full bg-purple-200 px-2 py-1 text-xs font-medium text-purple-700 dark:bg-purple-800 dark:text-purple-200"
							>
								Priorität {currentPriority}
							</div>
						{/if}
					</div>

					<div class="flex justify-center gap-2 sm:gap-3">
						{#each [1, 2, 3, 4, 5] as priority (priority)}
							{@const typedPriority = priority as Priority}
							{@const isSelected = currentPriority === priority}
							{@const isUsedElsewhere =
								!isSelected && Object.values(editingWeek.priorities).includes(typedPriority)}
							{@const usedByDay = isUsedElsewhere
								? Object.entries(editingWeek.priorities).find(([, p]) => p === priority)?.[0]
								: null}
							{@const usedByDayName = usedByDay
								? dayNames[usedByDay as keyof typeof dayNames]
								: null}

							<button
								class="relative h-12 w-12 transform rounded-full font-bold shadow-md transition-all duration-200 sm:h-14 sm:w-14
								{isSelected
									? 'scale-110 bg-gradient-to-r from-purple-600 to-blue-600 text-white ring-4 ring-purple-300 dark:ring-purple-700'
									: isUsedElsewhere
										? 'border-2 border-orange-300 bg-orange-50 text-orange-600 hover:scale-105 hover:border-orange-400 hover:shadow-lg dark:border-orange-600 dark:bg-orange-900/30 dark:text-orange-400'
										: 'border-2 border-gray-300 bg-white text-gray-700 hover:scale-105 hover:border-purple-400 hover:shadow-lg dark:border-gray-500 dark:bg-gray-700 dark:text-gray-300 dark:hover:border-purple-400'}"
								onclick={() => selectEditPriority(dayKey, typedPriority)}
								title={isUsedElsewhere
									? `Priorität ${priority} tauschen (aktuell bei ${usedByDayName})`
									: `Priorität ${priority} wählen`}
							>
								{priority}
								{#if isUsedElsewhere}
									<span
										class="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-orange-500 text-xs text-white"
										title="Wird getauscht"
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
