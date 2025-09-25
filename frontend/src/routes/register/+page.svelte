<!-- src/routes/register/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { currentUser } from '$lib/stores/auth';
	import { apiService } from '$lib/services/api';

	let email = $state('');
	let password = $state('');
	let passwordConfirm = $state('');
	let fullName = $state('');
	let magicWord = $state('');
	let error = $state('');
	let loading = $state(false);
	let registrationToken = $state('');
	let magicWordVerified = $state(false);

	$effect(() => {
		if ($currentUser) {
			goto('/');
		}
	});

	async function handleMagicWord(event: Event) {
		event.preventDefault();
		error = '';
		loading = true;

		try {
			const response = await fetch(`${apiService.baseUrl}/verify-magic-word`, {
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
			const response = await fetch(`${apiService.baseUrl}/register`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					email,
					password,
					passwordConfirm: password,
					name: fullName,
					registration_token: registrationToken
				})
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || 'Registration failed');
			}
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
							placeholder="Zauberwort eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
									   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
									   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					{#if error}
						<div
							class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
						>
							<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
						</div>
					{/if}

					<button
						type="submit"
						disabled={loading || !magicWord}
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4
							   font-semibold text-white shadow-lg transition hover:scale-105
							   disabled:cursor-not-allowed disabled:opacity-50"
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
							placeholder="Namen des Kindes eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
									   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
									   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					<div>
						<label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							Email Adresse
						</label>
						<input
							id="email"
							type="email"
							bind:value={email}
							required
							placeholder="Email eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
									   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
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
							placeholder="Passwort eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
									   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
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
							placeholder="Nochmal Passwort eingeben"
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
									   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
									   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</div>

					{#if error}
						<div
							class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
						>
							<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
						</div>
					{/if}

					<button
						type="submit"
						disabled={loading}
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4
							   font-semibold text-white shadow-lg transition hover:scale-105
							   disabled:cursor-not-allowed disabled:opacity-50"
					>
						{#if loading}
							<span class="mr-2 animate-spin">⟳</span>
						{/if}
						{loading ? 'Erstelle Account...' : 'Account erstellen'}
					</button>

					<button
						type="button"
						onclick={resetToMagicWord}
						class="w-full text-center text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
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
	</div>
</div>
