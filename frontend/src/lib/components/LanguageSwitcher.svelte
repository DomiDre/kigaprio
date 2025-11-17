<script lang="ts">
	import { locale, setLocale } from '$i18n/i18n-svelte';
	import { loadLocaleAsync } from '$i18n/i18n-util.async';
	import { saveLocale } from '$i18n/i18n-setup';
	import type { Locales } from '$i18n/i18n-types';

	const languages: { code: Locales; label: string; flag: string }[] = [
		{ code: 'de', label: 'Deutsch', flag: '🇩🇪' },
		{ code: 'en', label: 'English', flag: '🇬🇧' }
	];

	async function switchLanguage(newLocale: Locales) {
		if ($locale === newLocale) return;

		// Load the new locale
		await loadLocaleAsync(newLocale);

		// Update the current locale
		setLocale(newLocale);

		// Save to localStorage
		saveLocale(newLocale);
	}
</script>

<div class="flex items-center gap-2">
	{#each languages as lang}
		<button
			type="button"
			onclick={() => switchLanguage(lang.code)}
			class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors
					 {$locale === lang.code
				? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200'
				: 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'}"
			aria-label={lang.label}
			aria-current={$locale === lang.code ? 'true' : 'false'}
		>
			<span class="text-lg">{lang.flag}</span>
			<span>{lang.label}</span>
		</button>
	{/each}
</div>
