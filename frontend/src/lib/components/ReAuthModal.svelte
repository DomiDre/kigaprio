<script lang="ts">
	import { apiService } from '$lib/services/api';
	import { authStore } from '$lib/stores/auth';
	import { goto } from '$app/navigation';

	export let isOpen = false;
	export let onClose: (() => void) | null = null;

	let password = '';
	let error = '';
	let isLoading = false;
	let passwordInput: HTMLInputElement;
	let modalContent: HTMLDivElement;

	// Focus the password input when modal opens
	$: if (isOpen && passwordInput) {
		setTimeout(() => passwordInput?.focus(), 0);
	}

	async function handleReAuth() {
		error = '';
		isLoading = true;

		try {
			await apiService.reAuthenticate(password);
			password = '';
			isOpen = false;
			if (onClose) onClose();
		} catch (err) {
			error = (err as Error).message;
		} finally {
			isLoading = false;
		}
	}

	function handleLogout() {
		authStore.clearAuth();
		goto('/login');
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && !isLoading) {
			handleLogout();
		}
	}

	function handleContentKeydown(e: KeyboardEvent) {
		// Stop propagation for keyboard events on the modal content
		e.stopPropagation();
	}
</script>

{#if isOpen}
	<div
		class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black backdrop-blur-sm"
		on:click={handleLogout}
		on:keydown={handleKeydown}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<div
			bind:this={modalContent}
			class="mx-4 w-full max-w-md rounded-2xl bg-white shadow-2xl dark:bg-gray-800"
			on:click|stopPropagation
			on:keydown={handleContentKeydown}
			role="presentation"
		>
			<!-- Header -->
			<div class="border-b border-gray-200 p-6 dark:border-gray-700">
				<div class="flex items-center gap-3">
					<div
						class="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100 dark:bg-yellow-900/30"
					>
						<span class="text-2xl">⏰</span>
					</div>
					<div>
						<h2 class="text-xl font-bold text-gray-800 dark:text-white">Sitzung abgelaufen</h2>
						<p class="text-sm text-gray-600 dark:text-gray-400">Bitte melden Sie sich erneut an</p>
					</div>
				</div>
			</div>

			<!-- Content -->
			<div class="p-6">
				<div
					class="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-900/20"
				>
					<p class="text-sm text-yellow-800 dark:text-yellow-300">
						<strong>Ihre Sitzung ist abgelaufen</strong> aufgrund von Inaktivität oder der maximalen
						Sitzungsdauer. Geben Sie Ihr Passwort ein, um fortzufahren.
					</p>
				</div>

				<form on:submit|preventDefault={handleReAuth} class="space-y-4">
					<label class="block">
						<span class="text-sm font-medium text-gray-700 dark:text-gray-300"> Passwort </span>
						<input
							bind:this={passwordInput}
							type="password"
							bind:value={password}
							required
							disabled={isLoading}
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600
								   dark:bg-gray-700 dark:text-white"
							placeholder="Ihr Passwort eingeben"
						/>
					</label>

					{#if error}
						<div
							class="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
						>
							{error}
						</div>
					{/if}

					<div class="flex gap-3">
						<button
							type="submit"
							disabled={isLoading || !password}
							class="flex-1 transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 py-3 font-semibold
								   text-white shadow-lg transition hover:scale-105
								   disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
						>
							{#if isLoading}
								<span class="flex items-center justify-center gap-2">
									<svg class="h-5 w-5 animate-spin" viewBox="0 0 24 24">
										<circle
											class="opacity-25"
											cx="12"
											cy="12"
											r="10"
											stroke="currentColor"
											stroke-width="4"
											fill="none"
										/>
										<path
											class="opacity-75"
											fill="currentColor"
											d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
										/>
									</svg>
									Wird geladen...
								</span>
							{:else}
								Erneut anmelden
							{/if}
						</button>

						<button
							type="button"
							on:click={handleLogout}
							disabled={isLoading}
							class="flex-1 rounded-xl bg-gray-600 py-3 font-semibold text-white shadow-lg
								   transition-colors hover:bg-gray-700
								   disabled:cursor-not-allowed disabled:opacity-50"
						>
							Abmelden
						</button>
					</div>
				</form>
			</div>

			<!-- Footer -->
			<div class="rounded-b-2xl bg-gray-50 px-6 py-4 dark:bg-gray-900">
				<p class="text-center text-xs text-gray-600 dark:text-gray-400">
					💡 Tipp: Wählen Sie bei der Anmeldung eine andere Sicherheitsstufe, um die Sitzungsdauer
					anzupassen
				</p>
			</div>
		</div>
	</div>
{/if}
