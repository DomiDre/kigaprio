<script lang="ts">
	import { onMount } from 'svelte';
	import AccountGroup from 'virtual:icons/mdi/account-group';
	import CheckCircle from 'virtual:icons/mdi/check-circle';
	import ClockOutline from 'virtual:icons/mdi/clock-outline';
	import TrendingUp from 'virtual:icons/mdi/trending-up';
	import KeyVariant from 'virtual:icons/mdi/key-variant';
	import Upload from 'virtual:icons/mdi/upload';
	import Download from 'virtual:icons/mdi/download';
	import Plus from 'virtual:icons/mdi/plus';
	import Magnify from 'virtual:icons/mdi/magnify';
	import Close from 'virtual:icons/mdi/close';
	import Lock from 'virtual:icons/mdi/lock';
	import Alert from 'virtual:icons/mdi/alert';
	import ChevronDown from 'virtual:icons/mdi/chevron-down';
	import ChevronUp from 'virtual:icons/mdi/chevron-up';
	import { apiService } from '$lib/services/api';
	import { cryptoService } from '$lib/services/crypto';
	import DecryptedDataModal from '$lib/components/DecryptedDataModal.svelte';
	import type { DecryptedData, UserDisplay, UserPriorityRecord } from '$lib/types/dashboard';
	import { dayKeys, dayLabels, priorityColors } from '$lib/config/priorities';

	// State
	let selectedMonth = $state('2025-10');
	let keyUploaded = $state(false);
	let showManualEntry = $state(false);
	let searchQuery = $state('');
	let keyFile = $state<File | null>(null);
	let isLoading = $state(true);
	let error = $state('');
	let decryptionError = $state('');
	let showOverview = $state(false);

	// Decryption state
	let isDecrypting = $state(false);
	let isDecryptingAll = $state(false);
	let showDecryptedModal = $state(false);
	let decryptedData = $state<DecryptedData | null>(null);
	let decryptedUsers = $state(new Map<string, { name: string; userData: any; priorities: any }>());

	// Data
	let userSubmissions = $state<UserPriorityRecord[]>([]);
	let users = $state<UserDisplay[]>([]);

	// Calculate statistics reactively using $derived
	let stats = $derived.by(() => {
		const totalUsers = users.length;
		const submitted = users.filter((u) => u.submitted && u.hasData).length;
		const pending = totalUsers - submitted;
		const submissionRate = totalUsers > 0 ? Math.round((submitted / totalUsers) * 100) : 0;

		return {
			totalUsers,
			submitted,
			pending,
			submissionRate
		};
	});

	// Passphrase state
	let passphraseInput = $state('');
	let showPassphrasePrompt = $state(false);
	let pendingKeyFile = $state<File | null>(null);

	// Track if initial fetch is done
	let initialFetchDone = $state(false);

	// Build overview data structure using $derived
	let overviewData = $derived.by(() => {
		console.log('Building overview data, decryptedUsers size:', decryptedUsers.size);
		if (decryptedUsers.size === 0) return [];

		const data: any[] = [];

		decryptedUsers.forEach((userData) => {
			const weeks = userData.priorities?.weeks || [];

			data.push({
				userName: userData.name,
				weeks: weeks.map((week: any) => ({
					weekNumber: week.weekNumber,
					priorities: dayKeys.map((day) => week[day] || null)
				}))
			});
		});

		const sorted = data.sort((a, b) => a.userName.localeCompare(b.userName));
		console.log('Overview data built:', sorted.length, 'users');
		return sorted;
	});

	// Get all unique weeks across all users
	let allWeeks = $derived.by(() => {
		const weekSet = new Set<number>();
		decryptedUsers.forEach((userData) => {
			const weeks = userData.priorities?.weeks || [];
			weeks.forEach((week: any) => {
				weekSet.add(week.weekNumber);
			});
		});
		const weeks = Array.from(weekSet).sort((a, b) => a - b);
		console.log('All weeks:', weeks);
		return weeks;
	});

	// Calculate demand statistics
	let demandStats = $derived.by(() => {
		const stats: Record<number, Record<string, Record<number, number>>> = {};

		decryptedUsers.forEach((userData) => {
			const weeks = userData.priorities?.weeks || [];
			weeks.forEach((week: any) => {
				if (!stats[week.weekNumber]) {
					stats[week.weekNumber] = {};
					dayKeys.forEach((day) => {
						stats[week.weekNumber][day] = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
					});
				}

				dayKeys.forEach((day) => {
					const priority = week[day];
					if (priority) {
						stats[week.weekNumber][day][priority]++;
					}
				});
			});
		});

		console.log('Demand stats calculated for', Object.keys(stats).length, 'weeks');
		return stats;
	});

	// Fetch user submissions from API
	async function fetchUserSubmissions() {
		isLoading = true;
		error = '';

		try {
			const data = await apiService.getUserSubmissions(selectedMonth);
			userSubmissions = data;

			// Transform API data into display format
			users = userSubmissions.map((submission, index) => ({
				id: index + 1,
				name: submission.userName,
				submitted: true,
				encrypted: true,
				hasData: !!submission.prioritiesEncryptedFields,
				adminWrappedDek: submission.adminWrappedDek,
				userEncryptedFields: submission.userEncryptedFields,
				prioritiesEncryptedFields: submission.prioritiesEncryptedFields
			}));

			// If key is already uploaded, decrypt all data
			if (keyUploaded) {
				await decryptAllUsers();
			}
		} catch (err) {
			error = (err as Error).message;
			console.error('Error fetching submissions:', err);
		} finally {
			isLoading = false;
		}
	}

	// Decrypt all users' data automatically
	async function decryptAllUsers() {
		if (!keyUploaded || users.length === 0 || isDecryptingAll) return;

		console.log('Starting decryption of', users.length, 'users');
		isDecryptingAll = true;
		decryptionError = '';

		// Create a new map for the decrypted data
		const newDecryptedUsers = new Map();

		try {
			for (const user of users) {
				if (user.adminWrappedDek && user.userEncryptedFields && user.prioritiesEncryptedFields) {
					try {
						const result = await cryptoService.decryptUserData(
							user.adminWrappedDek,
							user.userEncryptedFields,
							user.prioritiesEncryptedFields
						);

						newDecryptedUsers.set(user.name, {
							name: result.userData.name || user.name,
							userData: result.userData,
							priorities: result.priorities
						});
					} catch (err) {
						console.error(`Failed to decrypt data for ${user.name}:`, err);
					}
				}
			}

			// Update the state once with all decrypted data
			decryptedUsers = newDecryptedUsers;
			console.log('Decryption complete:', decryptedUsers.size, 'users decrypted');
			showOverview = true; // Auto-show overview when decryption completes
		} catch (err) {
			console.error('Error during batch decryption:', err);
			decryptionError = 'Einige Daten konnten nicht entschlüsselt werden';
		} finally {
			isDecryptingAll = false;
		}
	}

	// Get decrypted name for display
	function getDisplayName(userName: string): string {
		const decrypted = decryptedUsers.get(userName);
		return decrypted?.name || userName;
	}

	// Filter users based on search query using $derived
	let filteredUsers = $derived.by(() => {
		return users.filter((user) => {
			const displayName = getDisplayName(user.name);
			return displayName.toLowerCase().includes(searchQuery.toLowerCase());
		});
	});

	// Fetch data on mount
	onMount(() => {
		fetchUserSubmissions();
		initialFetchDone = true;
	});

	// Watch for month changes using $effect (skip initial run)
	$effect(() => {
		if (initialFetchDone && selectedMonth) {
			console.log('Month changed to:', selectedMonth);
			// Clear decrypted data when month changes
			decryptedUsers = new Map();
			showOverview = false;
			fetchUserSubmissions();
		}
	});

	async function handleKeyUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files[0]) {
			keyFile = input.files[0];
			decryptionError = '';

			try {
				await cryptoService.loadPrivateKey(keyFile);
				keyUploaded = true;
				await decryptAllUsers();
			} catch (err) {
				const error = err as Error;

				if (error.message.includes('passphrase-protected')) {
					pendingKeyFile = keyFile;
					keyFile = null;
					showPassphrasePrompt = true;
				} else {
					decryptionError = error.message;
					keyFile = null;
				}
			}
		}
	}

	async function submitPassphrase() {
		if (!pendingKeyFile || !passphraseInput) return;

		try {
			await cryptoService.loadPrivateKey(pendingKeyFile, passphraseInput);
			keyFile = pendingKeyFile;
			keyUploaded = true;
			showPassphrasePrompt = false;
			passphraseInput = '';
			pendingKeyFile = null;
			await decryptAllUsers();
		} catch (err) {
			decryptionError = 'Incorrect passphrase or invalid key';
		}
	}

	function cancelPassphrase() {
		showPassphrasePrompt = false;
		passphraseInput = '';
		pendingKeyFile = null;
	}

	async function handleKeyDrop(event: DragEvent) {
		event.preventDefault();
		if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
			keyFile = event.dataTransfer.files[0];
			decryptionError = '';

			try {
				await cryptoService.loadPrivateKey(keyFile);
				keyUploaded = true;
				await decryptAllUsers();
			} catch (err) {
				const error = err as Error;

				if (error.message.includes('passphrase-protected')) {
					pendingKeyFile = keyFile;
					keyFile = null;
					showPassphrasePrompt = true;
				} else {
					decryptionError = error.message;
					keyFile = null;
				}
			}
		}
	}

	function preventDefaults(event: DragEvent) {
		event.preventDefault();
	}

	function removeKey() {
		keyUploaded = false;
		keyFile = null;
		cryptoService.clearKey();
		decryptionError = '';
		decryptedUsers = new Map();
		showOverview = false;
	}

	async function viewUserData(user: UserDisplay) {
		if (!keyUploaded) {
			decryptionError = 'Bitte laden Sie zuerst den privaten Schlüssel hoch';
			return;
		}

		const cached = decryptedUsers.get(user.name);
		if (cached) {
			decryptedData = {
				userName: cached.name,
				userData: cached.userData,
				priorities: cached.priorities
			};
			showDecryptedModal = true;
			return;
		}

		if (!user.adminWrappedDek || !user.userEncryptedFields || !user.prioritiesEncryptedFields) {
			decryptionError = 'Unvollständige Daten für diesen Benutzer';
			return;
		}

		isDecrypting = true;
		decryptionError = '';

		try {
			const result = await cryptoService.decryptUserData(
				user.adminWrappedDek,
				user.userEncryptedFields,
				user.prioritiesEncryptedFields
			);

			decryptedUsers.set(user.name, {
				name: result.userData.name || user.name,
				userData: result.userData,
				priorities: result.priorities
			});
			decryptedUsers = decryptedUsers;

			decryptedData = {
				userName: result.userData.name || user.name,
				userData: result.userData,
				priorities: result.priorities
			};
			showDecryptedModal = true;
		} catch (err) {
			console.error('Decryption error:', err);
			decryptionError = (err as Error).message;
		} finally {
			isDecrypting = false;
		}
	}

	function closeDecryptedModal() {
		showDecryptedModal = false;
		decryptedData = null;
	}

	function exportToExcel() {
		console.log('Exporting to Excel...');
		alert('Excel-Export wird noch implementiert');
	}

	function openManualEntry() {
		showManualEntry = true;
	}

	function closeManualEntry() {
		showManualEntry = false;
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<!-- Header -->
	<div class="border-b bg-white shadow-md dark:bg-gray-800">
		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-3xl font-bold text-gray-800 dark:text-white">Admin Dashboard</h1>
					<p class="mt-1 text-sm text-gray-600 dark:text-gray-300">
						Manage user submissions and export data
					</p>
				</div>
				<div class="flex items-center gap-4">
					<select
						bind:value={selectedMonth}
						class="rounded-lg border border-gray-300 px-4 py-2 shadow-sm focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
					>
						<option value="2025-10">October 2025</option>
						<option value="2025-09">September 2025</option>
						<option value="2025-08">August 2025</option>
					</select>
				</div>
			</div>
		</div>
	</div>

	<div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
		<!-- Error Display -->
		{#if error}
			<div
				class="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
			>
				<div class="flex items-start gap-2">
					<Alert class="h-5 w-5 text-red-600 dark:text-red-400" />
					<p class="text-sm text-red-800 dark:text-red-400">{error}</p>
				</div>
			</div>
		{/if}

		<!-- Decryption Error Display -->
		{#if decryptionError}
			<div
				class="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
			>
				<div class="flex items-start gap-2">
					<Alert class="h-5 w-5 text-red-600 dark:text-red-400" />
					<div class="flex-1">
						<p class="text-sm font-medium text-red-900 dark:text-red-300">Entschlüsselungsfehler</p>
						<p class="text-sm text-red-800 dark:text-red-400">{decryptionError}</p>
					</div>
					<button
						type="button"
						class="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
						onclick={() => (decryptionError = '')}
					>
						<Close class="h-5 w-5" />
					</button>
				</div>
			</div>
		{/if}

		<!-- Decryption Progress -->
		{#if isDecryptingAll}
			<div
				class="mb-6 rounded-lg border border-purple-200 bg-purple-50 p-4 dark:border-purple-800 dark:bg-purple-900/20"
			>
				<div class="flex items-center gap-3">
					<div
						class="h-5 w-5 animate-spin rounded-full border-2 border-purple-600 border-t-transparent"
					></div>
					<p class="text-sm font-medium text-purple-900 dark:text-purple-300">
						Entschlüssele Benutzerdaten... ({decryptedUsers.size}/{users.length})
					</p>
				</div>
			</div>
		{/if}

		<!-- Loading State -->
		{#if isLoading}
			<div class="flex items-center justify-center py-12">
				<div class="text-center">
					<div
						class="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-4 border-purple-200 border-t-purple-600 dark:border-purple-900 dark:border-t-purple-400"
					></div>
					<p class="text-gray-600 dark:text-gray-300">Lade Daten...</p>
				</div>
			</div>
		{:else}
			<!-- Statistics Cards -->
			<div class="mb-8 grid grid-cols-1 gap-6 md:grid-cols-4">
				<!-- Total Users -->
				<div
					class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm font-medium text-gray-600 dark:text-gray-300">Total Users</p>
							<p class="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
								{stats.totalUsers}
							</p>
						</div>
						<div
							class="rounded-lg bg-gradient-to-br from-purple-100 to-blue-100 p-3 dark:from-purple-900/30 dark:to-blue-900/30"
						>
							<AccountGroup class="h-6 w-6 text-purple-600 dark:text-purple-400" />
						</div>
					</div>
				</div>

				<!-- Submitted -->
				<div
					class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm font-medium text-gray-600 dark:text-gray-300">Submitted</p>
							<p class="mt-2 text-3xl font-bold text-green-600 dark:text-green-400">
								{stats.submitted}
							</p>
						</div>
						<div class="rounded-lg bg-green-50 p-3 dark:bg-green-900/30">
							<CheckCircle class="h-6 w-6 text-green-600 dark:text-green-400" />
						</div>
					</div>
				</div>

				<!-- Pending -->
				<div
					class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm font-medium text-gray-600 dark:text-gray-300">Pending</p>
							<p class="mt-2 text-3xl font-bold text-orange-600 dark:text-orange-400">
								{stats.pending}
							</p>
						</div>
						<div class="rounded-lg bg-orange-50 p-3 dark:bg-orange-900/30">
							<ClockOutline class="h-6 w-6 text-orange-600 dark:text-orange-400" />
						</div>
					</div>
				</div>

				<!-- Submission Rate -->
				<div
					class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm font-medium text-gray-600 dark:text-gray-300">Submission Rate</p>
							<p class="mt-2 text-3xl font-bold text-purple-600 dark:text-purple-400">
								{stats.submissionRate}%
							</p>
						</div>
						<div
							class="rounded-lg bg-gradient-to-br from-purple-100 to-blue-100 p-3 dark:from-purple-900/30 dark:to-blue-900/30"
						>
							<TrendingUp class="h-6 w-6 text-purple-600 dark:text-purple-400" />
						</div>
					</div>
				</div>
			</div>

			<!-- Priorities Overview Table -->
			{#if keyUploaded && decryptedUsers.size > 0}
				<div
					class="mb-8 rounded-xl border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-800"
				>
					<div class="border-b border-gray-200 p-6 dark:border-gray-700">
						<button
							type="button"
							class="flex w-full items-center justify-between"
							onclick={() => (showOverview = !showOverview)}
						>
							<div class="flex items-center gap-3">
								<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
									Priorities Overview
								</h2>
								<span
									class="rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
								>
									{decryptedUsers.size} users
								</span>
							</div>
							{#if showOverview}
								<ChevronUp class="h-5 w-5 text-gray-600 dark:text-gray-400" />
							{:else}
								<ChevronDown class="h-5 w-5 text-gray-600 dark:text-gray-400" />
							{/if}
						</button>
					</div>

					{#if showOverview}
						<div class="overflow-x-auto p-6">
							<!-- Legend -->
							<div class="mb-6 flex flex-wrap gap-4">
								<div class="flex items-center gap-2">
									<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Priority:</span
									>
								</div>
								{#each [1, 2, 3, 4, 5] as priority}
									<div class="flex items-center gap-2">
										<div
											class="h-4 w-4 rounded {priorityColors[
												priority as 1 | 2 | 3 | 4 | 5
											]} text-white"
										></div>
										<span class="text-xs text-gray-600 dark:text-gray-400">{priority}</span>
									</div>
								{/each}
							</div>

							<!-- Overview Table -->
							<table class="w-full border-collapse">
								<thead>
									<tr class="border-b-2 border-gray-300 dark:border-gray-600">
										<th
											class="sticky left-0 bg-white px-4 py-3 text-left text-sm font-semibold text-gray-900 dark:bg-gray-800 dark:text-white"
										>
											User
										</th>
										{#each allWeeks as weekNum}
											<th
												class="border-l border-gray-200 px-2 py-3 text-center dark:border-gray-700"
												colspan="5"
											>
												<div class="text-xs font-semibold text-gray-700 dark:text-gray-300">
													Week {weekNum}
												</div>
												<div class="mt-1 flex justify-around">
													{#each dayLabels as day}
														<span class="text-xs text-gray-500 dark:text-gray-400">{day}</span>
													{/each}
												</div>
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each overviewData as userData}
										<tr
											class="border-b border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50"
										>
											<td
												class="sticky left-0 bg-white px-4 py-3 font-medium text-gray-900 dark:bg-gray-800 dark:text-white"
											>
												<div class="flex items-center gap-2">
													<div
														class="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-purple-400 to-blue-600 text-sm font-semibold text-white"
													>
														{userData.userName.charAt(0).toUpperCase()}
													</div>
													<span class="text-sm">{userData.userName}</span>
												</div>
											</td>
											{#each allWeeks as weekNum}
												{@const week = userData.weeks.find((w: any) => w.weekNumber === weekNum)}
												{#if week}
													{#each week.priorities as priority}
														<td
															class="border-l border-gray-200 px-2 py-3 text-center dark:border-gray-700"
														>
															{#if priority}
																<div
																	class="mx-auto flex h-8 w-8 items-center justify-center rounded-md text-sm font-semibold {priorityColors[
																		priority as 1 | 2 | 3 | 4 | 5
																	]}"
																>
																	{priority}
																</div>
															{:else}
																<div
																	class="mx-auto h-8 w-8 rounded-md bg-gray-100 dark:bg-gray-700"
																></div>
															{/if}
														</td>
													{/each}
												{:else}
													{#each [1, 2, 3, 4, 5] as _}
														<td
															class="border-l border-gray-200 px-2 py-3 text-center dark:border-gray-700"
														>
															<div
																class="mx-auto h-8 w-8 rounded-md bg-gray-100 dark:bg-gray-700"
															></div>
														</td>
													{/each}
												{/if}
											{/each}
										</tr>
									{/each}
								</tbody>
							</table>

							<!-- Demand Statistics -->
							<div class="mt-8 border-t border-gray-200 pt-6 dark:border-gray-700">
								<h3 class="mb-4 text-sm font-semibold text-gray-900 dark:text-white">
									Demand per Day
								</h3>
								<div class="space-y-4">
									{#each allWeeks as weekNum}
										<div
											class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50"
										>
											<div class="mb-2 text-xs font-semibold text-gray-700 dark:text-gray-300">
												Week {weekNum}
											</div>
											<div class="grid grid-cols-5 gap-2">
												{#each dayKeys as day, dayIndex}
													{@const dayStat = demandStats[weekNum]?.[day]}
													<div
														class="rounded-md border border-gray-200 bg-white p-2 dark:border-gray-600 dark:bg-gray-800"
													>
														<div
															class="mb-1 text-center text-xs font-medium text-gray-600 dark:text-gray-400"
														>
															{dayLabels[dayIndex]}
														</div>
														{#if dayStat}
															<div class="space-y-1">
																{#each [1, 2, 3, 4, 5] as priority}
																	{#if dayStat[priority] > 0}
																		<div class="flex items-center gap-1 text-xs">
																			<div
																				class="h-3 w-3 rounded {priorityColors[
																					priority as 1 | 2 | 3 | 4 | 5
																				]}"
																			></div>
																			<span class="text-gray-700 dark:text-gray-300"
																				>{dayStat[priority]}</span
																			>
																		</div>
																	{/if}
																{/each}
															</div>
														{:else}
															<div class="text-center text-xs text-gray-400">-</div>
														{/if}
													</div>
												{/each}
											</div>
										</div>
									{/each}
								</div>
							</div>
						</div>
					{/if}
				</div>
			{/if}

			<div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
				<!-- Main Content Area -->
				<div class="space-y-6 lg:col-span-2">
					<!-- Private Key Upload -->
					<div
						class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
					>
						<div class="mb-4 flex items-center gap-2">
							<KeyVariant class="h-5 w-5 text-gray-700 dark:text-gray-300" />
							<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Private Key</h2>
						</div>

						{#if showPassphrasePrompt}
							<!-- Passphrase Input -->
							<div
								class="rounded-lg border-2 border-purple-300 bg-gradient-to-br from-purple-50 to-blue-50 p-6 dark:border-purple-700 dark:from-purple-900/30 dark:to-blue-900/30"
							>
								<div class="mb-4 text-center">
									<p class="text-sm font-medium text-gray-900 dark:text-white">
										This key is passphrase-protected
									</p>
									<p class="mt-1 text-xs text-gray-600 dark:text-gray-400">
										Enter your passphrase to decrypt the private key
									</p>
								</div>

								<input
									type="password"
									bind:value={passphraseInput}
									placeholder="Enter passphrase"
									class="mb-4 w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
									onkeypress={(e) => e.key === 'Enter' && submitPassphrase()}
								/>

								<div class="flex gap-3">
									<button
										type="button"
										class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
										onclick={cancelPassphrase}
									>
										Cancel
									</button>
									<button
										type="button"
										class="flex-1 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 font-semibold text-white shadow-lg transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
										onclick={submitPassphrase}
										disabled={!passphraseInput}
									>
										Unlock Key
									</button>
								</div>
							</div>
						{:else}
							<!-- Normal upload area -->
							<div
								class="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center transition-colors hover:border-purple-400 hover:bg-purple-50 dark:border-gray-600 dark:hover:border-purple-600 dark:hover:bg-purple-900/20"
								ondrop={handleKeyDrop}
								ondragover={preventDefaults}
								ondragenter={preventDefaults}
								role="region"
								aria-label="Private key file drop zone to locally decrypt data"
							>
								<input
									type="file"
									id="keyFileInput"
									accept=".pem,.key"
									class="hidden"
									onchange={handleKeyUpload}
								/>

								{#if keyUploaded && keyFile}
									<div class="flex flex-col items-center">
										<div class="mb-3 rounded-full bg-green-50 p-3 dark:bg-green-900/30">
											<CheckCircle class="h-8 w-8 text-green-600 dark:text-green-400" />
										</div>
										<p class="text-sm font-medium text-gray-900 dark:text-white">{keyFile.name}</p>
										<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
											Private key loaded successfully
										</p>
										{#if decryptedUsers.size > 0}
											<p class="mt-2 text-xs font-medium text-purple-600 dark:text-purple-400">
												✓ {decryptedUsers.size} user(s) decrypted
											</p>
										{/if}
										<button
											type="button"
											class="mt-4 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
											onclick={removeKey}
										>
											Remove Key
										</button>
									</div>
								{:else}
									<div class="flex flex-col items-center">
										<Upload class="mb-3 h-12 w-12 text-gray-400 dark:text-gray-500" />
										<p class="mb-1 text-sm font-medium text-gray-900 dark:text-white">
											Drop your private key file here
										</p>
										<p class="mb-4 text-xs text-gray-500 dark:text-gray-400">or</p>
										<label
											for="keyFileInput"
											class="cursor-pointer rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 font-semibold text-white shadow-lg transition-all hover:scale-105"
										>
											Browse Files
										</label>
										<p class="mt-2 text-xs text-gray-400 dark:text-gray-500">
											Accepts .pem or .key files
										</p>
									</div>
								{/if}
							</div>
						{/if}

						{#if keyUploaded}
							<div
								class="mt-4 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20"
							>
								<p class="text-sm text-green-800 dark:text-green-400">
									✓ Key loaded. Data decrypted and overview available above.
								</p>
							</div>
						{:else}
							<div
								class="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-900/20"
							>
								<p class="text-sm text-yellow-800 dark:text-yellow-400">
									⚠ Upload your private key to decrypt and view submission data.
								</p>
							</div>
						{/if}
					</div>

					<!-- User Submissions Table -->
					<div
						class="rounded-xl border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-800"
					>
						<div class="border-b border-gray-200 p-6 dark:border-gray-700">
							<div class="mb-4 flex items-center justify-between">
								<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
									User Submissions
								</h2>
								<div class="flex items-center gap-3">
									<div class="relative">
										<Magnify
											class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 transform text-gray-400"
										/>
										<input
											type="text"
											bind:value={searchQuery}
											placeholder="Search users..."
											class="rounded-lg border border-gray-300 py-2 pr-4 pl-10 text-sm focus:border-purple-500 focus:ring-2 focus:ring-purple-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="overflow-x-auto">
							<table class="w-full">
								<thead
									class="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/50"
								>
									<tr>
										<th
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase dark:text-gray-400"
										>
											User
										</th>
										<th
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase dark:text-gray-400"
										>
											Status
										</th>
										<th
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase dark:text-gray-400"
										>
											Encryption
										</th>
										<th
											class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase dark:text-gray-400"
										>
											Actions
										</th>
									</tr>
								</thead>
								<tbody
									class="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800"
								>
									{#if filteredUsers.length === 0}
										<tr>
											<td
												colspan="4"
												class="px-6 py-8 text-center text-gray-500 dark:text-gray-400"
											>
												{#if users.length === 0}
													Keine Einreichungen für diesen Monat gefunden
												{:else}
													Keine Benutzer gefunden für "{searchQuery}"
												{/if}
											</td>
										</tr>
									{:else}
										{#each filteredUsers as user}
											{@const displayName = getDisplayName(user.name)}
											{@const isDecrypted = decryptedUsers.has(user.name)}
											<tr class="transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/50">
												<td class="px-6 py-4 whitespace-nowrap">
													<div class="flex items-center">
														<div
															class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-purple-400 to-blue-600 font-semibold text-white"
														>
															{displayName.charAt(0).toUpperCase()}
														</div>
														<div class="ml-3">
															<p class="text-sm font-medium text-gray-900 dark:text-white">
																{displayName}
																{#if isDecrypted && displayName !== user.name}
																	<span class="ml-1 text-xs text-purple-600 dark:text-purple-400"
																		>✓</span
																	>
																{/if}
															</p>
															<p class="text-xs text-gray-500 dark:text-gray-400">ID: {user.id}</p>
														</div>
													</div>
												</td>
												<td class="px-6 py-4 whitespace-nowrap">
													{#if user.submitted && user.hasData}
														<span
															class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400"
														>
															<CheckCircle class="mr-1 h-3 w-3" />
															Submitted
														</span>
													{:else}
														<span
															class="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800 dark:bg-orange-900/30 dark:text-orange-400"
														>
															<ClockOutline class="mr-1 h-3 w-3" />
															Pending
														</span>
													{/if}
												</td>
												<td class="px-6 py-4 whitespace-nowrap">
													{#if user.encrypted}
														{#if isDecrypted}
															<span
																class="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
																title="Decrypted locally"
															>
																<CheckCircle class="mr-1 h-3 w-3" />
																Decrypted
															</span>
														{:else}
															<span
																class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
																title="Data is encrypted"
															>
																<Lock class="mr-1 h-3 w-3" />
																Encrypted
															</span>
														{/if}
													{:else}
														<span class="text-xs text-gray-400">No data</span>
													{/if}
												</td>
												<td class="px-6 py-4 text-sm whitespace-nowrap">
													{#if user.submitted && user.hasData && keyUploaded}
														<button
															type="button"
															class="font-medium text-purple-600 transition-colors hover:text-purple-800 disabled:cursor-not-allowed disabled:opacity-50 dark:text-purple-400 dark:hover:text-purple-300"
															onclick={() => viewUserData(user)}
															disabled={isDecrypting}
														>
															{isDecrypting ? 'Entschlüsseln...' : 'View Data'}
														</button>
													{:else if user.submitted && user.hasData && !keyUploaded}
														<span class="text-gray-400 dark:text-gray-500">Upload key first</span>
													{:else}
														<button
															type="button"
															class="font-medium text-gray-600 transition-colors hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-300"
															onclick={openManualEntry}
														>
															Enter Manually
														</button>
													{/if}
												</td>
											</tr>
										{/each}
									{/if}
								</tbody>
							</table>
						</div>
					</div>
				</div>

				<!-- Sidebar Actions -->
				<div class="space-y-6">
					<!-- Quick Actions -->
					<div
						class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
					>
						<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Quick Actions</h3>
						<div class="space-y-3">
							<button
								type="button"
								class="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-3 font-semibold text-white shadow-lg transition-all hover:scale-105"
								onclick={openManualEntry}
							>
								<Plus class="h-5 w-5" />
								Manual Entry
							</button>

							<button
								type="button"
								class="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 px-4 py-3 font-semibold text-white shadow-lg transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
								onclick={exportToExcel}
								disabled={!keyUploaded || users.length === 0}
							>
								<Download class="h-5 w-5" />
								Export to Excel
							</button>
						</div>

						{#if !keyUploaded}
							<div
								class="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-900/20"
							>
								<p class="text-xs text-yellow-800 dark:text-yellow-400">
									Upload private key to enable export
								</p>
							</div>
						{/if}
					</div>

					<!-- Monthly Overview -->
					<div
						class="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800"
					>
						<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
							Monthly Overview
						</h3>
						<div class="space-y-4">
							<div>
								<div class="mb-2 flex justify-between text-sm">
									<span class="text-gray-600 dark:text-gray-300">Completion Progress</span>
									<span class="font-medium text-gray-900 dark:text-white"
										>{stats.submissionRate}%</span
									>
								</div>
								<div class="h-2.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
									<div
										class="h-2.5 rounded-full bg-gradient-to-r from-purple-500 to-blue-600 transition-all duration-500"
										style="width: {stats.submissionRate}%"
									></div>
								</div>
							</div>

							<div class="border-t border-gray-200 pt-4 dark:border-gray-700">
								<div class="mb-2 flex items-center justify-between">
									<span class="text-sm text-gray-600 dark:text-gray-300">Encrypted Submissions</span
									>
									<span class="text-sm font-medium text-gray-900 dark:text-white"
										>{stats.submitted}</span
									>
								</div>
								<div class="flex items-center justify-between">
									<span class="text-sm text-gray-600 dark:text-gray-300">Paper Submissions</span>
									<span class="text-sm font-medium text-gray-900 dark:text-white">0</span>
								</div>
								{#if keyUploaded}
									<div
										class="mt-2 flex items-center justify-between border-t border-gray-200 pt-2 dark:border-gray-700"
									>
										<span class="text-sm text-gray-600 dark:text-gray-300">Decrypted</span>
										<span class="text-sm font-medium text-purple-600 dark:text-purple-400"
											>{decryptedUsers.size}</span
										>
									</div>
								{/if}
							</div>
						</div>
					</div>

					<!-- Data Status Info -->
					<div
						class="rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50 to-blue-50 p-6 shadow-xl dark:border-purple-700 dark:from-purple-900/30 dark:to-blue-900/30"
					>
						<h3
							class="mb-2 flex items-center gap-2 text-sm font-semibold text-purple-900 dark:text-purple-300"
						>
							<Lock class="h-4 w-4" />
							Encryption Status
						</h3>
						<p class="text-xs text-purple-800 dark:text-purple-400">
							All user data is encrypted. Upload the admin private key to decrypt and view the
							priorities overview table.
						</p>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- Decrypted Data Modal -->
{#if showDecryptedModal && decryptedData}
	<DecryptedDataModal
		userName={decryptedData.userName}
		userData={decryptedData.userData}
		priorities={decryptedData.priorities}
		onClose={closeDecryptedModal}
	/>
{/if}

<!-- Manual Entry Modal -->
{#if showManualEntry}
	<div class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4">
		<div
			class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-2xl dark:bg-gray-800"
		>
			<div class="border-b border-gray-200 p-6 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<h2 class="text-xl font-bold text-gray-900 dark:text-white">Manual Data Entry</h2>
					<button
						type="button"
						class="text-gray-400 transition-colors hover:text-gray-600 dark:hover:text-gray-300"
						onclick={closeManualEntry}
					>
						<Close class="h-6 w-6" />
					</button>
				</div>
			</div>

			<div class="space-y-4 p-6">
				<div
					class="rounded-lg border border-purple-200 bg-gradient-to-br from-purple-50 to-blue-50 p-4 dark:border-purple-700 dark:from-purple-900/30 dark:to-blue-900/30"
				>
					<p class="text-sm text-purple-800 dark:text-purple-400">
						Enter data for users who submitted on paper. This data will be encrypted with the public
						key before storage.
					</p>
				</div>

				<!-- Placeholder for data entry form -->
				<div
					class="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center dark:border-gray-600"
				>
					<p class="text-gray-500 dark:text-gray-400">Data entry form will be displayed here</p>
					<p class="mt-2 text-sm text-gray-400 dark:text-gray-500">
						This will be implemented in the next step
					</p>
				</div>
			</div>

			<div class="flex justify-end gap-3 border-t border-gray-200 p-6 dark:border-gray-700">
				<button
					type="button"
					class="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
					onclick={closeManualEntry}
				>
					Cancel
				</button>
				<button
					type="button"
					class="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-4 py-2 font-semibold text-white shadow-lg transition-all hover:scale-105"
				>
					Save Entry
				</button>
			</div>
		</div>
	</div>
{/if}
