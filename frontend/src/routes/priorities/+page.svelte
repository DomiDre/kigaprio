<script lang="ts">
	import { onMount } from 'svelte';
	import { pb } from '$lib/services/pocketbase';
	import { currentUser } from '$lib/stores/auth';
	import type { Priority, DayPriorities, WeekData } from '$lib/types/priorities.ts';

	// Priority configuration with proper typing
	const priorityColors: Record<1 | 2 | 3 | 4 | 5, string> = {
		5: 'bg-red-500',
		4: 'bg-orange-500',
		3: 'bg-yellow-500',
		2: 'bg-blue-500',
		1: 'bg-gray-400'
	} as const;

	const priorityLabels: Record<1 | 2 | 3 | 4 | 5, string> = {
		5: 'Sehr wichtig',
		4: 'Wichtig',
		3: 'Normal',
		2: 'Weniger wichtig',
		1: 'Unwichtig'
	} as const;

	const dayNames: Record<keyof DayPriorities, string> = {
		monday: 'Montag',
		tuesday: 'Dienstag',
		wednesday: 'Mittwoch',
		thursday: 'Donnerstag',
		friday: 'Freitag'
	} as const;

	// Helper function to get week dates for a given month
	function getWeeksForMonth(year: number, month: number): WeekData[] {
		const weeks: WeekData[] = [];
		const firstDay = new Date(year, month, 1);

		// Find first Monday of the month or the Monday of the week containing the 1st
		let currentDate = new Date(firstDay);
		const dayOfWeek = currentDate.getDay();
		if (dayOfWeek !== 1) {
			// If not Monday
			const daysToMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek;
			currentDate.setDate(currentDate.getDate() + daysToMonday);
		}

		let weekNumber = 1;

		// Generate 4 weeks
		while (weekNumber <= 4) {
			const startDate = new Date(currentDate);
			const endDate = new Date(currentDate);
			endDate.setDate(endDate.getDate() + 4); // Friday

			// Format dates as DD.MM.YYYY
			const formatDate = (date: Date) => {
				const day = date.getDate().toString().padStart(2, '0');
				const monthStr = (date.getMonth() + 1).toString().padStart(2, '0');
				const year = date.getFullYear();
				return `${day}.${monthStr}.${year}`;
			};

			weeks.push({
				weekNumber,
				startDate: formatDate(startDate),
				endDate: formatDate(endDate),
				priorities: {
					monday: null,
					tuesday: null,
					wednesday: null,
					thursday: null,
					friday: null
				},
				status: weekNumber === 1 ? 'pending' : 'locked'
			});

			// Move to next week
			currentDate.setDate(currentDate.getDate() + 7);
			weekNumber++;
		}

		return weeks;
	}

	// Get current and next month options
	function getMonthOptions(): string[] {
		const now = new Date();
		const currentMonth = now.getMonth();
		const currentYear = now.getFullYear();

		const months = [
			'Januar',
			'Februar',
			'März',
			'April',
			'Mai',
			'Juni',
			'Juli',
			'August',
			'September',
			'Oktober',
			'November',
			'Dezember'
		];

		const options: string[] = [];

		// Current month
		options.push(`${months[currentMonth]} ${currentYear}`);

		// Next month
		const nextMonth = new Date(currentYear, currentMonth + 1);
		options.push(`${months[nextMonth.getMonth()]} ${nextMonth.getFullYear()}`);

		return options;
	}

	// Parse month string to get year and month
	function parseMonthString(monthStr: string): { year: number; month: number } {
		const months: Record<string, number> = {
			Januar: 0,
			Februar: 1,
			März: 2,
			April: 3,
			Mai: 4,
			Juni: 5,
			Juli: 6,
			August: 7,
			September: 8,
			Oktober: 9,
			November: 10,
			Dezember: 11
		};

		const [monthName, yearStr] = monthStr.split(' ');
		return {
			year: parseInt(yearStr),
			month: months[monthName]
		};
	}

	// Get day dates for display
	function getDayDates(weekData: WeekData): string[] {
		const [day, _month] = weekData.startDate.split('.');
		const startDay = parseInt(day);

		return Array.from({ length: 5 }, (_, i) => {
			const dayNum = startDay + i;
			return `${dayNum}.`;
		});
	}

	// Component state using Svelte 5 runes
	const monthOptions = getMonthOptions();
	let selectedMonth = $state(monthOptions[0]);
	let activeWeekIndex = $state(0);
	let isMobile = $state(false);
	let showEditModal = $state(false);
	let editingWeek = $state<WeekData | null>(null);
	let saveError = $state('');
	let saveSuccess = $state('');

	// Initialize weeks data with proper dates
	let weeks = $state<WeekData[]>([]);

	// Derived state
	let completedWeeks = $derived(weeks.filter((w) => w.status === 'completed').length);
	let progressPercentage = $derived((completedWeeks / weeks.length) * 100);

	// Update weeks when month changes
	$effect(() => {
		const { year, month } = parseMonthString(selectedMonth);
		weeks = getWeeksForMonth(year, month);
		loadUserData();
	});

	// Check for mobile on mount
	onMount(() => {
		checkMobile();
		window.addEventListener('resize', checkMobile);

		return () => {
			window.removeEventListener('resize', checkMobile);
		};
	});

	function checkMobile() {
		isMobile = window.innerWidth < 768;
	}

	async function loadUserData() {
		if (!$currentUser) return;

		try {
			// Load existing priorities from PocketBase
			const records = await pb.collection('priorities').getFullList({
				filter: `userId = "${$currentUser.id}" && month = "${selectedMonth}"`,
				sort: 'weekNumber'
			});

			// Update weeks with loaded data
			records.forEach((record: any) => {
				const weekIndex = weeks.findIndex((w) => w.weekNumber === record.weekNumber);
				if (weekIndex !== -1) {
					weeks[weekIndex] = {
						...weeks[weekIndex],
						priorities: record.priorities,
						status: 'completed',
						id: record.id
					};

					// Unlock next week if this one is completed
					if (weekIndex < weeks.length - 1 && weeks[weekIndex + 1].status === 'locked') {
						weeks[weekIndex + 1].status = 'pending';
					}
				}
			});
		} catch (error) {
			console.error('Error loading priorities:', error);
		}
	}

	function selectPriority(weekIndex: number, day: keyof DayPriorities, priority: Priority) {
		if (!priority || weeks[weekIndex].status === 'locked') return;

		// Check if this priority is already used this week
		const currentWeek = weeks[weekIndex];
		const dayEntries = Object.entries(currentWeek.priorities) as [keyof DayPriorities, Priority][];

		// Remove priority from other days if it exists
		dayEntries.forEach(([d, p]) => {
			if (p === priority && d !== day) {
				weeks[weekIndex].priorities[d] = null;
			}
		});

		// Set the priority for the selected day
		weeks[weekIndex].priorities[day] = priority;
	}

	function openEditModal(week: WeekData, index: number) {
		if (week.status === 'locked') return;
		editingWeek = { ...week };
		activeWeekIndex = index;
		showEditModal = true;
	}

	function closeEditModal() {
		showEditModal = false;
		editingWeek = null;
	}

	async function saveWeek(weekIndex: number) {
		const week = weeks[weekIndex];

		// Validate all days have priorities
		const allDaysSet = Object.values(week.priorities).every((p) => p !== null);
		if (!allDaysSet) {
			saveError = 'Bitte vergeben Sie für jeden Tag eine Priorität';
			setTimeout(() => (saveError = ''), 3000);
			return;
		}

		// Validate each priority is used exactly once
		const usedPriorities = Object.values(week.priorities).filter((p) => p !== null);
		const uniquePriorities = new Set(usedPriorities);
		if (uniquePriorities.size !== 5) {
			saveError = 'Jede Priorität (1-5) muss genau einmal vergeben werden';
			setTimeout(() => (saveError = ''), 3000);
			return;
		}

		try {
			const data = {
				userId: $currentUser?.id,
				month: selectedMonth,
				weekNumber: week.weekNumber,
				priorities: week.priorities,
				startDate: week.startDate,
				endDate: week.endDate
			};

			if (week.id) {
				// Update existing record
				await pb.collection('priorities').update(week.id, data);
			} else {
				// Create new record
				const record = await pb.collection('priorities').create(data);
				weeks[weekIndex].id = record.id;
			}

			weeks[weekIndex].status = 'completed';

			// Unlock next week if exists
			if (weekIndex < weeks.length - 1) {
				weeks[weekIndex + 1].status = 'pending';
			}

			saveSuccess = 'Woche erfolgreich gespeichert!';
			setTimeout(() => (saveSuccess = ''), 3000);
			closeEditModal();
		} catch (error) {
			saveError = 'Fehler beim Speichern. Bitte versuchen Sie es erneut.';
			setTimeout(() => (saveError = ''), 3000);
			console.error('Save error:', error);
		}
	}

	async function submitMonth() {
		const allWeeksComplete = weeks.every((w) => w.status === 'completed');
		if (!allWeeksComplete) {
			saveError = 'Bitte vervollständigen Sie alle Wochen vor dem Einreichen';
			setTimeout(() => (saveError = ''), 3000);
			return;
		}

		try {
			// Mark month as submitted in PocketBase
			await pb.collection('monthlySubmissions').create({
				userId: $currentUser?.id,
				month: selectedMonth,
				submittedAt: new Date().toISOString(),
				weeks: weeks
			});

			saveSuccess = 'Monat erfolgreich eingereicht!';
			setTimeout(() => (saveSuccess = ''), 3000);
		} catch (error) {
			saveError = 'Fehler beim Einreichen. Bitte versuchen Sie es erneut.';
			setTimeout(() => (saveError = ''), 3000);
		}
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-6xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8 text-center">
			<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">Prioritäten</h1>
			<p class="text-gray-600 dark:text-gray-300">
				Geben Sie für jeden Tag Ihre Betreuungspriorität an <br />(5 = höchste Priorität)
			</p>
			<div
				class="mt-4 inline-flex items-center rounded-lg bg-white px-4 py-2 shadow dark:bg-gray-800"
			>
				<span class="text-sm text-gray-600 dark:text-gray-300">Monat:</span>
				<select
					bind:value={selectedMonth}
					class="ml-2 border-0 bg-transparent font-semibold text-purple-600 focus:outline-none dark:text-purple-400"
				>
					{#each monthOptions as month}
						<option value={month}>{month}</option>
					{/each}
				</select>
			</div>
		</div>

		<!-- Legend -->
		<div class="mb-6 rounded-xl bg-white p-4 shadow-lg dark:bg-gray-800">
			<div class="flex flex-wrap items-center justify-center gap-4 text-sm">
				<span class="font-semibold text-gray-700 dark:text-gray-300">Priorität:</span>
				{#each Object.entries(priorityLabels) as [priority, label]}
					<div class="flex items-center gap-2">
						<span
							class="flex h-8 w-8 items-center justify-center rounded-full {priorityColors[
								Number(priority) as 1 | 2 | 3 | 4 | 5
							]} font-bold text-white"
						>
							{priority}
						</span>
						<span class="text-gray-600 dark:text-gray-400">{label}</span>
					</div>
				{/each}
			</div>
		</div>

		<!-- Progress Indicator -->
		{#if weeks.length > 0}
			<div class="mb-6 rounded-xl bg-white p-4 shadow-lg dark:bg-gray-800">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Fortschritt</span>
					<span class="text-sm font-semibold text-purple-600 dark:text-purple-400">
						{completedWeeks} von {weeks.length} Wochen vollständig
					</span>
				</div>
				<div class="mt-2 h-3 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
					<div
						class="h-full rounded-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-500"
						style="width: {progressPercentage}%"
					></div>
				</div>
			</div>

			<!-- Mobile Week Tabs -->
			{#if isMobile}
				<div class="mb-6 flex gap-2 overflow-x-auto pb-2">
					{#each weeks as week, index}
						<button
							class="min-w-[80px] flex-none rounded-lg px-4 py-2 shadow transition
							{activeWeekIndex === index
								? 'bg-purple-600 text-white'
								: 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'}"
							onclick={() => (activeWeekIndex = index)}
						>
							Woche {week.weekNumber}
						</button>
					{/each}
				</div>

				<!-- Mobile Single Week View -->
				<div class="rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
					<div class="mb-6 flex items-center justify-between">
						<div>
							<h3 class="text-lg font-bold text-gray-800 dark:text-white">
								Woche {weeks[activeWeekIndex].weekNumber}
							</h3>
							<p class="text-xs text-gray-500 dark:text-gray-400">
								{weeks[activeWeekIndex].startDate} - {weeks[activeWeekIndex].endDate}
							</p>
						</div>
						<span
							class="rounded-full px-3 py-1 text-sm
						{weeks[activeWeekIndex].status === 'completed'
								? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
								: weeks[activeWeekIndex].status === 'pending'
									? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
									: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}"
						>
							{weeks[activeWeekIndex].status === 'completed'
								? '✓ Fertig'
								: weeks[activeWeekIndex].status === 'pending'
									? 'Offen'
									: 'Gesperrt'}
						</span>
					</div>

					<div class="space-y-4">
						{#each Object.entries(dayNames) as [dayKey, dayName], dayIndex}
							{@const dayDates = getDayDates(weeks[activeWeekIndex])}
							{@const monthName = weeks[activeWeekIndex].startDate.split('.')[1]}
							<div
								class="rounded-lg bg-gradient-to-r from-purple-50 to-blue-50 p-4 dark:from-gray-700 dark:to-gray-600"
							>
								<div class="mb-3 flex items-center justify-between">
									<span class="text-lg font-semibold text-gray-700 dark:text-gray-200"
										>{dayName}</span
									>
									<span class="text-sm text-gray-500 dark:text-gray-400">
										{dayDates[dayIndex]}{monthName}
									</span>
								</div>
								<div class="flex justify-center gap-2">
									{#each [1, 2, 3, 4, 5] as priority}
										<button
											class="h-12 w-12 transform rounded-full font-bold shadow transition
											{weeks[activeWeekIndex].priorities[dayKey as keyof DayPriorities] === priority
												? 'scale-110 bg-gradient-to-r from-purple-600 to-blue-600 text-white'
												: 'border-2 border-gray-300 bg-white text-gray-700 hover:scale-105 hover:border-purple-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300'}"
											disabled={weeks[activeWeekIndex].status === 'locked'}
											onclick={() =>
												selectPriority(
													activeWeekIndex,
													dayKey as keyof DayPriorities,
													priority as Priority
												)}
										>
											{priority}
										</button>
									{/each}
								</div>
							</div>
						{/each}
					</div>

					{#if weeks[activeWeekIndex].status === 'pending'}
						<div class="mt-6 flex gap-3">
							<button
								class="flex-1 transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 py-3 font-semibold text-white shadow-lg transition hover:scale-105"
								onclick={() => saveWeek(activeWeekIndex)}
							>
								Woche speichern
							</button>
						</div>
					{/if}
				</div>
			{:else}
				<!-- Desktop Grid View -->
				<div class="mb-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
					{#each weeks as week, index}
						<div
							class="rounded-xl bg-white p-4 shadow-xl transition hover:translate-y-[-2px] dark:bg-gray-800
						{week.status === 'pending' ? 'border-2 border-purple-400' : ''}"
						>
							<div class="mb-4 flex items-center justify-between">
								<h3 class="font-bold text-gray-800 dark:text-white">Woche {week.weekNumber}</h3>
								<span
									class="rounded-full px-2 py-1 text-xs
								{week.status === 'completed'
										? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
										: week.status === 'pending'
											? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
											: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}"
								>
									{week.status === 'completed'
										? '✓ Fertig'
										: week.status === 'pending'
											? 'Offen'
											: 'Gesperrt'}
								</span>
							</div>
							<div class="mb-3 text-xs text-gray-500 dark:text-gray-400">
								{week.startDate} - {week.endDate}
							</div>
							<div class="space-y-2">
								{#each Object.entries(dayNames) as [dayKey, dayName]}
									{@const priority = week.priorities[dayKey as keyof DayPriorities]}
									<div
										class="flex items-center justify-between rounded p-2
									{week.status === 'pending'
											? 'border border-purple-200 bg-purple-50 dark:border-purple-700 dark:bg-purple-900/20'
											: 'bg-gray-50 dark:bg-gray-700'}"
									>
										<span class="text-sm font-medium dark:text-gray-300"
											>{dayName.substring(0, 2)}</span
										>
										<span
											class="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white
										{priority
												? priorityColors[priority as 1 | 2 | 3 | 4 | 5]
												: 'bg-gray-200 text-gray-400 dark:bg-gray-600'}"
										>
											{priority || '?'}
										</span>
									</div>
								{/each}
							</div>
							{#if week.status === 'pending'}
								<button
									class="mt-3 w-full rounded-lg bg-purple-600 py-2 text-sm font-semibold text-white transition hover:bg-purple-700"
									onclick={() => openEditModal(week, index)}
								>
									Bearbeiten
								</button>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{/if}

		<!-- Action Buttons -->
		<div class="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
			<button
				class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4 font-semibold text-white shadow-xl transition hover:scale-105 sm:w-auto"
				onclick={submitMonth}
			>
				Gesamten Monat einreichen
			</button>
		</div>

		<!-- Notifications -->
		{#if saveError}
			<div class="fixed right-4 bottom-4 rounded-lg bg-red-500 px-4 py-3 text-white shadow-lg">
				{saveError}
			</div>
		{/if}
		{#if saveSuccess}
			<div class="fixed right-4 bottom-4 rounded-lg bg-green-500 px-4 py-3 text-white shadow-lg">
				{saveSuccess}
			</div>
		{/if}
	</div>

	<!-- Desktop Edit Modal -->
	{#if showEditModal && editingWeek}
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
					{#each Object.entries(dayNames) as [dayKey, dayName], dayIndex}
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
								{#each [1, 2, 3, 4, 5] as priority}
									<button
										class="h-14 w-14 transform rounded-full font-bold shadow transition
											{editingWeek.priorities[dayKey as keyof DayPriorities] === priority
											? 'scale-110 bg-gradient-to-r from-purple-600 to-blue-600 text-white'
											: 'border-2 border-gray-300 bg-white text-gray-700 hover:scale-105 dark:border-gray-500 dark:bg-gray-700 dark:text-gray-300'}"
										onclick={() => {
											if (!editingWeek) return;
											editingWeek.priorities[dayKey as keyof DayPriorities] = priority as Priority;
											// Remove this priority from other days
											Object.keys(editingWeek.priorities).forEach((d) => {
												if (
													d !== dayKey &&
													editingWeek!.priorities[d as keyof DayPriorities] === priority
												) {
													editingWeek!.priorities[d as keyof DayPriorities] = null;
												}
											});
										}}
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
						onclick={() => {
							if (!editingWeek) return;
							weeks[activeWeekIndex] = { ...editingWeek };
							saveWeek(activeWeekIndex);
						}}
					>
						Speichern
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
