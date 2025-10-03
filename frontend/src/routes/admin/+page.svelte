<script lang="ts">
	import { onMount } from 'svelte';
	import { apiService } from '$lib/services/api';
	import { getMonthOptions } from '$lib/utils/dateHelpers';

	// Types
	type MonthStats = {
		totalSubmissions: number;
		completedWeeks: number;
		pendingWeeks: number;
		uniqueUsers: number;
		weeklyCompletion: { week: number; completed: number; total: number }[];
	};

	type UserSubmission = {
		userId: string;
		userName: string;
		email: string;
		completedWeeks: number;
		totalWeeks: number;
		lastActivity: string;
		status: 'complete' | 'partial' | 'none';
	};

	const monthOptions = getMonthOptions();
	// State
	let selectedMonth = $state(monthOptions[0]);
	let monthStats = $state<MonthStats | null>(null);
	let userSubmissions = $state<UserSubmission[]>([]);
	let isLoading = $state(true);
	let exportLoading = $state(false);
	let searchTerm = $state('');
	let sortBy = $state<'name' | 'completion' | 'lastActivity'>('name');
	let sortDirection = $state<'asc' | 'desc'>('asc');
	let showNotifications = $state(false);
	let notificationMessage = $state('');
	let notificationType = $state<'success' | 'error'>('success');

	// Filter controls
	let filterStatus = $state<'all' | 'complete' | 'partial' | 'none'>('all');
	let showDetailedView = $state(false);

	// Reminder modal
	let showReminderModal = $state(false);
	let reminderRecipients = $state<string[]>([]);
	let reminderMessage = $state(
		'Bitte vergessen Sie nicht, Ihre Prioritäten für diese Woche einzutragen.'
	);

	// Helper functions

	// Derived states
	let filteredUsers = $derived.by(() => {
		let filtered = [...userSubmissions];

		// Apply search filter
		if (searchTerm) {
			filtered = filtered.filter((user) =>
				user.userName.toLowerCase().includes(searchTerm.toLowerCase())
			);
		}

		// Apply status filter
		if (filterStatus !== 'all') {
			filtered = filtered.filter((user) => user.status === filterStatus);
		}

		// Apply sorting
		filtered.sort((a, b) => {
			let compareValue = 0;

			switch (sortBy) {
				case 'name':
					compareValue = a.userName.localeCompare(b.userName);
					break;
				case 'completion':
					compareValue = a.completedWeeks / a.totalWeeks - b.completedWeeks / b.totalWeeks;
					break;
				case 'lastActivity':
					compareValue = new Date(b.lastActivity).getTime() - new Date(a.lastActivity).getTime();
					break;
			}

			return sortDirection === 'asc' ? compareValue : -compareValue;
		});

		return filtered;
	});

	let completionRate = $derived(
		monthStats
			? (monthStats.completedWeeks / (monthStats.completedWeeks + monthStats.pendingWeeks)) * 100
			: 0
	);

	// Data loading
	async function loadMonthData() {
		isLoading = true;
		try {
			const [stats, submissions] = await Promise.all([
				apiService.getMonthStats(selectedMonth),
				apiService.getUserSubmissions(selectedMonth)
			]);
			console.log(submissions);

			monthStats = stats;
			userSubmissions = submissions;
		} catch (error) {
			console.error('Error loading month data:', error);
			showNotification('Fehler beim Laden der Daten', 'error');
		} finally {
			isLoading = false;
		}
	}

	// Actions
	async function exportToExcel() {
		exportLoading = true;
		try {
			// Call API to generate Excel file
			const blob = await apiService.exportMonthData(selectedMonth);

			// Download the file
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `prioritaeten_${selectedMonth}.xlsx`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			window.URL.revokeObjectURL(url);

			showNotification('Export erfolgreich heruntergeladen', 'success');
		} catch (error) {
			console.error('Export error:', error);
			showNotification('Fehler beim Export', 'error');
		} finally {
			exportLoading = false;
		}
	}

	async function sendReminders() {
		try {
			const response = await apiService.sendReminders(
				reminderRecipients,
				reminderMessage,
				selectedMonth
			);

			showNotification(
				`Erinnerungen gesendet: ${response.sent} erfolgreich, ${response.failed} fehlgeschlagen`,
				response.failed > 0 ? 'error' : 'success'
			);

			showReminderModal = false;
			reminderRecipients = [];
		} catch (error) {
			console.error('Reminder error:', error);
			showNotification('Fehler beim Senden der Erinnerungen', 'error');
		}
	}

	function toggleUserSelection(userId: string) {
		const index = reminderRecipients.indexOf(userId);
		if (index === -1) {
			reminderRecipients.push(userId);
		} else {
			reminderRecipients.splice(index, 1);
		}
		reminderRecipients = [...reminderRecipients];
	}

	function selectAllIncomplete() {
		reminderRecipients = userSubmissions
			.filter((user) => user.status !== 'complete')
			.map((user) => user.userId);
	}

	function showNotification(message: string, type: 'success' | 'error') {
		notificationMessage = message;
		notificationType = type;
		showNotifications = true;
		setTimeout(() => {
			showNotifications = false;
		}, 3000);
	}

	function toggleSort(column: 'name' | 'completion' | 'lastActivity') {
		if (sortBy === column) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortBy = column;
			sortDirection = 'asc';
		}
	}

	// Lifecycle
	onMount(() => {
		loadMonthData();
	});

	// Effect to reload data when month changes
	$effect(() => {
		// Trigger data load when selectedMonth changes
		// Using a reactive statement to ensure it runs
		const month = selectedMonth;
		loadMonthData();
	});
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-7xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8">
			<h1 class="mb-2 text-3xl font-bold text-gray-800 dark:text-white">Admin Dashboard</h1>
			<p class="text-gray-600 dark:text-gray-400">
				Übersicht und Verwaltung der Prioritäten-Einreichungen
			</p>
		</div>

		<!-- Controls Bar -->
		<div class="mb-6 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
			<div class="flex flex-wrap items-center justify-between gap-4">
				<div class="flex items-center gap-4">
					<select
						bind:value={selectedMonth}
						class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
					>
						{#each monthOptions as option}
							<option value={option}>{option}</option>
						{/each}
					</select>

					<button
						onclick={loadMonthData}
						disabled={isLoading}
						class="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
					>
						{#if isLoading}
							<span class="flex items-center gap-2">
								<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24">
									<circle
										class="opacity-25"
										cx="12"
										cy="12"
										r="10"
										stroke="currentColor"
										stroke-width="4"
										fill="none"
									></circle>
									<path
										class="opacity-75"
										fill="currentColor"
										d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
									></path>
								</svg>
								Lädt...
							</span>
						{:else}
							Aktualisieren
						{/if}
					</button>
				</div>

				<div class="flex gap-3">
					<button
						onclick={() => (showReminderModal = true)}
						class="flex items-center gap-2 rounded-lg bg-yellow-600 px-4 py-2 text-white transition-colors hover:bg-yellow-700"
					>
						<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
							></path>
						</svg>
						Erinnerungen senden
					</button>

					<button
						onclick={exportToExcel}
						disabled={exportLoading}
						class="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-white transition-colors hover:bg-green-700 disabled:opacity-50"
					>
						{#if exportLoading}
							<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24">
								<circle
									class="opacity-25"
									cx="12"
									cy="12"
									r="10"
									stroke="currentColor"
									stroke-width="4"
									fill="none"
								></circle>
								<path
									class="opacity-75"
									fill="currentColor"
									d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
								></path>
							</svg>
						{:else}
							<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
								></path>
							</svg>
						{/if}
						Excel Export
					</button>
				</div>
			</div>
		</div>

		<!-- Stats Cards -->
		{#if monthStats}
			<div class="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
				<div class="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
					<div class="mb-4 flex items-center justify-between">
						<div class="rounded-lg bg-blue-100 p-3 dark:bg-blue-900">
							<svg
								class="h-6 w-6 text-blue-600 dark:text-blue-300"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
								></path>
							</svg>
						</div>
					</div>
					<h3 class="text-2xl font-bold text-gray-800 dark:text-white">{monthStats.uniqueUsers}</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400">Aktive Nutzer</p>
				</div>

				<div class="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
					<div class="mb-4 flex items-center justify-between">
						<div class="rounded-lg bg-green-100 p-3 dark:bg-green-900">
							<svg
								class="h-6 w-6 text-green-600 dark:text-green-300"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
								></path>
							</svg>
						</div>
					</div>
					<h3 class="text-2xl font-bold text-gray-800 dark:text-white">
						{monthStats.completedWeeks}
					</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400">Vollständige Wochen</p>
				</div>

				<div class="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
					<div class="mb-4 flex items-center justify-between">
						<div class="rounded-lg bg-yellow-100 p-3 dark:bg-yellow-900">
							<svg
								class="h-6 w-6 text-yellow-600 dark:text-yellow-300"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
								></path>
							</svg>
						</div>
					</div>
					<h3 class="text-2xl font-bold text-gray-800 dark:text-white">
						{monthStats.pendingWeeks}
					</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400">Ausstehende Wochen</p>
				</div>

				<div class="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
					<div class="mb-4 flex items-center justify-between">
						<div class="rounded-lg bg-purple-100 p-3 dark:bg-purple-900">
							<svg
								class="h-6 w-6 text-purple-600 dark:text-purple-300"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
								></path>
							</svg>
						</div>
					</div>
					<h3 class="text-2xl font-bold text-gray-800 dark:text-white">
						{completionRate.toFixed(1)}%
					</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400">Abschlussquote</p>
				</div>
			</div>

			<!-- Weekly Progress Chart -->
			<div class="mb-8 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
				<h2 class="mb-4 text-xl font-bold text-gray-800 dark:text-white">
					Wöchentlicher Fortschritt
				</h2>
				<div class="space-y-4">
					{#each monthStats.weeklyCompletion as week}
						<div class="flex items-center gap-4">
							<span class="w-20 text-sm font-medium text-gray-600 dark:text-gray-400"
								>Woche {week.week}</span
							>
							<div
								class="relative h-8 flex-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
							>
								<div
									class="absolute inset-y-0 left-0 flex items-center justify-end rounded-full bg-gradient-to-r from-purple-600 to-blue-600 pr-3 transition-all duration-500"
									style="width: {(week.completed / week.total) * 100}%"
								>
									<span class="text-xs font-medium text-white">
										{week.completed}/{week.total}
									</span>
								</div>
							</div>
							<span class="w-16 text-right text-sm text-gray-600 dark:text-gray-400">
								{((week.completed / week.total) * 100).toFixed(0)}%
							</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- User Table -->
		<div class="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
			<div class="mb-6">
				<h2 class="mb-4 text-xl font-bold text-gray-800 dark:text-white">Nutzerübersicht</h2>

				<!-- Filters -->
				<div class="mb-4 flex flex-wrap gap-4">
					<input
						type="text"
						bind:value={searchTerm}
						placeholder="Suche nach Name oder E-Mail..."
						class="min-w-[200px] flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
					/>

					<select
						bind:value={filterStatus}
						class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
					>
						<option value="all">Alle Status</option>
						<option value="complete">Vollständig</option>
						<option value="partial">Teilweise</option>
						<option value="none">Keine Einreichung</option>
					</select>

					<button
						onclick={() => (showDetailedView = !showDetailedView)}
						class="rounded-lg border border-gray-300 px-4 py-2 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
					>
						{showDetailedView ? 'Kompakte Ansicht' : 'Detaillierte Ansicht'}
					</button>
				</div>
			</div>

			<!-- Table -->
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="border-b border-gray-200 dark:border-gray-700">
							<th class="px-4 py-3 text-left">
								<button
									onclick={() => toggleSort('name')}
									class="flex items-center gap-1 font-semibold text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
								>
									Name
									{#if sortBy === 'name'}
										<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d={sortDirection === 'asc' ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'}
											></path>
										</svg>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-gray-700 dark:text-gray-300">E-Mail</th>
							<th class="px-4 py-3 text-left">
								<button
									onclick={() => toggleSort('completion')}
									class="flex items-center gap-1 font-semibold text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
								>
									Fortschritt
									{#if sortBy === 'completion'}
										<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d={sortDirection === 'asc' ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'}
											></path>
										</svg>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left">
								<button
									onclick={() => toggleSort('lastActivity')}
									class="flex items-center gap-1 font-semibold text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
								>
									Letzte Aktivität
									{#if sortBy === 'lastActivity'}
										<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d={sortDirection === 'asc' ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'}
											></path>
										</svg>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-gray-700 dark:text-gray-300">Status</th>
							{#if showDetailedView}
								<th class="px-4 py-3 text-left text-gray-700 dark:text-gray-300">Aktionen</th>
							{/if}
						</tr>
					</thead>
					<tbody>
						{#each filteredUsers as user (user.userId)}
							<tr
								class="border-b border-gray-100 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50"
							>
								<td class="px-4 py-3 font-medium text-gray-800 dark:text-gray-200"
									>{user.userName}</td
								>
								<td class="px-4 py-3 text-gray-600 dark:text-gray-400">{user.email}</td>
								<td class="px-4 py-3">
									<div class="flex items-center gap-2">
										<div class="h-2 w-32 rounded-full bg-gray-200 dark:bg-gray-700">
											<div
												class="h-full rounded-full transition-all duration-300
												{user.status === 'complete'
													? 'bg-green-500'
													: user.status === 'partial'
														? 'bg-yellow-500'
														: 'bg-gray-400'}"
												style="width: {(user.completedWeeks / user.totalWeeks) * 100}%"
											></div>
										</div>
										<span class="text-sm text-gray-600 dark:text-gray-400">
											{user.completedWeeks}/{user.totalWeeks}
										</span>
									</div>
								</td>
								<td class="px-4 py-3 text-gray-600 dark:text-gray-400">
									{new Date(user.lastActivity).toLocaleDateString('de-DE')}
								</td>
								<td class="px-4 py-3">
									<span
										class="inline-flex rounded-full px-2 py-1 text-xs font-medium
										{user.status === 'complete'
											? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
											: user.status === 'partial'
												? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
												: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}"
									>
										{user.status === 'complete'
											? 'Vollständig'
											: user.status === 'partial'
												? 'Teilweise'
												: 'Ausstehend'}
									</span>
								</td>
								{#if showDetailedView}
									<td class="px-4 py-3">
										<button
											onclick={() => console.log('View details for', user.userId)}
											class="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
										>
											Details
										</button>
									</td>
								{/if}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</div>

	<!-- Reminder Modal -->
	{#if showReminderModal}
		<div class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4">
			<div
				class="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-800"
			>
				<div class="mb-6 flex items-center justify-between">
					<h3 class="text-xl font-bold text-gray-800 dark:text-white">Erinnerungen senden</h3>
					<button
						aria-label="Fenster schließen"
						onclick={() => (showReminderModal = false)}
						class="rounded-lg p-2 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
					>
						<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</button>
				</div>

				<div class="mb-4">
					<label
						for="reminder-message"
						class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
					>
						Nachricht
					</label>
					<textarea
						bind:value={reminderMessage}
						id="reminder-message"
						rows="3"
						class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
					></textarea>
				</div>

				<div class="mb-4">
					<div class="mb-2 flex items-center justify-between">
						<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
							Empfänger auswählen
						</span>
						<button
							onclick={selectAllIncomplete}
							class="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
						>
							Alle unvollständigen auswählen
						</button>
					</div>

					<div
						class="max-h-64 overflow-y-auto rounded-lg border border-gray-300 dark:border-gray-600"
					>
						{#each userSubmissions as user (user.userId)}
							<label
								class="flex cursor-pointer items-center gap-3 border-b border-gray-100 p-3 last:border-0 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700"
							>
								<input
									type="checkbox"
									checked={reminderRecipients.includes(user.userId)}
									onchange={() => toggleUserSelection(user.userId)}
									class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
								/>
								<div class="flex-1">
									<div class="font-medium text-gray-800 dark:text-gray-200">{user.userName}</div>
									<div class="text-sm text-gray-500 dark:text-gray-400">{user.email}</div>
								</div>
								<span
									class="rounded-full px-2 py-1 text-xs
									{user.status === 'complete'
										? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
										: user.status === 'partial'
											? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
											: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}"
								>
									{user.completedWeeks}/{user.totalWeeks} Wochen
								</span>
							</label>
						{/each}
					</div>
				</div>

				<div class="flex justify-end gap-3">
					<button
						onclick={() => (showReminderModal = false)}
						class="rounded-lg border border-gray-300 px-4 py-2 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
					>
						Abbrechen
					</button>
					<button
						onclick={sendReminders}
						disabled={reminderRecipients.length === 0}
						class="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
					>
						An {reminderRecipients.length} Nutzer senden
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Notifications -->
	{#if showNotifications}
		<div class="fixed right-4 bottom-4 z-50">
			<div
				class="flex items-center gap-3 rounded-lg p-4 shadow-lg
				{notificationType === 'success' ? 'bg-green-500' : 'bg-red-500'} text-white"
			>
				{#if notificationType === 'success'}
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"
						></path>
					</svg>
				{:else}
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						></path>
					</svg>
				{/if}
				<span>{notificationMessage}</span>
			</div>
		</div>
	{/if}
</div>
