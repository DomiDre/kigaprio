<script lang="ts">
	import { onMount } from 'svelte';
	import { currentUser } from '$lib/stores/auth';
	import { isAuthenticated } from '$lib/stores/auth';
	import { apiService } from '$lib/services/api';
	import { goto } from '$app/navigation';
	import Loading from '$lib/components/Loading.svelte';
	import { getMonthOptions, parseMonthString } from '$lib/utils/dateHelpers';

	let loading = true;
	let priorities: any[] = [];
	const monthOptions = getMonthOptions();
	let selectedMonth = monthOptions[0]; // Format: "Januar 2025"
	let completedWeeks = 0;
	let totalWeeks = 0;
	let progressPercentage = 0;
	let allWeeksCompleted = false;
	let error: string | null = null;

	// Helper function to check if a week is complete (matching main component logic)
	function isWeekComplete(priority: any): boolean {
		if (!priority || !priority.priorities) return false;

		const p = priority.priorities;
		const priorityValues = [p.monday, p.tuesday, p.wednesday, p.thursday, p.friday];

		// Filter out null, undefined, and empty strings
		const validPriorities = priorityValues.filter(
			(val) => val !== null && val !== undefined && val !== ''
		);

		// Must have all 5 days filled AND all values must be unique (1-5)
		return validPriorities.length === 5 && new Set(validPriorities).size === 5;
	}

	async function loadPriorities() {
		try {
			loading = true;
			error = null;

			// Fetch priorities for selected month (using correct format like "Januar 2025")
			const response = await apiService.getPriorities(selectedMonth);
			priorities = response || [];

			// Calculate progress
			calculateProgress();
		} catch (err) {
			console.error('Error loading priorities:', err);
			error = 'Fehler beim Laden der Prioritäten';
			priorities = [];
		} finally {
			loading = false;
		}
	}

	function calculateProgress() {
		// Parse the selected month string (e.g., "Januar 2025")
		const { year, month } = parseMonthString(selectedMonth);
		const currentYear = year;
		const currentMonthNum = month; // Already 0-indexed from parseMonthString

		// Calculate total weeks in current month
		const firstDay = new Date(currentYear, currentMonthNum, 1);
		const lastDay = new Date(currentYear, currentMonthNum + 1, 0);

		// Count weeks that have at least one weekday (Mon-Fri) in the month
		totalWeeks = 0;
		const tempDate = new Date(firstDay);

		// Find the first Monday of or before the first day of month
		while (tempDate.getDay() !== 1) {
			tempDate.setDate(tempDate.getDate() - 1);
		}

		// Count each week that has at least one weekday in the month
		while (tempDate <= lastDay) {
			const weekStart = new Date(tempDate);
			const weekEnd = new Date(tempDate);
			weekEnd.setDate(weekEnd.getDate() + 4); // Friday of the same week

			// Check if this week has any weekday in the current month
			let hasWeekdayInMonth = false;
			for (let d = new Date(weekStart); d <= weekEnd; d.setDate(d.getDate() + 1)) {
				if (d.getMonth() === currentMonthNum && d.getFullYear() === currentYear) {
					hasWeekdayInMonth = true;
					break;
				}
			}

			if (hasWeekdayInMonth) {
				totalWeeks++;
			}

			// Move to next week
			tempDate.setDate(tempDate.getDate() + 7);
		}

		// Count completed weeks using the updated logic
		completedWeeks = priorities.filter(isWeekComplete).length;

		// Calculate percentage
		if (totalWeeks > 0) {
			progressPercentage = Math.round((completedWeeks / totalWeeks) * 100);
		} else {
			progressPercentage = 0;
		}

		// Check if all weeks are completed
		allWeeksCompleted = completedWeeks === totalWeeks && totalWeeks > 0;
	}

	async function handleLogout() {
		try {
			await apiService.logout();
		} catch (err) {
			console.error('Logout error:', err);
		} finally {
			goto('/');
		}
	}

	function getMonthName(monthString: string): string {
		// monthString is already in format "Januar 2025", just return it
		return monthString;
	}

	function getNextIncompleteWeek(): number | null {
		for (let week = 1; week <= totalWeeks; week++) {
			const weekPriority = priorities.find((p) => p.weekNumber === week);
			if (!weekPriority || !isWeekComplete(weekPriority)) {
				return week;
			}
		}
		return null;
	}

	onMount(() => {
		if ($isAuthenticated && $currentUser) {
			loadPriorities();
		}
	});

	// Reload priorities when month changes
	$: if (selectedMonth && $isAuthenticated && $currentUser) {
		loadPriorities();
	}
</script>

{#if $isAuthenticated && $currentUser}
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-4xl px-4 py-10">
			<!-- Dashboard Header -->
			<div class="mb-10 flex flex-col items-center">
				<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">
					Willkommen, {$currentUser?.name?.split(' ')[0] || 'zurück'}!
				</h1>
				<p class="text-center text-gray-600 dark:text-gray-300">
					{#if allWeeksCompleted}
						🎉 Super! Alle Wochen für {getMonthName(selectedMonth)} sind priorisiert!
					{:else}
						Hier können die Prioritäten für die nächsten Wochen eingegeben werden.
					{/if}
				</p>

				<!-- Month Selector -->
				<div class="mt-4 flex items-center gap-3">
					<label for="month-select" class="text-sm font-medium text-gray-700 dark:text-gray-300">
						Monat:
					</label>
					<select
						id="month-select"
						bind:value={selectedMonth}
						class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-800 shadow-sm transition-colors hover:border-purple-400 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
					>
						{#each monthOptions as month}
							<option value={month}>{month}</option>
						{/each}
					</select>
				</div>

				<div class="mt-4 flex gap-4">
					<button
						class="rounded-lg bg-purple-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-purple-700"
						on:click={handleLogout}>Logout</button
					>
				</div>
			</div>

			{#if loading}
				<Loading message="Lade Prioritäten..." />
			{:else if error}
				<div class="mb-6 rounded-lg bg-red-100 p-4 text-red-700 dark:bg-red-900 dark:text-red-300">
					{error}
				</div>
			{:else}
				<!-- Dashboard Cards Overview -->
				<div class="mb-10 grid grid-cols-1 gap-6 md:grid-cols-2">
					<!-- Week Progress -->
					<div
						class="flex flex-col items-center rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800"
					>
						<div class="mb-2 text-lg font-semibold text-purple-600 dark:text-purple-300">
							Wochenfortschritt - {getMonthName(selectedMonth)}
						</div>

						{#if allWeeksCompleted}
							<div class="mb-4 text-center">
								<div class="mb-2 text-4xl">✅</div>
								<div class="font-semibold text-green-600 dark:text-green-400">
									Alle Wochen vollständig!
								</div>
							</div>
						{:else}
							<div class="mb-2 h-4 w-full rounded-full bg-gray-200 dark:bg-gray-700">
								<div
									class="h-full rounded-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-500"
									style="width:{progressPercentage}%"
								></div>
							</div>
							<div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
								{completedWeeks} von {totalWeeks} Wochen abgeschlossen ({progressPercentage}%)
							</div>
							{#if getNextIncompleteWeek()}
								<div class="mb-3 text-xs text-gray-500 dark:text-gray-400">
									Nächste offene Woche: Woche {getNextIncompleteWeek()}
								</div>
							{/if}
						{/if}

						<a
							href="/priorities"
							class="mt-3 rounded bg-purple-100 px-3 py-1 font-medium text-purple-700 transition hover:bg-purple-200 dark:bg-purple-900 dark:text-purple-300"
						>
							{allWeeksCompleted ? 'Prioritäten ansehen' : 'Prioritäten bearbeiten'}
						</a>
					</div>

					<!-- Statistics Card -->
					<div class="flex flex-col rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
						<div class="mb-3 text-lg font-semibold text-purple-600 dark:text-purple-300">
							Aktuelle Statistiken
						</div>
						<div class="flex-1 space-y-2">
							<div class="flex justify-between text-sm">
								<span class="text-gray-600 dark:text-gray-400">Monat:</span>
								<span class="font-medium text-gray-800 dark:text-gray-200">
									{getMonthName(selectedMonth)}
								</span>
							</div>
							<div class="flex justify-between text-sm">
								<span class="text-gray-600 dark:text-gray-400">Gesamte Wochen:</span>
								<span class="font-medium text-gray-800 dark:text-gray-200">{totalWeeks}</span>
							</div>
							<div class="flex justify-between text-sm">
								<span class="text-gray-600 dark:text-gray-400">Priorisierte Wochen:</span>
								<span class="font-medium text-gray-800 dark:text-gray-200">{completedWeeks}</span>
							</div>
							<div class="flex justify-between text-sm">
								<span class="text-gray-600 dark:text-gray-400">Offene Wochen:</span>
								<span class="font-medium text-gray-800 dark:text-gray-200">
									{totalWeeks - completedWeeks}
								</span>
							</div>
						</div>
						{#if !allWeeksCompleted && totalWeeks - completedWeeks > 0}
							<div
								class="mt-3 rounded bg-orange-50 p-2 text-xs text-orange-600 dark:bg-orange-900/20 dark:text-orange-400"
							>
								💡 Noch {totalWeeks - completedWeeks}
								{totalWeeks - completedWeeks === 1 ? 'Woche' : 'Wochen'} zu priorisieren
							</div>
						{/if}
					</div>
				</div>

				<!-- Recent Priorities Preview -->
				{#if priorities.length > 0}
					<div class="mb-6 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
						<div class="mb-4 text-lg font-semibold text-purple-600 dark:text-purple-300">
							Letzte Prioritäten
						</div>
						<div class="space-y-2">
							{#each priorities.slice(0, 3) as priority}
								<div
									class="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-700"
								>
									<div>
										<span class="font-medium text-gray-800 dark:text-gray-200">
											Woche {priority.weekNumber}
										</span>
										<span class="ml-2 text-sm text-gray-500 dark:text-gray-400">
											({priority.startDate} - {priority.endDate})
										</span>
									</div>
									<div>
										{#if isWeekComplete(priority)}
											<span class="text-green-600 dark:text-green-400">✓ Vollständig</span>
										{:else}
											<span class="text-orange-600 dark:text-orange-400">⚠ Unvollständig</span>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			{/if}

			<!-- Profile Card -->
			<div class="flex items-center gap-4 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
				<div
					class="flex h-16 w-16 items-center justify-center rounded-full bg-purple-200 text-xl font-bold text-purple-800 dark:bg-purple-800 dark:text-purple-100"
				>
					{$currentUser?.name?.charAt(0).toUpperCase() || '?'}
				</div>
				<div class="flex-1">
					<div class="font-semibold text-gray-800 dark:text-white">
						{$currentUser?.name || 'Account'}
					</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$currentUser?.email}</div>
				</div>
				<a
					href="/account"
					class="rounded bg-gray-100 px-3 py-2 text-sm font-medium text-purple-600 transition-colors hover:bg-purple-200 dark:bg-gray-700 dark:text-purple-300"
				>
					Account verwalten
				</a>
			</div>
		</div>
	</div>
{:else}
	<Loading message="Lade..." />
{/if}

