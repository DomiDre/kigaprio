<!-- src/routes/register/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { apiService } from '$lib/services/api';

	let username = $state('');
	let password = $state('');
	let passwordConfirm = $state('');
	let fullName = $state('');
	let magicWord = $state('');
	let keepLoggedIn = $state(false);
	let error = $state('');
	let loading = $state(false);
	let registrationToken = $state('');
	let magicWordVerified = $state(false);

	$effect(() => {
		if ($isAuthenticated) {
			goto('/');
		}
	});

	async function handleMagicWord(event: Event) {
		event.preventDefault();
		error = '';
		loading = true;

		try {
			const response = await fetch(`${apiService.baseUrl}/auth/verify-magic-word`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ magic_word: magicWord })
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.detail || 'Ungültiges Zauberwort');
			}

			const data = await response.json();
			registrationToken = data.token;
			magicWordVerified = true;
			error = '';
		} catch (err) {
			error = (err as Error).message;
		} finally {
			loading = false;
		}
	}

	async function handleRegister(event: Event) {
		event.preventDefault();

		error = '';
		loading = true;

		// Basic validation
		if (password !== passwordConfirm) {
			error = 'Passwörter stimmen nicht überein';
			loading = false;
			return;
		}
		if (password.length < 1) {
			error = 'Password must be at least 1 character long';
			loading = false;
			return;
		}

		try {
			await apiService.register({
				identity: username,
				password,
				passwordConfirm: password,
				name: fullName,
				registration_token: registrationToken,
				keep_logged_in: keepLoggedIn
			});
			goto('/');
		} catch (err) {
			error = (err as Error).message;
			// If token expired, reset to magic word step
			if (error.includes('token')) {
				magicWordVerified = false;
				registrationToken = '';
				magicWord = '';
			}
		} finally {
			loading = false;
		}
	}

	function goToLogin() {
		goto('/login');
	}

	function resetToMagicWord() {
		magicWordVerified = false;
		registrationToken = '';
		magicWord = '';
		error = '';
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-4xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8 text-center">
			<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">Anmelden</h1>
			<p class="text-gray-600 dark:text-gray-300">
				{magicWordVerified
					? 'Account zur Eingabe der Prioliste erstellen'
					: 'Bitte geben Sie das Zauberwort ein, das im Gebäude hinterlegt ist'}
			</p>
		</div>

		<!-- Main Card -->
		<div class="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			{#if !magicWordVerified}
				<!-- Magic Word Form -->
				<form class="space-y-6" onsubmit={handleMagicWord}>
					<div class="mb-4 text-center">
						<div
							class="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-500"
						>
							<span class="text-3xl">🔐</span>
						</div>
						<h2 class="text-xl font-semibold text-gray-800 dark:text-white">
							Zugangsverifizierung
						</h2>
						<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
							Das Zauberwort finden Sie im Eingangsbereich des Gebäudes
						</p>
					</div>

					<div>
						<label
							for="magicWord"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							Zauberwort
						</label>
						<input
							id="magicWord"
							type="text"
							bind:value={magicWord}
							required
							disabled={loading}
							placeholder="Zauberwort eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					{#if error}
						<div
							class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
						>
							<div class="flex items-start">
								<svg
									class="mr-2 h-5 w-5 flex-shrink-0 text-red-600"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path
										fill-rule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
										clip-rule="evenodd"
									/>
								</svg>
								<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
							</div>
						</div>
					{/if}

					<button
						type="submit"
						disabled={loading || !magicWord}
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4
							   font-semibold text-white shadow-lg transition hover:scale-105
							   disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
					>
						{#if loading}
							<span class="mr-2 animate-spin">⟳</span>
						{/if}
						{loading ? 'Überprüfe...' : 'Zauberwort überprüfen'}
					</button>
				</form>
			{:else}
				<!-- Registration Form -->
				<form class="space-y-6" onsubmit={handleRegister}>
					<div
						class="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-900/20"
					>
						<p class="flex items-center text-sm text-green-700 dark:text-green-400">
							<span class="mr-2">✓</span> Zauberwort verifiziert! Sie können sich jetzt registrieren.
						</p>
					</div>

					<div>
						<label
							for="fullName"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							Name
						</label>
						<input
							id="fullName"
							type="text"
							bind:value={fullName}
							disabled={loading}
							placeholder="Namen des Kindes eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					<div>
						<label
							for="username"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							Loginname
						</label>
						<input
							id="username"
							type="text"
							bind:value={username}
							required
							disabled={loading}
							placeholder="Username eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					<div>
						<label
							for="password"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							Passwort
						</label>
						<input
							id="password"
							type="password"
							bind:value={password}
							required
							disabled={loading}
							placeholder="Passwort eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					<div>
						<label
							for="passwordConfirm"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							Passwort bestätigen
						</label>
						<input
							id="passwordConfirm"
							type="password"
							bind:value={passwordConfirm}
							required
							disabled={loading}
							placeholder="Nochmal Passwort eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					<!-- SIMPLIFIED: Keep Me Logged In Checkbox (same as login) -->
					<div
						class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900"
					>
						<label class="flex cursor-pointer items-start">
							<input
								type="checkbox"
								bind:checked={keepLoggedIn}
								disabled={loading}
								class="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600
								       focus:ring-2 focus:ring-blue-500 focus:ring-offset-0
								       disabled:cursor-not-allowed disabled:opacity-50
								       dark:border-gray-600 dark:bg-gray-700"
							/>
							<div class="ml-3 flex-1">
								<span class="block font-medium text-gray-900 dark:text-white">
									Angemeldet bleiben
								</span>
								<span class="mt-1 block text-sm text-gray-600 dark:text-gray-400">
									{#if keepLoggedIn}
										Sie bleiben 30 Tage angemeldet. Empfohlen für persönliche Geräte.
									{:else}
										Sie werden nach 8 Stunden oder beim Schließen des Browsers abgemeldet. Empfohlen
										für gemeinsam genutzte Computer.
									{/if}
								</span>
							</div>
						</label>
					</div>

					{#if error}
						<div
							class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
						>
							<div class="flex items-start">
								<svg
									class="mr-2 h-5 w-5 flex-shrink-0 text-red-600"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path
										fill-rule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
										clip-rule="evenodd"
									/>
								</svg>
								<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
							</div>
						</div>
					{/if}

					<button
						type="submit"
						disabled={loading}
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4
							   font-semibold text-white shadow-lg transition hover:scale-105
							   disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
					>
						{#if loading}
							<span class="mr-2 animate-spin">⟳</span>
						{/if}
						{loading ? 'Erstelle Account...' : 'Account erstellen'}
					</button>

					<button
						type="button"
						onclick={resetToMagicWord}
						disabled={loading}
						class="w-full text-center text-sm text-gray-600 hover:text-gray-800
						       disabled:cursor-not-allowed disabled:opacity-50
						       dark:text-gray-400 dark:hover:text-gray-200"
					>
						← Zurück zur Zauberwort-Eingabe
					</button>
				</form>
			{/if}

			<p class="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
				Haben Sie bereits einen Account?
				<button
					type="button"
					onclick={goToLogin}
					class="ml-1 font-semibold text-blue-600 underline hover:text-blue-500"
				>
					Hier klicken zum einloggen.
				</button>
			</p>
		</div>

		<!-- Security Note -->
		<div class="mx-auto mt-6 max-w-md">
			<div
				class="flex items-start rounded-lg bg-white p-4 text-xs text-gray-500 shadow dark:bg-gray-800 dark:text-gray-400"
			>
				<svg
					class="mr-2 h-4 w-4 flex-shrink-0 text-green-600"
					fill="currentColor"
					viewBox="0 0 20 20"
				>
					<path
						fill-rule="evenodd"
						d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
						clip-rule="evenodd"
					/>
				</svg>
				<p class="leading-relaxed">
					Gespeicherte Daten werden Serverseitig verschlüsselt. Wir können Ihre persönlichen
					Informationen nicht lesen.
				</p>
			</div>
		</div>
	</div>
</div>
