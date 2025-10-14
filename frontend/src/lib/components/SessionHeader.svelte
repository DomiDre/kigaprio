<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { authStore, securityTier, isAuthenticated } from '$lib/stores/auth';
	import {
		getRemainingSessionTime,
		formatTime,
		getSecurityTierConfig
	} from '$lib/utils/sessionUtils';
	import type { SecurityTier } from '$lib/stores/auth';

	export let onReAuthRequired: (() => void) | null = null;

	let remainingTime: ReturnType<typeof getRemainingSessionTime> = null;
	let currentTier: SecurityTier | null = null;
	let updateInterval: ReturnType<typeof setInterval> | null = null;
	let showDropdown = false;

	$: if ($securityTier) {
		currentTier = $securityTier;
	}

	function updateSessionInfo() {
		if (!$isAuthenticated || currentTier !== 'balanced') {
			return;
		}

		remainingTime = getRemainingSessionTime();

		// If session expired, trigger re-auth
		if (
			remainingTime &&
			remainingTime.inactivityRemaining <= 0 &&
			remainingTime.maxSessionRemaining <= 0
		) {
			if (onReAuthRequired) {
				onReAuthRequired();
			} else {
				authStore.clearAuth();
			}
		}
	}

	onMount(() => {
		updateSessionInfo();
		if (currentTier === 'balanced') {
			updateInterval = setInterval(updateSessionInfo, 10000);
		}
	});

	onDestroy(() => {
		if (updateInterval) {
			clearInterval(updateInterval);
		}
	});

	function getStatusIcon(): string {
		if (!remainingTime) return '🟢';
		const minRemaining = Math.min(
			remainingTime.inactivityRemaining,
			remainingTime.maxSessionRemaining
		);
		if (minRemaining < 5 * 60 * 1000) return '🔴';
		if (minRemaining < 10 * 60 * 1000) return '🟡';
		return '🟢';
	}

	function getTierIcon(): string {
		if (currentTier === 'high') return '🔒';
		if (currentTier === 'balanced') return '⚖️';
		return '✨';
	}

	function toggleDropdown() {
		showDropdown = !showDropdown;
	}

	// Close dropdown when clicking outside
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.session-header-dropdown')) {
			showDropdown = false;
		}
	}

	onMount(() => {
		document.addEventListener('click', handleClickOutside);
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});
</script>

{#if $isAuthenticated && currentTier}
	<div class="session-header-dropdown relative">
		<!-- Compact Status Button -->
		<button
			on:click={toggleDropdown}
			class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3
				   py-2 shadow-sm transition-colors hover:bg-gray-50
				   dark:border-gray-600 dark:bg-gray-800 dark:hover:bg-gray-700"
		>
			<span class="text-lg">{getTierIcon()}</span>
			{#if currentTier === 'balanced' && remainingTime}
				<span class="font-mono text-sm font-semibold text-gray-700 dark:text-gray-300">
					{formatTime(
						Math.min(remainingTime.inactivityRemaining, remainingTime.maxSessionRemaining)
					)}
				</span>
				<span class="text-lg">{getStatusIcon()}</span>
			{:else}
				<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
					{getSecurityTierConfig(currentTier).name}
				</span>
			{/if}
			<span class="text-xs text-gray-400">▼</span>
		</button>

		<!-- Dropdown Details -->
		{#if showDropdown}
			<div
				class="absolute right-0 z-50 mt-2 w-72 rounded-xl border-2 border-gray-200
					   bg-white p-4 shadow-xl dark:border-gray-700 dark:bg-gray-800"
			>
				<!-- Header -->
				<div
					class="mb-3 flex items-center gap-2 border-b border-gray-200 pb-3 dark:border-gray-700"
				>
					<span class="text-2xl">{getTierIcon()}</span>
					<div class="flex-1">
						<h4 class="font-semibold text-gray-800 dark:text-white">
							{getSecurityTierConfig(currentTier).name}
						</h4>
						<p class="text-xs text-gray-600 dark:text-gray-400">Aktuelle Sitzung</p>
					</div>
				</div>

				<!-- Timer for Balanced Mode -->
				{#if currentTier === 'balanced' && remainingTime}
					<div class="mb-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
						<div class="space-y-2">
							<div class="flex items-center justify-between">
								<span class="text-xs text-gray-600 dark:text-gray-400">Inaktivität:</span>
								<span class="font-mono text-sm font-semibold text-gray-800 dark:text-white">
									{formatTime(remainingTime.inactivityRemaining)}
								</span>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-xs text-gray-600 dark:text-gray-400">Max. Sitzung:</span>
								<span class="font-mono text-sm font-semibold text-gray-800 dark:text-white">
									{formatTime(remainingTime.maxSessionRemaining)}
								</span>
							</div>
						</div>

						{#if remainingTime.willExpireSoon}
							<div
								class="mt-2 rounded border border-yellow-300 bg-yellow-50 p-2 dark:border-yellow-700 dark:bg-yellow-900/20"
							>
								<p class="text-center text-xs font-medium text-yellow-800 dark:text-yellow-300">
									⚠️ Sitzung läuft bald ab
								</p>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Session Details -->
				<div class="space-y-2 text-xs">
					<div class="flex justify-between">
						<span class="text-gray-600 dark:text-gray-400">Speicherung:</span>
						<span class="font-medium text-gray-800 dark:text-white">
							{getSecurityTierConfig(currentTier).storage}
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-600 dark:text-gray-400">Gültigkeit:</span>
						<span class="font-medium text-gray-800 dark:text-white">
							{getSecurityTierConfig(currentTier).persistence}
						</span>
					</div>
				</div>

				<!-- Info -->
				<div class="mt-3 border-t border-gray-200 pt-3 dark:border-gray-700">
					<p class="text-center text-xs text-gray-600 dark:text-gray-400">
						💡 Sie können die Sicherheitsstufe bei der nächsten Anmeldung ändern
					</p>
				</div>
			</div>
		{/if}
	</div>
{/if}
