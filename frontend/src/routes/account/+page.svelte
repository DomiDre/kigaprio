<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated, authStore } from '$lib/auth.store';
	import { apiService } from '$lib/api.service';
	import Loading from '$lib/components/Loading.svelte';

	// Component state
	let isLoading = $state(true);
	let dekMissing = $state(false);

	// User info
	let username = $state('');
	let accountCreated = $state('');
	let lastLogin = $state('');

	// Password change
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let passwordError = $state('');
	let passwordSuccess = $state('');
	let changingPassword = $state(false);
	let showPasswords = $state(false);

	// Data management
	let showDataModal = $state(false);
	let userData = $state<any>(null);
	let loadingUserData = $state(false);

	// Account deletion
	let showDeleteModal = $state(false);
	let deleteConfirmation = $state('');
	let deletionInProgress = $state(false);

	// General messages
	let error = $state('');
	let success = $state('');

	// Password validation
	function validatePassword(password: string): string | null {
		if (password.length < 8) {
			return 'Das Passwort muss mindestens 8 Zeichen lang sein';
		}
		if (!/[A-Z]/.test(password)) {
			return 'Das Passwort muss mindestens einen Großbuchstaben enthalten';
		}
		if (!/[a-z]/.test(password)) {
			return 'Das Passwort muss mindestens einen Kleinbuchstaben enthalten';
		}
		if (!/[0-9]/.test(password)) {
			return 'Das Passwort muss mindestens eine Zahl enthalten';
		}
		if (!/[^A-Za-z0-9]/.test(password)) {
			return 'Das Passwort muss mindestens ein Sonderzeichen enthalten';
		}
		return null;
	}

	// Load user account info
	async function loadAccountInfo() {
		if (!$isAuthenticated) {
			dekMissing = true;
			error = 'Sitzung abgelaufen. Bitte melden Sie sich erneut an.';
			setTimeout(() => {
				authStore.clearAuth();
				goto('/login');
			}, 2000);
			return;
		}

		try {
			const accountInfo = await apiService.getAccountInfo();
			username = accountInfo.username || '';
			accountCreated = accountInfo.createdAt
				? new Date(accountInfo.createdAt).toLocaleDateString('de-DE')
				: '';
			lastLogin = accountInfo.lastLogin
				? new Date(accountInfo.lastLogin).toLocaleDateString('de-DE')
				: '';
		} catch (err: any) {
			console.error('Error loading account info:', err);
			error = 'Fehler beim Laden der Kontoinformationen';
		}
	}

	// Change password
	async function changePassword() {
		// Reset messages
		passwordError = '';
		passwordSuccess = '';

		// Validate inputs
		if (!currentPassword || !newPassword || !confirmPassword) {
			passwordError = 'Bitte füllen Sie alle Felder aus';
			return;
		}

		if (newPassword !== confirmPassword) {
			passwordError = 'Die neuen Passwörter stimmen nicht überein';
			return;
		}

		if (currentPassword === newPassword) {
			passwordError = 'Das neue Passwort muss sich vom aktuellen unterscheiden';
			return;
		}

		// Validate password strength
		const validationError = validatePassword(newPassword);
		if (validationError) {
			passwordError = validationError;
			return;
		}

		try {
			changingPassword = true;
			await apiService.changePassword(currentPassword, newPassword);

			passwordSuccess = 'Passwort erfolgreich geändert';
			// Clear form
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';

			// Auto-clear success message
			setTimeout(() => {
				passwordSuccess = '';
			}, 5000);
		} catch (err: any) {
			passwordError = err.message || 'Fehler beim Ändern des Passworts';
		} finally {
			changingPassword = false;
		}
	}

	// Request user data
	async function requestUserData() {
		try {
			loadingUserData = true;
			error = '';

			userData = await apiService.getUserData();
			showDataModal = true;
		} catch (err: any) {
			error = 'Fehler beim Abrufen der Daten: ' + err.message;
		} finally {
			loadingUserData = false;
		}
	}

	// Export user data
	async function exportUserData() {
		try {
			error = '';

			if (!userData) {
				userData = await apiService.getUserData();
			}

			// Create JSON blob and download
			const dataStr = JSON.stringify(userData, null, 2);
			const blob = new Blob([dataStr], { type: 'application/json' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `meine-daten-${new Date().toISOString().split('T')[0]}.json`;
			a.click();
			URL.revokeObjectURL(url);

			success = 'Daten erfolgreich exportiert';
			setTimeout(() => (success = ''), 3000);
		} catch (err: any) {
			error = 'Fehler beim Exportieren: ' + err.message;
		}
	}

	// Delete account
	async function deleteAccount() {
		if (deleteConfirmation !== 'LÖSCHEN') {
			error = 'Bitte geben Sie "LÖSCHEN" zur Bestätigung ein';
			setTimeout(() => (error = ''), 3000);
			return;
		}

		try {
			deletionInProgress = true;
			error = '';

			const result = await apiService.deleteAllUserData();

			// Generate deletion report
			const report = {
				deletionDate: new Date().toISOString(),
				username: username,
				deletedItems: result.deletedItems,
				status: 'completed',
				message: 'Ihr Account wurde vollständig gelöscht gemäß DSGVO Art. 17'
			};

			// Download deletion report
			const reportStr = JSON.stringify(report, null, 2);
			const blob = new Blob([reportStr], { type: 'application/json' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `löschbericht-${new Date().toISOString().split('T')[0]}.json`;
			a.click();
			URL.revokeObjectURL(url);

			success = 'Account wurde gelöscht. Löschbericht wurde heruntergeladen.';

			// Logout and redirect after deletion
			setTimeout(() => {
				authStore.clearAuth();
				goto('/');
			}, 3000);
		} catch (err: any) {
			error = 'Fehler beim Löschen: ' + err.message;
		} finally {
			deletionInProgress = false;
			showDeleteModal = false;
		}
	}

	// Password strength indicator
	function getPasswordStrength(password: string): { score: number; text: string; color: string } {
		let score = 0;

		if (password.length >= 8) score++;
		if (password.length >= 12) score++;
		if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
		if (/[0-9]/.test(password)) score++;
		if (/[^A-Za-z0-9]/.test(password)) score++;

		if (score <= 2) return { score, text: 'Schwach', color: 'bg-red-500' };
		if (score <= 3) return { score, text: 'Mittel', color: 'bg-orange-500' };
		if (score <= 4) return { score, text: 'Gut', color: 'bg-yellow-500' };
		return { score: 5, text: 'Stark', color: 'bg-green-500' };
	}

	let passwordStrength = $derived(getPasswordStrength(newPassword));

	onMount(() => {
		if (!$isAuthenticated) {
			goto('/login');
			return;
		}

		loadAccountInfo();
		isLoading = false;
	});
</script>

{#if isLoading}
	<Loading message="Lade Account..." />
{:else if dekMissing}
	<div
		class="flex min-h-screen items-center justify-center bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="max-w-md rounded-2xl bg-white p-8 text-center shadow-xl dark:bg-gray-800">
			<div class="mb-4 text-6xl">⚠️</div>
			<h2 class="mb-4 text-2xl font-bold text-gray-800 dark:text-white">Sitzung abgelaufen</h2>
			<p class="mb-4 text-gray-600 dark:text-gray-300">
				Ihre Sitzung ist abgelaufen. Sie werden zur Anmeldung weitergeleitet...
			</p>
			<div class="animate-spin text-4xl">⟳</div>
		</div>
	</div>
{:else if $isAuthenticated}
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-4xl px-4 py-10">
			<!-- Navigation Bar -->
			<div class="mb-8 flex items-center justify-between">
				<h1 class="text-3xl font-bold text-gray-800 dark:text-white">Account-Verwaltung</h1>
				<div class="flex gap-3">
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
				</div>
			</div>

			{#if error}
				<div class="mb-6 rounded-lg bg-red-100 p-4 text-red-700 dark:bg-red-900 dark:text-red-300">
					{error}
				</div>
			{/if}

			{#if success}
				<div
					class="mb-6 rounded-lg bg-green-100 p-4 text-green-700 dark:bg-green-900 dark:text-green-300"
				>
					{success}
				</div>
			{/if}

			<!-- Account Information -->
			<div class="mb-6 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
				<h2 class="mb-4 text-xl font-semibold text-purple-600 dark:text-purple-300">
					👤 Account-Informationen
				</h2>
				<div class="grid gap-4 md:grid-cols-2">
					<div>
						<div class="text-sm font-medium text-gray-600 dark:text-gray-400">Username</div>
						<p class="mt-1 text-gray-800 dark:text-gray-200">{username || 'Nicht verfügbar'}</p>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-600 dark:text-gray-400">Account erstellt</div>
						<p class="mt-1 text-gray-800 dark:text-gray-200">
							{accountCreated || 'Nicht verfügbar'}
						</p>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-600 dark:text-gray-400">Letzte Anmeldung</div>
						<p class="mt-1 text-gray-800 dark:text-gray-200">{lastLogin || 'Nicht verfügbar'}</p>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-600 dark:text-gray-400">Account-Status</div>
						<p class="mt-1">
							<span
								class="inline-flex items-center rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200"
							>
								✓ Aktiv
							</span>
						</p>
					</div>
				</div>
			</div>

			<!-- Password Change -->
			<div class="mb-6 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
				<h2 class="mb-4 text-xl font-semibold text-purple-600 dark:text-purple-300">
					🔐 Passwort ändern
				</h2>

				{#if passwordError}
					<div
						class="mb-4 rounded-lg bg-red-100 p-3 text-sm text-red-700 dark:bg-red-900 dark:text-red-300"
					>
						{passwordError}
					</div>
				{/if}

				{#if passwordSuccess}
					<div
						class="mb-4 rounded-lg bg-green-100 p-3 text-sm text-green-700 dark:bg-green-900 dark:text-green-300"
					>
						{passwordSuccess}
					</div>
				{/if}

				<div class="space-y-4">
					<div>
						<label
							for="current-password"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							Aktuelles Passwort
						</label>
						<div class="relative mt-1">
							<input
								id="current-password"
								type={showPasswords ? 'text' : 'password'}
								bind:value={currentPassword}
								class="w-full rounded-lg border border-gray-300 px-4 py-2 pr-10 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
								placeholder="Aktuelles Passwort eingeben"
							/>
						</div>
					</div>

					<div>
						<label
							for="new-password"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							Neues Passwort
						</label>
						<div class="relative mt-1">
							<input
								id="new-password"
								type={showPasswords ? 'text' : 'password'}
								bind:value={newPassword}
								class="w-full rounded-lg border border-gray-300 px-4 py-2 pr-10 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
								placeholder="Neues Passwort eingeben"
							/>
						</div>
						{#if newPassword}
							<div class="mt-2">
								<div class="flex items-center gap-2">
									<div class="h-2 flex-1 rounded-full bg-gray-200 dark:bg-gray-700">
										<div
											class="h-full rounded-full transition-all {passwordStrength.color}"
											style="width: {passwordStrength.score * 20}%"
										></div>
									</div>
									<span class="text-xs font-medium text-gray-600 dark:text-gray-400">
										{passwordStrength.text}
									</span>
								</div>
							</div>
						{/if}
					</div>

					<div>
						<label
							for="confirm-password"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							Neues Passwort bestätigen
						</label>
						<div class="relative mt-1">
							<input
								id="confirm-password"
								type={showPasswords ? 'text' : 'password'}
								bind:value={confirmPassword}
								class="w-full rounded-lg border border-gray-300 px-4 py-2 pr-10 focus:border-purple-500 focus:ring-2 focus:ring-purple-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
								placeholder="Neues Passwort wiederholen"
							/>
						</div>
					</div>

					<div class="flex items-center">
						<input
							id="show-passwords"
							type="checkbox"
							bind:checked={showPasswords}
							class="h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-2 focus:ring-purple-500"
						/>
						<label for="show-passwords" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
							Passwörter anzeigen
						</label>
					</div>

					<button
						onclick={changePassword}
						disabled={changingPassword}
						class="w-full rounded-lg bg-purple-600 px-4 py-2 font-medium text-white transition-colors hover:bg-purple-700 disabled:opacity-50 md:w-auto"
					>
						{changingPassword ? 'Wird geändert...' : 'Passwort ändern'}
					</button>
				</div>
			</div>

			<!-- Data Management -->
			<div class="mb-6 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
				<h2 class="mb-4 text-xl font-semibold text-purple-600 dark:text-purple-300">
					📊 Datenverwaltung (DSGVO)
				</h2>
				<p class="mb-6 text-sm text-gray-600 dark:text-gray-400">
					Gemäß der Datenschutz-Grundverordnung haben Sie das Recht auf Auskunft, Berichtigung und
					Löschung Ihrer personenbezogenen Daten.
				</p>

				<div class="flex flex-wrap gap-3">
					<button
						onclick={requestUserData}
						disabled={loadingUserData}
						class="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
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
								d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
							/>
						</svg>
						Gespeicherte Daten einsehen
					</button>

					<button
						onclick={exportUserData}
						class="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700"
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
								d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
							/>
						</svg>
						Daten exportieren
					</button>
				</div>
			</div>

			<!-- Danger Zone -->
			<div
				class="rounded-xl border-2 border-red-200 bg-red-50 p-6 dark:border-red-800 dark:bg-red-900/20"
			>
				<h2 class="mb-4 text-xl font-semibold text-red-600 dark:text-red-400">⚠️ Gefahrenzone</h2>
				<p class="mb-4 text-sm text-gray-700 dark:text-gray-300">
					Das Löschen Ihres Accounts ist unwiderruflich. Alle Ihre Daten werden permanent gelöscht.
				</p>
				<button
					onclick={() => (showDeleteModal = true)}
					class="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
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
							d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
						/>
					</svg>
					Account löschen
				</button>
			</div>
		</div>

		<!-- Data View Modal -->
		{#if showDataModal && userData}
			<div class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4">
				<div
					class="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800"
				>
					<div class="mb-4 flex items-center justify-between">
						<h3 class="text-xl font-semibold text-gray-800 dark:text-white">
							Ihre gespeicherten Daten
						</h3>
						<button
							onclick={() => (showDataModal = false)}
							aria-label="Schließen"
							class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="h-6 w-6"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M6 18L18 6M6 6l12 12"
								/>
							</svg>
						</button>
					</div>

					<div
						class="mb-4 rounded-lg bg-blue-50 p-3 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
					>
						ℹ️ Dies ist eine vollständige Kopie aller Daten, die wir über Sie speichern (DSGVO Art.
						15)
					</div>

					<div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-900">
						<pre
							class="text-sm whitespace-pre-wrap text-gray-700 dark:text-gray-300">{JSON.stringify(
								userData,
								null,
								2
							)}</pre>
					</div>

					<div class="mt-4 flex justify-end gap-3">
						<button
							onclick={exportUserData}
							class="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
						>
							Als JSON exportieren
						</button>
						<button
							onclick={() => (showDataModal = false)}
							class="rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200"
						>
							Schließen
						</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- Delete Confirmation Modal -->
		{#if showDeleteModal}
			<div class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4">
				<div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
					<div class="mb-4">
						<h3 class="text-xl font-semibold text-red-600 dark:text-red-400">
							⚠️ Account dauerhaft löschen
						</h3>
					</div>

					<div class="mb-6 space-y-4">
						<p class="text-gray-700 dark:text-gray-300">
							<strong>Diese Aktion ist unwiderruflich!</strong> Folgende Daten werden gelöscht:
						</p>

						<ul class="list-disc pl-5 text-sm text-gray-600 dark:text-gray-400">
							<li>Ihr Benutzerkonto und alle Anmeldedaten</li>
							<li>Alle gespeicherten Prioritäten</li>
							<li>Alle persönlichen Einstellungen</li>
							<li>Sämtliche Aktivitätsprotokolle</li>
						</ul>

						<p class="text-sm text-gray-600 dark:text-gray-400">
							Nach der Löschung erhalten Sie einen Löschbericht als Nachweis gemäß DSGVO Art. 17.
						</p>

						<div>
							<label
								for="delete-confirm"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300"
							>
								Geben Sie <strong>LÖSCHEN</strong> zur Bestätigung ein:
							</label>
							<input
								id="delete-confirm"
								type="text"
								bind:value={deleteConfirmation}
								class="mt-1 w-full rounded-lg border border-red-300 px-4 py-2 focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none dark:border-red-600 dark:bg-gray-700 dark:text-gray-200"
								placeholder="LÖSCHEN"
							/>
						</div>
					</div>

					<div class="flex gap-3">
						<button
							onclick={deleteAccount}
							disabled={deletionInProgress || deleteConfirmation !== 'LÖSCHEN'}
							class="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
						>
							{#if deletionInProgress}
								Lösche Account...
							{:else}
								Account endgültig löschen
							{/if}
						</button>
						<button
							onclick={() => {
								showDeleteModal = false;
								deleteConfirmation = '';
							}}
							disabled={deletionInProgress}
							class="flex-1 rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200"
						>
							Abbrechen
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
{:else}
	<Loading message="Lade..." />
{/if}
