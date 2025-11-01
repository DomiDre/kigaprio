<script lang="ts">
	import { onMount } from 'svelte';
	import Refresh from 'virtual:icons/mdi/refresh';
	import { apiService } from '$lib/services/api';
	import { cryptoService } from '$lib/services/crypto';
	import { webAuthnCryptoService } from '$lib/services/webauthn-crypto';
	import DecryptedDataModal from '$lib/components/DecryptedDataModal.svelte';
	import StatsCards from '$lib/components/StatsCards.svelte';
	import AuthenticationPanel from '$lib/components/AuthenticationPanel.svelte';
	import PrioritiesOverview from '$lib/components/PrioritiesOverview.svelte';
	import UserSubmissionsTable from '$lib/components/UserSubmissionsTable.svelte';
	import SidebarActions from '$lib/components/SidebarActions.svelte';
	import ManualEntryModal from '$lib/components/ManualEntryModal.svelte';
	import ErrorDisplay from '$lib/components/ErrorDisplay.svelte';
	import LoadingIndicator from '$lib/components/LoadingIndicator.svelte';
	import type { DecryptedData, UserDisplay, UserPriorityRecord } from '$lib/types/dashboard';
	import { dayKeys } from '$lib/config/priorities';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';

	// State
	let selectedMonth = $state('2025-10');
	let keyUploaded = $state(false);
	let showManualEntry = $state(false);
	let searchQuery = $state('');
	let keyFile = $state<File | null>(null);
	let isLoading = $state(true);
	let isRefreshing = $state(false);
	let error = $state('');
	let decryptionError = $state('');
	let showOverview = $state(false);
	let authMode: 'file' | 'webauthn' | null = $state(null);

	// Decryption state
	let isDecrypting = $state(false);
	let isDecryptingAll = $state(false);
	let showDecryptedModal = $state(false);
	let decryptedData = $state<DecryptedData | null>(null);
	let decryptedUsers = $state(
		new SvelteMap<string, { name: string; userData: any; priorities: any }>()
	);

	// Data
	let userSubmissions = $state<UserPriorityRecord[]>([]);
	let users = $state<UserDisplay[]>([]);

	// Passphrase state
	let passphraseInput = $state('');
	let showPassphrasePrompt = $state(false);
	let pendingKeyFile = $state<File | null>(null);

	// Track if initial fetch is done
	let initialFetchDone = $state(false);

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

	// Build overview data structure using $derived
	let overviewData = $derived.by(() => {
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

		return data.sort((a, b) => a.userName.localeCompare(b.userName));
	});

	// Get all unique weeks across all users
	let allWeeks = $derived.by(() => {
		const weekSet = new SvelteSet<number>();
		decryptedUsers.forEach((userData) => {
			const weeks = userData.priorities?.weeks || [];
			weeks.forEach((week: any) => {
				weekSet.add(week.weekNumber);
			});
		});
		return Array.from(weekSet).sort((a, b) => a - b);
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

		return stats;
	});

	// Filter users based on search query using $derived
	let filteredUsers = $derived.by(() => {
		return users.filter((user) => {
			const displayName = getDisplayName(user.name);
			return displayName.toLowerCase().includes(searchQuery.toLowerCase());
		});
	});

	// Fetch user submissions from API
	async function fetchUserSubmissions() {
		isLoading = true;
		error = '';

		try {
			const data = await apiService.getUserSubmissions(selectedMonth);
			userSubmissions = data;

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

		isDecryptingAll = true;
		decryptionError = '';

		const newDecryptedUsers = new SvelteMap<
			string,
			{ name: string; userData: any; priorities: any }
		>();

		try {
			for (const user of users) {
				if (user.adminWrappedDek && user.userEncryptedFields && user.prioritiesEncryptedFields) {
					try {
						// Use the appropriate service based on auth mode
						const service = authMode === 'webauthn' ? webAuthnCryptoService : cryptoService;

						const result = await service.decryptUserData(
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

			decryptedUsers = newDecryptedUsers;
			showOverview = true;
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

	function isDecrypted(userName: string): boolean {
		return decryptedUsers.has(userName);
	}

	// Fetch data on mount
	onMount(() => {
		fetchUserSubmissions();
		initialFetchDone = true;
	});

	// Watch for month changes using $effect
	$effect(() => {
		if (initialFetchDone && selectedMonth) {
			decryptedUsers = new SvelteMap();
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
		} catch {
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
	function removeKey() {
		keyUploaded = false;
		keyFile = null;
		authMode = null;
		cryptoService.clearKey();
		webAuthnCryptoService.clearKey();
		decryptionError = '';
		decryptedUsers = new SvelteMap();
		showOverview = false;
	}

	async function handleYubiKeyAuth() {
		isDecrypting = true;
		decryptionError = '';

		try {
			await webAuthnCryptoService.authenticateWithYubiKey();
			keyUploaded = true;
			authMode = 'webauthn';
			await decryptAllUsers();
		} catch (err) {
			const errorMsg = (err as Error).message;
			if (errorMsg.includes('NotAllowedError')) {
				decryptionError =
					'YubiKey authentication cancelled. Please touch your YubiKey when prompted.';
			} else {
				decryptionError = errorMsg;
			}
			throw err;
		} finally {
			isDecrypting = false;
		}
	}

	async function viewUserData(user: UserDisplay) {
		if (!keyUploaded) {
			decryptionError = 'Bitte authentifizieren Sie sich zuerst';
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
			// Use the appropriate service based on auth mode
			const service = authMode === 'webauthn' ? webAuthnCryptoService : cryptoService;

			const result = await service.decryptUserData(
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
		alert('Excel-Export wird noch implementiert');
	}

	function openManualEntry() {
		showManualEntry = true;
	}

	function closeManualEntry() {
		showManualEntry = false;
	}

	async function handleRefresh() {
		if (isRefreshing || isLoading) return;

		isRefreshing = true;
		error = '';
		decryptionError = '';

		try {
			await fetchUserSubmissions();
		} catch (err) {
			error = 'Fehler beim Aktualisieren der Daten';
			console.error('Refresh error:', err);
		} finally {
			isRefreshing = false;
		}
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

					<button
						type="button"
						onclick={handleRefresh}
						disabled={isRefreshing || isLoading}
						class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-all hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
						title="Refresh data"
					>
						<Refresh class="h-4 w-4 {isRefreshing ? 'animate-spin' : ''}" />
						<span class="hidden sm:inline">
							{isRefreshing ? 'Refreshing...' : 'Refresh'}
						</span>
					</button>
				</div>
			</div>
		</div>
	</div>

	<div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
		<!-- Error Messages -->
		{#if error}
			<ErrorDisplay message={error} onClose={() => (error = '')} />
		{/if}

		{#if decryptionError}
			<ErrorDisplay
				message={decryptionError}
				title="Entschlüsselungsfehler"
				onClose={() => (decryptionError = '')}
			/>
		{/if}

		<!-- Progress Indicators -->
		{#if isDecryptingAll}
			<LoadingIndicator
				message="Entschlüssele Benutzerdaten... ({decryptedUsers.size}/{users.length})"
			/>
		{/if}

		{#if isRefreshing}
			<LoadingIndicator
				message="Aktualisiere Daten{keyUploaded ? ' und entschlüssele...' : '...'}"
				color="blue"
			/>
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
			<StatsCards {stats} />

			<!-- Priorities Overview Table -->
			{#if keyUploaded && decryptedUsers.size > 0}
				<PrioritiesOverview
					{showOverview}
					decryptedUsersCount={decryptedUsers.size}
					{overviewData}
					{allWeeks}
					{demandStats}
					onToggle={() => (showOverview = !showOverview)}
				/>
			{/if}

			<div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
				<!-- Main Content Area -->
				<div class="space-y-6 lg:col-span-2">
					<!-- Private Key Upload -->
					<AuthenticationPanel
						{keyUploaded}
						{keyFile}
						{showPassphrasePrompt}
						{passphraseInput}
						decryptedUsersCount={decryptedUsers.size}
						onKeyUpload={handleKeyUpload}
						onKeyDrop={handleKeyDrop}
						onPassphraseChange={(value) => (passphraseInput = value)}
						onSubmitPassphrase={submitPassphrase}
						onCancelPassphrase={cancelPassphrase}
						onRemoveKey={removeKey}
						onYubiKeyAuth={handleYubiKeyAuth}
					/>

					<!-- User Submissions Table -->
					<UserSubmissionsTable
						{filteredUsers}
						{searchQuery}
						{keyUploaded}
						{isDecrypting}
						totalUsers={users.length}
						{isDecrypted}
						{getDisplayName}
						onSearchChange={(value) => (searchQuery = value)}
						onViewUser={viewUserData}
						onManualEntry={openManualEntry}
					/>
				</div>

				<!-- Sidebar Actions -->
				<SidebarActions
					{keyUploaded}
					{stats}
					decryptedUsersCount={decryptedUsers.size}
					onManualEntry={openManualEntry}
					onExportExcel={exportToExcel}
				/>
			</div>
		{/if}
	</div>
</div>

<!-- Modals -->
{#if showDecryptedModal && decryptedData}
	<DecryptedDataModal
		userName={decryptedData.userName}
		userData={decryptedData.userData}
		priorities={decryptedData.priorities}
		onClose={closeDecryptedModal}
	/>
{/if}

{#if showManualEntry}
	<ManualEntryModal onClose={closeManualEntry} />
{/if}

