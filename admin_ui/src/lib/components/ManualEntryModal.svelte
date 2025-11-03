<script lang="ts">
	import Close from 'virtual:icons/mdi/close';
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';

	type Priority = 1 | 2 | 3 | 4 | 5 | null;

	interface WeekPriority {
		weekNumber: number;
		monday: Priority;
		tuesday: Priority;
		wednesday: Priority;
		thursday: Priority;
		friday: Priority;
	}

	interface Props {
		onClose: () => void;
		onSubmit: (data: { identifier: string; month: string; weeks: WeekPriority[] }) => void;
	}

	let { onClose, onSubmit }: Props = $props();

	let identifier = $state('');
	let month = $state('');
	let error = $state('');

	// Initialize 4 weeks of priorities
	let weeks = $state<WeekPriority[]>([
		{ weekNumber: 1, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null },
		{ weekNumber: 2, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null },
		{ weekNumber: 3, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null },
		{ weekNumber: 4, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null }
	]);

	const days: Array<'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday'> = [
		'monday',
		'tuesday',
		'wednesday',
		'thursday',
		'friday'
	];

	const dayLabels = {
		monday: 'Mo',
		tuesday: 'Di',
		wednesday: 'Mi',
		thursday: 'Do',
		friday: 'Fr'
	};

	// Set default month to current month
	const now = new Date();
	month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

	// Store references to all input elements for auto-focus
	let inputRefs: Map<string, HTMLInputElement> = new Map();

	function getInputKey(weekIndex: number, dayIndex: number): string {
		return `${weekIndex}-${dayIndex}`;
	}

	// Custom action to register input refs
	function registerInput(node: HTMLInputElement, key: string) {
		inputRefs.set(key, node);
		return {
			destroy() {
				inputRefs.delete(key);
			}
		};
	}

	function focusNextInput(weekIndex: number, dayIndex: number) {
		// Calculate next input position
		let nextWeekIndex = weekIndex;
		let nextDayIndex = dayIndex + 1;

		// Move to next week if we're at the last day
		if (nextDayIndex >= days.length) {
			nextWeekIndex++;
			nextDayIndex = 0;
		}

		// Focus next input if it exists
		if (nextWeekIndex < weeks.length) {
			const nextKey = getInputKey(nextWeekIndex, nextDayIndex);
			const nextInput = inputRefs.get(nextKey);
			if (nextInput) {
				nextInput.focus();
				// Select the content if there is any
				nextInput.select();
			}
		}
	}

	function validatePriority(value: string): Priority {
		if (value === '' || value === null) return null;
		const num = parseInt(value, 10);
		if (num >= 1 && num <= 5) return num as Priority;
		return null;
	}

	// Get which day uses a specific priority in a week
	function getDayUsingPriority(
		weekIndex: number,
		priority: Priority
	): 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | null {
		if (priority === null) return null;
		const week = weeks[weekIndex];
		return days.find((day) => week[day] === priority) || null;
	}

	function handlePriorityInput(
		weekIndex: number,
		day: 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday',
		dayIndex: number,
		event: Event
	) {
		const target = event.target as HTMLInputElement;
		const newPriority = validatePriority(target.value);

		if (newPriority === null) {
			weeks[weekIndex][day] = null;
			error = '';
			return;
		}

		// Check if this priority is already used in the same week
		const dayUsingPriority = getDayUsingPriority(weekIndex, newPriority);

		if (dayUsingPriority && dayUsingPriority !== day) {
			error = `Priorität ${newPriority} wird bereits für ${dayLabels[dayUsingPriority]} verwendet. Jede Priorität kann nur einmal pro Woche vergeben werden.`;
			target.value = weeks[weekIndex][day]?.toString() ?? '';
			return;
		}

		weeks[weekIndex][day] = newPriority;
		error = '';

		// Auto-focus next input
		focusNextInput(weekIndex, dayIndex);
	}

	function validateWeeks(): boolean {
		// Check each week for duplicate priorities
		for (let i = 0; i < weeks.length; i++) {
			const week = weeks[i];
			const priorities = days.map((day) => week[day]).filter((p) => p !== null);

			// Check for duplicates
			const uniquePriorities = new Set(priorities);
			if (priorities.length !== uniquePriorities.size) {
				error = `Woche ${i + 1}: Jede Priorität darf nur einmal pro Woche vergeben werden`;
				return false;
			}
		}
		return true;
	}

	function handleSubmit() {
		error = '';

		// Validate identifier
		if (!identifier.trim()) {
			error = 'Bitte geben Sie eine Kennung ein (z.B. Teilnehmernummer)';
			return;
		}

		// Validate month format (YYYY-MM)
		const monthRegex = /^\d{4}-\d{2}$/;
		if (!monthRegex.test(month)) {
			error = 'Bitte geben Sie einen gültigen Monat ein (Format: YYYY-MM)';
			return;
		}

		// Check if at least one priority is set
		const hasAnyPriority = weeks.some((week) =>
			days.some((day) => week[day] !== null && week[day] !== undefined)
		);

		if (!hasAnyPriority) {
			error = 'Bitte geben Sie mindestens eine Priorität ein';
			return;
		}

		// Validate no duplicate priorities per week
		if (!validateWeeks()) {
			return;
		}
		console.log(identifier, month, weeks);

		onSubmit({ identifier, month, weeks });
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
		}
	}

	function handleStopPropagation(event: Event) {
		event.stopPropagation();
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
	transition:fade={{ duration: 200 }}
	onclick={onClose}
	onkeydown={(e) => e.key === 'Enter' && e.stopPropagation()}
	role="button"
	tabindex="-1"
>
	<div
		class="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white shadow-2xl dark:bg-gray-800"
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
		<!-- Header -->
		<div class="flex items-center justify-between border-b border-gray-200 p-6 dark:border-gray-700">
			<h2 class="text-2xl font-bold text-gray-800 dark:text-white">
				Manuelle Prioritäten-Eingabe
			</h2>
			<button
				onclick={onClose}
				class="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-200"
				aria-label="Schließen"
			>
				<Close class="h-6 w-6" />
			</button>
		</div>

		<!-- Body -->
		<div class="p-6">
			<!-- Form Section -->
			<div class="mb-6">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<div class="flex flex-col gap-2">
						<label
							for="identifier"
							class="text-sm font-semibold text-gray-700 dark:text-gray-300"
						>
							Kennung (z.B. Teilnehmernummer):
						</label>
						<input
							id="identifier"
							type="text"
							bind:value={identifier}
							placeholder="123 oder ABC"
							class="rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400"
						/>
					</div>

					<div class="flex flex-col gap-2">
						<label for="month" class="text-sm font-semibold text-gray-700 dark:text-gray-300">
							Monat:
						</label>
						<input
							id="month"
							type="month"
							bind:value={month}
							class="rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400"
						/>
					</div>
				</div>

				{#if error}
					<div
						class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200"
						transition:scale={{ duration: 200 }}
					>
						{error}
					</div>
				{/if}
			</div>

			<!-- Priorities Grid -->
			<div class="mb-4 rounded-xl bg-gray-50 p-4 dark:bg-gray-900/50">
				<!-- Grid Header -->
				<div class="mb-3 grid grid-cols-[80px_repeat(5,1fr)] gap-2 text-center text-sm font-semibold text-gray-600 dark:text-gray-400">
					<div>Woche</div>
					{#each days as day (day)}
						<div>{dayLabels[day]}</div>
					{/each}
				</div>

				<!-- Grid Rows -->
				{#each weeks as week, weekIndex (weekIndex)}
					<div class="mb-2 grid grid-cols-[80px_repeat(5,1fr)] items-center gap-2">
						<div class="text-center text-sm font-semibold text-gray-700 dark:text-gray-300">
							KW {week.weekNumber}
						</div>
						{#each days as day, dayIndex (day)}
							<div class="flex justify-center">
								<input
									type="number"
									min="1"
									max="5"
									value={week[day] ?? ''}
									oninput={(e) => handlePriorityInput(weekIndex, day, dayIndex, e)}
									placeholder="-"
									use:registerInput={getInputKey(weekIndex, dayIndex)}
									class="w-full max-w-[60px] rounded-lg border border-gray-300 px-3 py-2 text-center text-base font-semibold text-gray-900 transition-colors placeholder:text-gray-300 focus:border-purple-500 focus:outline-none focus:ring-4 focus:ring-purple-500/10 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-600 dark:focus:border-purple-400 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
								/>
							</div>
						{/each}
					</div>
				{/each}
			</div>

			<!-- Help Text -->
			<div class="rounded-lg bg-blue-50 p-3 text-sm text-blue-800 dark:bg-blue-900/20 dark:text-blue-200">
				<strong>Hinweis:</strong> Geben Sie Prioritäten von 1-5 ein (1 = höchste Priorität). Jede
				Priorität darf nur einmal pro Woche vergeben werden. Leer lassen = keine Angabe.
			</div>
		</div>

		<!-- Footer -->
		<div class="flex justify-end gap-3 border-t border-gray-200 p-6 dark:border-gray-700">
			<button
				onclick={onClose}
				class="rounded-lg bg-gray-100 px-5 py-2.5 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
			>
				Abbrechen
			</button>
			<button
				onclick={handleSubmit}
				class="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
			>
				Speichern
			</button>
		</div>
	</div>
</div>