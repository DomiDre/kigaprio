<!-- src/routes/register/+page.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { pb } from '$lib/services/pocketbase';
	import { currentUser } from '$lib/stores/auth';
	import { registerUser } from '$lib/services/auth';

	let email = $state('');
	let password = $state('');
	let passwordConfirm = $state('');
	let fullName = $state('');
	let error = $state('');
	let loading = $state(false);

	$effect(() => {
		if ($currentUser) {
			goto('/');
		}
	});

	async function handleRegister(event: Event) {
		event.preventDefault();

		error = '';
		loading = true;

		// Basic validation
		if (password !== passwordConfirm) {
			error = 'Passwords do not match';
			loading = false;
			return;
		}

		if (password.length < 8) {
			error = 'Password must be at least 8 characters long';
			loading = false;
			return;
		}

		try {
			await registerUser(email, password, fullName);
			// Auto-login after registration
			await pb.collection('users').authWithPassword(email, password);
			goto('/');
		} catch (err) {
			error = (err as Error).message;
		} finally {
			loading = false;
		}
	}

	function goToLogin() {
		goto('/login');
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-4xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8 text-center">
			<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">Anmelden</h1>
			<p class="text-gray-600 dark:text-gray-300">Account zur Eingabe der Prioliste erstellen</p>
		</div>
		<!-- Main Card -->
		<div class="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			<form class="space-y-6" onsubmit={handleRegister}>
				<div>
					<label for="fullName" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Name
					</label>
					<input
						id="fullName"
						type="text"
						bind:value={fullName}
						placeholder="Namen des Kindes eingeben"
						class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
                               focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none dark:bg-gray-700 dark:text-white"
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
                               focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none dark:bg-gray-700 dark:text-white"
					/>
				</div>

				<div>
					<label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Passwort
					</label>
					<input
						id="password"
						type="password"
						bind:value={password}
						required
						placeholder="Passwort eingeben (min. 8 Zeichen)"
						class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
                               focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none dark:bg-gray-700 dark:text-white"
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
                               focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none dark:bg-gray-700 dark:text-white"
					/>
				</div>

				{#if error}
					<div
						class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
					>
						<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
					</div>
				{/if}

				<button
					type="submit"
					disabled={loading}
					class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4
                           font-semibold text-white shadow-lg transition hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50"
				>
					{#if loading}
						<span class="mr-2 animate-spin">⟳</span>
					{/if}
					{loading ? 'Erstelle Account...' : 'Account erstellen'}
				</button>

				<p class="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
					Haben Sie bereits einen Account?
					<button
						type="button"
						onclick={goToLogin}
						class="ml-1 font-semibold text-blue-600 underline hover:text-blue-500"
					>
						Hier klicken zum einloggen.
					</button>
				</p>
			</form>
		</div>
	</div>
</div>
