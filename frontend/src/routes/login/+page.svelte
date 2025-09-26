<script lang="ts">
	import { goto } from '$app/navigation';
	import { currentUser, isAuthenticated } from '$lib/stores/auth';
	import { apiService } from '$lib/services/api';
	import { onMount } from 'svelte';

	let email = '';
	let password = '';
	let error = '';

	onMount(() => {
		if ($isAuthenticated) {
			goto('/');
		}
	});

	async function handleLogin() {
		error = '';
		try {
			await apiService.login(email, password);
			goto('/');
		} catch (err) {
			error = (err as Error).message;
		}
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

	function handleDashboard() {
		goto('/');
	}

	function goToRegister() {
		goto('/register');
	}
</script>

<div
	class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
>
	<div class="container mx-auto max-w-4xl px-4 py-8">
		<!-- Header -->
		<div class="mb-8 text-center">
			<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">Login Prioliste</h1>
			<p class="text-gray-600 dark:text-gray-300">Kindergarten Prioliste eingeben</p>
		</div>
		<!-- Main Card -->
		<div class="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
			{#if $currentUser}
				<div class="rounded-lg bg-gray-100 p-6 text-center shadow dark:bg-gray-700">
					<p class="mb-4 text-gray-800 dark:text-gray-100">Willkommen, {$currentUser.email}!</p>
					<button
						class="rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-3 font-semibold text-white shadow-lg transition hover:scale-105"
						on:click={handleDashboard}
					>
						Dashboard
					</button>
					<button
						class="rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-3 font-semibold text-white shadow-lg transition hover:scale-105"
						on:click={handleLogout}
					>
						Abmelden
					</button>
				</div>
			{:else}
				<form class="space-y-6" on:submit|preventDefault={handleLogin}>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						E-Mail
						<input
							type="email"
							bind:value={email}
							required
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
                                   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none dark:bg-gray-700 dark:text-white"
						/>
					</label>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Passwort
						<input
							type="password"
							bind:value={password}
							required
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
                                   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none dark:bg-gray-700 dark:text-white"
						/>
					</label>
					<button
						type="submit"
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 py-3 font-semibold
                               text-white shadow-lg transition hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50"
					>
						Anmelden
					</button>
					<button
						type="button"
						class="w-full rounded-xl bg-gray-600 py-3 font-semibold text-white shadow-lg hover:bg-gray-700"
						on:click={goToRegister}
					>
						Registrieren
					</button>
					{#if error}
						<p
							class="mt-4 rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
						>
							{error}
						</p>
					{/if}
				</form>
			{/if}
		</div>
	</div>
</div>
