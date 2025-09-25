<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiService } from '$lib/services/api';
	import { currentUser } from '$lib/stores/auth';
	import { isAuthenticated } from '$lib/stores/auth';
	import { onMount } from 'svelte';

	onMount(() => {
		if (!$isAuthenticated) {
			goto('/login');
		}
	});
	async function handleLogout() {
		try {
			await apiService.logout();
		} catch (err) {
			console.error('Logout error:', err);
		} finally {
			goto('/');
		}
	}
</script>

{#if $isAuthenticated && $currentUser}
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-4xl px-4 py-10">
			<!-- Dashboard Header -->
			<div class="mb-10 flex flex-col items-center">
				<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">Willkommen!</h1>
				<p class="text-center text-gray-600 dark:text-gray-300">
					Hier können die Prioritäten für die nächsten Wochen eingegeben werden.
				</p>

				<div class="mt-4 flex gap-4">
					<button
						class="rounded-lg bg-purple-600 px-4 py-2 font-semibold text-white hover:bg-purple-700"
						on:click={handleLogout}>Logout</button
					>
				</div>
			</div>

			<!-- Dashboard Cards Overview -->
			<div class="mb-10 grid grid-cols-1 gap-6 md:grid-cols-2">
				<!-- Week Progress -->
				<div class="flex flex-col items-center rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
					<div class="mb-2 text-lg font-semibold text-purple-600 dark:text-purple-300">
						Wochenfortschritt
					</div>
					<div class="mb-2 h-4 w-full rounded-full bg-gray-200 dark:bg-gray-700">
						<!-- Replace 60 with a reactive percentage value -->
						<div
							class="h-full rounded-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-500"
							style="width:60%"
						></div>
					</div>
					<div class="text-sm text-gray-600 dark:text-gray-400">3 von 5 Wochen abgeschlossen</div>
					<a
						href="/priorities"
						class="mt-3 rounded bg-purple-100 px-3 py-1 font-medium text-purple-700 transition hover:bg-purple-200 dark:bg-purple-900 dark:text-purple-300"
						>Prioritäten bearbeiten</a
					>
				</div>
				<!-- Next Steps Card -->
				<div class="flex flex-col items-center rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
					<div class="mb-2 text-lg font-semibold text-purple-600 dark:text-purple-300">
						Was können Sie hier tun?
					</div>
					<ul class="mb-4 space-y-1 text-sm text-gray-600 dark:text-gray-300">
						<li>• Wochen priorisieren</li>
						<li>• Bisherige Priorisierungen einsehen</li>
					</ul>
				</div>
			</div>

			<!-- Profile Card -->
			<div class="flex items-center gap-4 rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
				<div
					class="flex h-16 w-16 items-center justify-center rounded-full bg-purple-200 text-xl font-bold text-purple-800 dark:bg-purple-800 dark:text-purple-100"
				>
					{$currentUser?.name?.charAt(0)}
				</div>
				<div class="flex-1">
					<div class="font-semibold text-gray-800 dark:text-white">
						{$currentUser?.name || 'Account'}
					</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$currentUser?.email}</div>
				</div>
				<a
					href="/account"
					class="rounded bg-gray-100 px-3 py-2 text-sm font-medium text-purple-600 hover:bg-purple-200 dark:bg-gray-700 dark:text-purple-300"
					>Account verwalten</a
				>
			</div>
		</div>
	</div>
{:else}
	<div
		class="flex min-h-screen items-center justify-center bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div
			class="mb-10 flex flex-col items-center rounded-xl bg-white px-8 py-6 shadow-lg dark:bg-gray-800"
		>
			<div class="mb-3 flex items-center justify-center">
				<svg
					class="h-8 w-8 text-purple-500 dark:text-purple-300"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 16h-1v-4h-1m1 0h.01m-1.01-4a4 4 0 10-8 0 4 4 0 008 0zm7 8a4 4 0 10-8 0 4 4 0 008 0z"
					/>
				</svg>
			</div>
			<div class="mb-2 text-lg font-semibold text-gray-800 dark:text-white">Nicht angemeldet</div>
			<div class="mb-4 text-center text-sm text-gray-600 dark:text-gray-300">
				Sie sind nicht eingeloggt.<br />
				Bitte melden Sie sich an, um fortzufahren.
			</div>
			<button
				class="mt-2 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-3 font-semibold text-white shadow transition hover:scale-105"
				on:click={() => goto('/login')}
			>
				Zur Anmeldung
			</button>
		</div>
	</div>
{/if}
