// i18n setup and locale detection
import type { Locales } from './i18n-types';
import { loadLocaleAsync } from './i18n-util.async';

const LOCALE_STORAGE_KEY = 'priotag-locale';

/**
 * Get available locales
 */
export const availableLocales: Locales[] = ['de', 'en'];

/**
 * Default locale if none can be detected
 */
export const defaultLocale: Locales = 'de';

/**
 * Get locale from localStorage
 */
function getStoredLocale(): Locales | null {
	if (typeof window === 'undefined') return null;

	const stored = localStorage.getItem(LOCALE_STORAGE_KEY) as Locales | null;
	if (stored && availableLocales.includes(stored)) {
		return stored;
	}
	return null;
}

/**
 * Save locale to localStorage
 */
export function saveLocale(locale: Locales): void {
	if (typeof window === 'undefined') return;
	localStorage.setItem(LOCALE_STORAGE_KEY, locale);
}

/**
 * Detect user's preferred locale from:
 * 1. localStorage (previously saved)
 * 2. Browser language
 * 3. Default locale (German)
 */
export function detectUserLocale(): Locales {
	// First check localStorage
	const stored = getStoredLocale();
	if (stored) {
		return stored;
	}

	// Then check browser language
	if (typeof window !== 'undefined') {
		const lang = navigator.language.toLowerCase();
		// Map browser languages to our locales
		if (lang.startsWith('en')) return 'en';
		if (lang.startsWith('de')) return 'de';
	}

	return defaultLocale;
}

/**
 * Initialize i18n with detected locale
 */
export async function initI18n() {
	const locale = detectUserLocale();
	await loadLocaleAsync(locale);
	return locale;
}
