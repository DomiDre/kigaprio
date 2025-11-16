<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore, isAuthenticated } from '$lib/auth.stores';
	import { apiService } from '$lib/api.service';
	import { onMount } from 'svelte';
	import Loading from '$lib/components/Loading.svelte';

	let username = '';
	let password = '';
	let keepLoggedIn = false;
	let error = '';
	let isLoading = false;

	onMount(() => {
		if ($isAuthenticated) {
			goto('/dashboard');
		}
	});

	async function handleLogin() {
		error = '';
		isLoading = true;

		try {
			await apiService.login(username, password, keepLoggedIn);
			const isAdmin = await authStore.verifyAuth();
			if (isAdmin) {
				goto('/dashboard');
			} else {
				error = 'Zugriff verweigert. Nur Administratoren können sich hier anmelden.';
				await apiService.logout(); // Logout the non-admin user
			}
		} catch (err) {
			error = (err as Error).message;
		} finally {
			isLoading = false;
		}
	}
</script>

{#if $isAuthenticated}
	<Loading message="Lade..." />
{:else}
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-5xl px-4 py-8">
			<!-- Header -->
			<div class="mb-8 text-center">
				<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">Admin UI Login</h1>
			</div>

			<!-- Main Card -->
			<div class="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
				<form class="space-y-6" on:submit|preventDefault={handleLogin}>
					<!-- Username -->
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Username
						<input
							type="text"
							bind:value={username}
							required
							disabled={isLoading}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</label>

					<!-- Password -->
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Passwort
						<input
							type="password"
							bind:value={password}
							required
							disabled={isLoading}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</label>

					<!-- Login Button -->
					<button
						type="submit"
						disabled={isLoading}
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 py-3 font-semibold
							   text-white shadow-lg transition hover:scale-105
							   disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
					>
						{isLoading ? 'Wird angemeldet...' : 'Anmelden'}
					</button>

					<!-- Error Message -->
					{#if error}
						<div
							class="mt-4 rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
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
								<span>{error}</span>
							</div>
						</div>
					{/if}
				</form>
			</div>

			<!-- Footer -->
			<div class="mt-8 text-center">
				<div class="flex flex-wrap justify-center gap-4 text-sm text-gray-600 dark:text-gray-400">
					<a
						href="https://github.com/domidre/priotag"
						target="_blank"
						rel="noopener noreferrer"
						class="transition-colors hover:text-blue-600 dark:hover:text-blue-400"
					>
						GitHub
					</a>
				</div>
			</div>
		</div>
	</div>
{/if}
