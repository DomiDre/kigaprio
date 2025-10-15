<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiService } from '$lib/services/api';
	import { getMonthOptions } from '$lib/utils/dateHelpers';

	// Types
	type UserSubmission = {
		userId: string;
		userName: string;
		completedWeeks: number;
		totalWeeks: number;
		lastActivity: string;
		status: 'complete' | 'partial' | 'none';
	};

	const monthOptions = getMonthOptions();
	// State
	let selectedMonth = $state(monthOptions[0]);
	let userSubmissions = $state<UserSubmission[]>([]);
	let isLoading = $state(true);
	let searchTerm = $state('');
	let sortBy = $state<'name' | 'completion' | 'lastActivity'>('name');
	let sortDirection = $state<'asc' | 'desc'>('asc');
	let showNotifications = $state(false);
	let notificationMessage = $state('');
	let notificationType = $state<'success' | 'error'>('success');

	let isAdmin = $state(false);

	// Admin verification state
	let isVerifying = $state(true);
	let accessDenied = $state(false);

	// Filter controls
	let filterStatus = $state<'all' | 'complete' | 'partial' | 'none'>('all');
	let showDetailedView = $state(false);

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

	// Admin verification on mount
	onMount(async () => {
		// Quick check before even trying API
		if (!isAdmin) {
			goto('/dashboard');
			return;
		}

		// Verify with backend
		try {
			// Try to call an admin endpoint to verify access
			await apiService.getMagicWordInfo();
			isVerifying = false;
			// Load initial data after verification
			loadMonthData();
		} catch (error: any) {
			console.error('Admin verification failed:', error);
			if (
				error.message?.includes('Berechtigung') ||
				error.message?.includes('Keine') ||
				error.message?.includes('access')
			) {
				// 403 error - not actually an admin
				accessDenied = true;
				setTimeout(() => goto('/dashboard'), 2000);
			} else {
				// Other error, show it but don't redirect
				isVerifying = false;
				showNotification('Fehler bei der Verifizierung: ' + error.message, 'error');
			}
		}
	});

	// Data loading
	async function loadMonthData() {
		isLoading = true;
		try {
			const submissions = await apiService.getUserSubmissions(selectedMonth);
			userSubmissions = submissions;
		} catch (error) {
			console.error('Error loading month data:', error);
			showNotification('Fehler beim Laden der Daten', 'error');
		} finally {
			isLoading = false;
		}
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

	// Effect to reload data when month changes
	$effect(() => {
		// Only load data if we're verified and not in access denied state
		if (!isVerifying && !accessDenied) {
			void selectedMonth;
			loadMonthData();
		}
	});
</script>

{#if isVerifying}
	<div
		class="flex min-h-screen items-center justify-center bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="text-center">
			<div class="mb-4 flex justify-center">
				<svg class="h-12 w-12 animate-spin text-purple-600" viewBox="0 0 24 24">
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
			</div>
			<p class="text-lg text-gray-700 dark:text-gray-300">Überprüfe Berechtigungen...</p>
		</div>
	</div>
{:else if accessDenied}
	<div
		class="flex min-h-screen items-center justify-center bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="rounded-xl bg-white p-8 text-center shadow-lg dark:bg-gray-800">
			<svg
				class="mx-auto mb-4 h-16 w-16 text-red-600"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
				></path>
			</svg>
			<p class="mb-2 text-xl font-bold text-red-600">Zugriff verweigert</p>
			<p class="mb-4 text-gray-600 dark:text-gray-400">
				Sie haben keine Administratorrechte für diese Seite.
			</p>
			<p class="text-sm text-gray-500 dark:text-gray-500">Sie werden weitergeleitet...</p>
		</div>
	</div>
{:else}
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-7xl px-4 py-8">
			<!-- Header with Navigation -->
			<div class="mb-8 flex items-start justify-between">
				<div>
					<h1 class="mb-2 text-3xl font-bold text-gray-800 dark:text-white">Admin Dashboard</h1>
					<p class="text-gray-600 dark:text-gray-400">
						Übersicht und Verwaltung der Prioritäten-Einreichungen
					</p>
				</div>

				<!-- Navigation Buttons -->
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

					<a
						href="/dashboard"
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
								d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
							/>
						</svg>
						Dashboard
					</a>
				</div>
			</div>

			<!-- Controls Bar -->
			<div class="mb-6 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
				<div class="flex flex-wrap items-center justify-between gap-4">
					<div class="flex items-center gap-4">
						<select
							bind:value={selectedMonth}
							class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
						>
							{#each monthOptions as option (option)}
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
				</div>
			</div>

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

		<!-- Notifications -->
		{#if showNotifications}
			<div class="fixed right-4 bottom-4 z-50">
				<div
					class="flex items-center gap-3 rounded-lg p-4 shadow-lg
					{notificationType === 'success' ? 'bg-green-500' : 'bg-red-500'} text-white"
				>
					{#if notificationType === 'success'}
						<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M5 13l4 4L19 7"
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
{/if}
