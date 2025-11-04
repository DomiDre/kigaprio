<script lang="ts">
	import Close from 'virtual:icons/mdi/close';
	import { fade, scale } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { SvelteMap } from 'svelte/reactivity';

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
		onSubmitAndContinue: (data: {
			identifier: string;
			month: string;
			weeks: WeekPriority[];
		}) => void;
	}

	let { onClose, onSubmit, onSubmitAndContinue }: Props = $props();

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

	const dayLabelsFull = {
		monday: 'Montag',
		tuesday: 'Dienstag',
		wednesday: 'Mittwoch',
		thursday: 'Donnerstag',
		friday: 'Freitag'
	};

	// Set default month to current month
	const now = new Date();
	month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

	// Store references to all input elements for auto-focus
	let inputRefs: SvelteMap<string, HTMLInputElement> = new SvelteMap();

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

		const dayUsingPriority = getDayUsingPriority(weekIndex, newPriority);

		if (dayUsingPriority && dayUsingPriority !== day) {
			error = `Priorität ${newPriority} wird bereits für ${dayLabelsFull[dayUsingPriority]} verwendet. Jede Priorität kann nur einmal pro Woche vergeben werden.`;
			target.value = weeks[weekIndex][day]?.toString() ?? '';
			return;
		}

		weeks[weekIndex][day] = newPriority;
		error = '';
		focusNextInput(weekIndex, dayIndex);
	}

	function validateWeeks(): boolean {
		for (let i = 0; i < weeks.length; i++) {
			const week = weeks[i];
			const priorities = days.map((day) => week[day]).filter((p) => p !== null);
			const uniquePriorities = new Set(priorities);

			if (priorities.length !== uniquePriorities.size) {
				error = `Woche ${i + 1}: Jede Priorität darf nur einmal pro Woche vergeben werden`;
				return false;
			}
		}
		return true;
	}

	function validateForm(): boolean {
		error = '';

		if (!identifier.trim()) {
			error = 'Bitte geben Sie eine Kennung ein (z.B. Teilnehmernummer)';
			return false;
		}

		const monthRegex = /^\d{4}-\d{2}$/;
		if (!monthRegex.test(month)) {
			error = 'Bitte geben Sie einen gültigen Monat ein (Format: YYYY-MM)';
			return false;
		}

		const hasAnyPriority = weeks.some((week) =>
			days.some((day) => week[day] !== null && week[day] !== undefined)
		);

		if (!hasAnyPriority) {
			error = 'Bitte geben Sie mindestens eine Priorität ein';
			return false;
		}

		return validateWeeks();
	}

	function resetForm() {
		identifier = '';
		weeks = [
			{ weekNumber: 1, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null },
			{ weekNumber: 2, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null },
			{ weekNumber: 3, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null },
			{ weekNumber: 4, monday: null, tuesday: null, wednesday: null, thursday: null, friday: null }
		];
		error = '';
	}

	function handleSubmit() {
		if (!validateForm()) return;
		onSubmit({ identifier, month, weeks });
	}

	function handleSubmitAndContinue() {
		if (!validateForm()) return;
		onSubmitAndContinue({ identifier, month, weeks });
		resetForm();
		setTimeout(() => document.getElementById('identifier')?.focus(), 100);
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

<!-- Full screen on mobile, centered modal on desktop -->
<div
	class="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4"
	transition:fade={{ duration: 200 }}
	onclick={onClose}
	onkeydown={(e) => e.key === 'Enter' && e.stopPropagation()}
	role="button"
	tabindex="-1"
>
	<div
		class="flex h-[95vh] w-full max-w-4xl flex-col rounded-t-2xl bg-white shadow-2xl sm:h-auto sm:max-h-[90vh] sm:rounded-2xl dark:bg-gray-800"
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
		<!-- Header - Sticky on mobile -->
		<div
			class="flex items-center justify-between border-b border-gray-200 p-4 sm:p-6 dark:border-gray-700"
		>
			<h2 class="text-lg font-bold text-gray-800 sm:text-2xl dark:text-white">
				Manuelle Prioritäten-Eingabe
			</h2>
			<button
				onclick={onClose}
				class="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-200"
				aria-label="Schließen"
			>
				<Close class="h-5 w-5 sm:h-6 sm:w-6" />
			</button>
		</div>

		<!-- Body - Scrollable -->
		<div class="flex-1 overflow-y-auto p-4 sm:p-6">
			<!-- Form Section -->
			<div class="mb-4 sm:mb-6">
				<div class="flex flex-col gap-2">
					<label for="identifier" class="text-sm font-semibold text-gray-700 dark:text-gray-300">
						Kennung (z.B. Teilnehmernummer):
					</label>
					<input
						id="identifier"
						type="text"
						bind:value={identifier}
						placeholder="123 oder ABC"
						class="rounded-lg border border-gray-300 px-4 py-3 text-base text-gray-900 transition-colors focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 focus:outline-none sm:py-2 sm:text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400"
					/>
				</div>

				<!-- Month input for better tab order -->
				<div class="mt-4 flex flex-col gap-2">
					<label for="month" class="text-sm font-semibold text-gray-700 dark:text-gray-300">
						Monat:
					</label>
					<input
						id="month"
						type="month"
						bind:value={month}
						class="rounded-lg border border-gray-300 px-4 py-3 text-base text-gray-900 transition-colors focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 focus:outline-none sm:py-2 sm:text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400"
					/>
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

			<!-- Priorities Grid - Mobile optimized -->
			<div class="mb-4 space-y-4 sm:rounded-xl sm:bg-gray-50 sm:p-4 dark:sm:bg-gray-900/50">
				<!-- Desktop: Grid with header -->
				<div class="hidden sm:block">
					<div
						class="mb-3 grid grid-cols-[80px_repeat(5,1fr)] gap-2 text-center text-sm font-semibold text-gray-600 dark:text-gray-400"
					>
						<div>Woche</div>
						{#each days as day (day)}
							<div>{dayLabels[day]}</div>
						{/each}
					</div>

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
										class="w-full max-w-[60px] [appearance:textfield] rounded-lg border border-gray-300 px-3 py-2 text-center text-base font-semibold text-gray-900 transition-colors placeholder:text-gray-300 focus:border-purple-500 focus:ring-4 focus:ring-purple-500/10 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-600 dark:focus:border-purple-400 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
									/>
								</div>
							{/each}
						</div>
					{/each}
				</div>

				<!-- Mobile: Card-based layout -->
				<div class="space-y-4 sm:hidden">
					{#each weeks as week, weekIndex (weekIndex)}
						<div
							class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
						>
							<div class="mb-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300">
								Kalenderwoche {week.weekNumber}
							</div>

							<div class="space-y-3">
								{#each days as day, dayIndex (day)}
									<div class="flex items-center gap-3">
										<label
											for="mobile-{weekIndex}-{dayIndex}"
											class="w-24 text-sm font-medium text-gray-700 dark:text-gray-300"
										>
											{dayLabelsFull[day]}
										</label>
										<input
											id="mobile-{weekIndex}-{dayIndex}"
											type="number"
											min="1"
											max="5"
											value={week[day] ?? ''}
											oninput={(e) => handlePriorityInput(weekIndex, day, dayIndex, e)}
											placeholder="1-5"
											use:registerInput={getInputKey(weekIndex, dayIndex)}
											class="w-20 [appearance:textfield] rounded-lg border border-gray-300 px-4 py-3 text-center text-lg font-semibold text-gray-900 transition-colors placeholder:text-gray-300 focus:border-purple-500 focus:ring-4 focus:ring-purple-500/10 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder:text-gray-600 dark:focus:border-purple-400 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
										/>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Help Text -->
			<div
				class="rounded-lg bg-blue-50 p-3 text-xs text-blue-800 sm:text-sm dark:bg-blue-900/20 dark:text-blue-200"
			>
				<strong>Hinweis:</strong> Geben Sie Prioritäten von 1-5 ein (1 = höchste Priorität). Jede Priorität
				darf nur einmal pro Woche vergeben werden. Leer lassen = keine Angabe.
			</div>
		</div>

		<!-- Footer - Sticky on mobile -->
		<div
			class="flex flex-col gap-2 border-t border-gray-200 p-4 sm:flex-row sm:justify-between sm:gap-3 sm:p-6 dark:border-gray-700"
		>
			<button
				onclick={onClose}
				class="order-3 rounded-lg bg-gray-100 px-5 py-3 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-200 sm:order-1 sm:py-2.5 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
			>
				Abbrechen
			</button>
			<div class="flex flex-col gap-2 sm:flex-row sm:gap-3">
				<button
					onclick={handleSubmitAndContinue}
					class="order-1 rounded-lg bg-purple-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-purple-700 sm:order-2 sm:py-2.5 dark:bg-purple-500 dark:hover:bg-purple-600"
				>
					Speichern & Weiter
				</button>
				<button
					onclick={handleSubmit}
					class="order-2 rounded-lg bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700 sm:order-3 sm:py-2.5 dark:bg-blue-500 dark:hover:bg-blue-600"
				>
					Speichern
				</button>
			</div>
		</div>
	</div>
</div>
