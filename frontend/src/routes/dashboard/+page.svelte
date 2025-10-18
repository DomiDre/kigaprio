<script lang="ts">
	import { onMount } from 'svelte';
	import { isAuthenticated, authStore } from '$lib/stores/auth';
	import { apiService } from '$lib/services/api';
	import { goto } from '$app/navigation';
	import Loading from '$lib/components/Loading.svelte';
	import { getMonthOptions, parseMonthString, formatMonthForAPI } from '$lib/utils/dateHelpers';
	import type { WeekData } from '$lib/types/priorities';
	import { SvelteDate } from 'svelte/reactivity';
	import ProtectedRoute from '$lib/components/ProtectedRoute.svelte';

	let loading = true;
	let priorities: WeekData[] = [];
	const monthOptions = getMonthOptions();
	let selectedMonth = monthOptions[0];
	let completedWeeks = 0;
	let totalWeeks = 0;
	let progressPercentage = 0;
	let allWeeksCompleted = false;
	let error: string | null = null;

	// Statistics
	let totalPrioritiesSet = 0;
	let currentStreak = 0;
	let longestStreak = 0;
	let completionRate = 0;

	// Helper function to check if a week is complete
	function isWeekComplete(week: WeekData): boolean {
		const priorities = [week.monday, week.tuesday, week.wednesday, week.thursday, week.friday];
		const validPriorities = priorities.filter((p) => p !== null && p !== undefined);
		return validPriorities.length === 5 && new Set(validPriorities).size === 5;
	}

	async function loadPriorities() {
		if (!$isAuthenticated) {
			error = 'Sitzung abgelaufen. Bitte melden Sie sich erneut an.';
			setTimeout(() => {
				authStore.clearAuth();
				goto('/login');
			}, 2000);
			return;
		}

		try {
			loading = true;
			error = null;

			const apiMonth = formatMonthForAPI(selectedMonth);
			const response = await apiService.getPriorities(apiMonth);

			// Properly update priorities array
			priorities = response.weeks || [];

			// Calculate statistics
			calculateProgress();
			calculateStatistics();
		} catch (err: any) {
			console.error('Error loading priorities:', err);
			if (err.message?.includes('Verschlüsselungsschlüssel')) {
				dekMissing = true;
				error = 'Sitzung abgelaufen. Sie werden zur Anmeldung weitergeleitet...';
				setTimeout(() => {
					authStore.clearAuth();
					goto('/login');
				}, 2000);
			} else {
				error = 'Fehler beim Laden der Prioritäten';
			}
			priorities = [];
		} finally {
			loading = false;
		}
	}

	function calculateProgress() {
		const { year, month } = parseMonthString(selectedMonth);

		// Calculate total weeks in the month
		const firstDay = new SvelteDate(year, month, 1);
		const lastDay = new SvelteDate(year, month + 1, 0);

		totalWeeks = 0;
		const tempDate = new SvelteDate(firstDay);

		// Find first Monday
		while (tempDate.getDay() !== 1) {
			tempDate.setDate(tempDate.getDate() - 1);
		}

		// Count weeks with weekdays in the month
		while (tempDate <= lastDay) {
			const weekEnd = new SvelteDate(tempDate);
			weekEnd.setDate(weekEnd.getDate() + 4);

			let hasWeekdayInMonth = false;
			for (let d = new SvelteDate(tempDate); d <= weekEnd; d.setDate(d.getDate() + 1)) {
				if (d.getMonth() === month && d.getFullYear() === year) {
					hasWeekdayInMonth = true;
					break;
				}
			}

			if (hasWeekdayInMonth) {
				totalWeeks++;
			}

			tempDate.setDate(tempDate.getDate() + 7);
		}

		// Count completed weeks
		completedWeeks = priorities.filter(isWeekComplete).length;
		progressPercentage = totalWeeks > 0 ? Math.round((completedWeeks / totalWeeks) * 100) : 0;
		allWeeksCompleted = completedWeeks === totalWeeks && totalWeeks > 0;
	}

	function calculateStatistics() {
		// Calculate total priorities set
		totalPrioritiesSet = priorities.reduce((total, week) => {
			const weekPriorities = [
				week.monday,
				week.tuesday,
				week.wednesday,
				week.thursday,
				week.friday
			];
			return total + weekPriorities.filter((p) => p !== null && p !== undefined).length;
		}, 0);

		// Calculate streaks
		let tempCurrentStreak = 0;
		let tempLongestStreak = 0;
		let streakActive = true;

		priorities.forEach((week) => {
			if (isWeekComplete(week)) {
				if (streakActive) {
					tempCurrentStreak++;
				}
				tempLongestStreak++;
			} else {
				streakActive = false;
				if (tempLongestStreak > longestStreak) {
					longestStreak = tempLongestStreak;
				}
				tempLongestStreak = 0;
			}
		});

		currentStreak = tempCurrentStreak;
		if (tempLongestStreak > longestStreak) {
			longestStreak = tempLongestStreak;
		}

		// Calculate completion rate
		const totalPossiblePriorities = totalWeeks * 5;
		completionRate =
			totalPossiblePriorities > 0
				? Math.round((totalPrioritiesSet / totalPossiblePriorities) * 100)
				: 0;
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

	function getNextIncompleteWeek(): number | null {
		for (let i = 0; i < priorities.length; i++) {
			if (!isWeekComplete(priorities[i])) {
				return priorities[i].weekNumber;
			}
		}
		return null;
	}

	onMount(() => {
		loadPriorities();
	});

	// Reload priorities when month changes
	$: if (selectedMonth && $isAuthenticated) {
		loadPriorities();
	}
</script>

<ProtectedRoute>
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-6xl px-4 py-10">
			<!-- Navigation Bar -->
			<div class="mb-6 flex items-center justify-between">
				<h1 class="text-3xl font-bold text-gray-800 dark:text-white">Dashboard</h1>
				<div class="flex gap-3">
					<a
						href="/priorities"
						class="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors duration-200 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-5 w-5"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
							/>
						</svg>
						Prioritäten
					</a>
					<button
						class="rounded-lg bg-red-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-red-700"
						on:click={handleLogout}>Logout</button
					>
				</div>
			</div>

			<!-- Welcome Section -->
			<div class="mb-8 text-center">
				<h2 class="mb-2 text-2xl font-semibold text-gray-800 dark:text-white">
					Willkommen zurück!
				</h2>
				<p class="text-gray-600 dark:text-gray-300">
					{#if allWeeksCompleted}
						🎉 Super! Alle Wochen für {selectedMonth} sind priorisiert!
					{:else}
						Hier ist Ihre Übersicht für {selectedMonth}
					{/if}
				</p>

				<!-- Month Selector -->
				<div class="mt-4 flex items-center justify-center gap-3">
					<label for="month-select" class="text-sm font-medium text-gray-700 dark:text-gray-300">
						Monat auswählen:
					</label>
					<select
						id="month-select"
						bind:value={selectedMonth}
						class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-800 shadow-sm transition-colors hover:border-purple-400 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
					>
						{#each monthOptions as month (month)}
							<option value={month}>{month}</option>
						{/each}
					</select>
				</div>
			</div>

			{#if loading}
				<Loading message="Lade Dashboard..." />
			{:else if error}
				<div class="mb-6 rounded-lg bg-red-100 p-4 text-red-700 dark:bg-red-900 dark:text-red-300">
					{error}
				</div>
			{:else}
				<!-- Main Statistics Grid -->
				<div class="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
					<!-- Progress Card -->
					<div class="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
						<div class="mb-2 flex items-center justify-between">
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Fortschritt</span>
							<span class="text-2xl">📊</span>
						</div>
						<div class="mb-1 text-2xl font-bold text-gray-800 dark:text-white">
							{progressPercentage}%
						</div>
						<div class="mb-2 h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
							<div
								class="h-full rounded-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-500"
								style="width:{progressPercentage}%"
							></div>
						</div>
						<div class="text-xs text-gray-600 dark:text-gray-400">
							{completedWeeks}/{totalWeeks} Wochen
						</div>
					</div>

					<!-- Current Streak -->
					<div class="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
						<div class="mb-2 flex items-center justify-between">
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400"
								>Aktuelle Serie</span
							>
							<span class="text-2xl">🔥</span>
						</div>
						<div class="mb-1 text-2xl font-bold text-gray-800 dark:text-white">
							{currentStreak}
						</div>
						<div class="text-xs text-gray-600 dark:text-gray-400">aufeinanderfolgende Wochen</div>
					</div>

					<!-- Completion Rate -->
					<div class="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
						<div class="mb-2 flex items-center justify-between">
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400"
								>Abschlussquote</span
							>
							<span class="text-2xl">✅</span>
						</div>
						<div class="mb-1 text-2xl font-bold text-gray-800 dark:text-white">
							{completionRate}%
						</div>
						<div class="text-xs text-gray-600 dark:text-gray-400">
							{totalPrioritiesSet}/{totalWeeks * 5} Prioritäten
						</div>
					</div>

					<!-- Longest Streak -->
					<div class="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
						<div class="mb-2 flex items-center justify-between">
							<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Längste Serie</span
							>
							<span class="text-2xl">🏆</span>
						</div>
						<div class="mb-1 text-2xl font-bold text-gray-800 dark:text-white">
							{longestStreak}
						</div>
						<div class="text-xs text-gray-600 dark:text-gray-400">Wochen in Folge</div>
					</div>
				</div>

				<!-- Week Overview -->
				{#if priorities.length > 0}
					<div class="mb-8 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
						<h3 class="mb-4 text-lg font-semibold text-purple-600 dark:text-purple-300">
							Wochenübersicht - {selectedMonth}
						</h3>
						<div class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
							{#each priorities as week (week.weekNumber)}
								<div
									class="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-700"
								>
									<div>
										<span class="font-medium text-gray-800 dark:text-gray-200">
											Woche {week.weekNumber}
										</span>
									</div>
									<div>
										{#if isWeekComplete(week)}
											<span
												class="inline-flex items-center rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200"
											>
												✓ Vollständig
											</span>
										{:else}
											<span
												class="inline-flex items-center rounded-full bg-orange-100 px-2 py-1 text-xs font-medium text-orange-800 dark:bg-orange-900 dark:text-orange-200"
											>
												In Bearbeitung
											</span>
										{/if}
									</div>
								</div>
							{/each}
						</div>
						{#if !allWeeksCompleted && getNextIncompleteWeek()}
							<div class="mt-4 rounded-lg bg-blue-50 p-3 dark:bg-blue-900/20">
								<p class="text-sm text-blue-700 dark:text-blue-300">
									💡 Nächste zu bearbeitende Woche: <strong>Woche {getNextIncompleteWeek()}</strong>
								</p>
								<a
									href="/priorities"
									class="mt-2 inline-block text-sm font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400"
								>
									Jetzt bearbeiten →
								</a>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Account Management -->
				<div
					class="flex items-center justify-between rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800"
				>
					<div>
						<h3 class="font-semibold text-gray-800 dark:text-white">Account-Verwaltung</h3>
						<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
							Passwort ändern, Gespeicherte Daten einsehen, Account löschen
						</p>
					</div>
					<a
						href="/account"
						class="rounded-lg bg-purple-100 px-4 py-2 text-sm font-medium text-purple-700 transition-colors hover:bg-purple-200 dark:bg-purple-900 dark:text-purple-300"
					>
						Account verwalten →
					</a>
				</div>
			{/if}
		</div>
	</div>
</ProtectedRoute>
