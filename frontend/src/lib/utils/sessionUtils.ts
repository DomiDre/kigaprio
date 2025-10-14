import { authStore, type SecurityTier } from '$lib/stores/auth';
import { get } from 'svelte/store';
import { browser } from '$app/environment';

// Session timeout constants (in milliseconds)
export const BALANCED_INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes
export const BALANCED_MAX_SESSION = 8 * 60 * 60 * 1000; // 8 hours

/**
 * Check if the current session is valid based on the security tier
 */
export function isSessionValid(): boolean {
	if (!browser) return false;

	const auth = get(authStore);

	if (!auth.isAuthenticated || !auth.securityTier) {
		return false;
	}

	// High and convenience modes don't expire automatically
	if (auth.securityTier !== 'balanced') {
		return true;
	}

	// Check balanced mode timeouts
	if (!auth.sessionStartTime || !auth.lastActivityTime) {
		return false;
	}

	const now = Date.now();
	const timeSinceActivity = now - auth.lastActivityTime;
	const timeSinceStart = now - auth.sessionStartTime;

	// Check if either timeout has been exceeded
	if (timeSinceActivity > BALANCED_INACTIVITY_TIMEOUT) {
		return false;
	}

	if (timeSinceStart > BALANCED_MAX_SESSION) {
		return false;
	}

	return true;
}

/**
 * Get remaining session time for balanced mode
 * Returns object with remaining time in milliseconds for both timeouts
 */
export function getRemainingSessionTime(): {
	inactivityRemaining: number;
	maxSessionRemaining: number;
	willExpireSoon: boolean;
} | null {
	if (!browser) return null;

	const auth = get(authStore);

	if (auth.securityTier !== 'balanced' || !auth.sessionStartTime || !auth.lastActivityTime) {
		return null;
	}

	const now = Date.now();
	const timeSinceActivity = now - auth.lastActivityTime;
	const timeSinceStart = now - auth.sessionStartTime;

	const inactivityRemaining = BALANCED_INACTIVITY_TIMEOUT - timeSinceActivity;
	const maxSessionRemaining = BALANCED_MAX_SESSION - timeSinceStart;

	// Consider "expiring soon" if less than 5 minutes remain
	const willExpireSoon = Math.min(inactivityRemaining, maxSessionRemaining) < 5 * 60 * 1000;

	return {
		inactivityRemaining: Math.max(0, inactivityRemaining),
		maxSessionRemaining: Math.max(0, maxSessionRemaining),
		willExpireSoon
	};
}

/**
 * Format milliseconds to human-readable time
 */
export function formatTime(ms: number): string {
	const seconds = Math.floor(ms / 1000);
	const minutes = Math.floor(seconds / 60);
	const hours = Math.floor(minutes / 60);

	if (hours > 0) {
		const remainingMinutes = minutes % 60;
		return `${hours}h ${remainingMinutes}m`;
	}

	if (minutes > 0) {
		const remainingSeconds = seconds % 60;
		return `${minutes}m ${remainingSeconds}s`;
	}

	return `${seconds}s`;
}

/**
 * Check if DEK is available for current security tier
 */
export function isDEKAvailable(): boolean {
	if (!browser) return false;

	const tier = authStore.getSecurityTier();
	if (!tier) return false;

	return authStore.hasDEK(tier);
}

/**
 * Get security tier configuration
 */
export function getSecurityTierConfig(tier: SecurityTier): {
	name: string;
	description: string;
	storage: string;
	persistence: string;
	reAuthRequired: string;
} {
	const configs = {
		high: {
			name: 'Hohe Sicherheit',
			description: 'Maximale Sicherheit für gemeinsam genutzte Geräte',
			storage: 'Session Storage (Tab)',
			persistence: 'Bis Tab geschlossen wird',
			reAuthRequired: 'Für jeden neuen Tab'
		},
		balanced: {
			name: 'Ausgewogen',
			description: 'Balance zwischen Sicherheit und Komfort',
			storage: 'Split-Key (Server + Client)',
			persistence: '30min Inaktivität / 8h Maximum',
			reAuthRequired: 'Nach Timeout'
		},
		convenience: {
			name: 'Komfort',
			description: 'Maximaler Komfort für vertrauenswürdige Geräte',
			storage: 'Local Storage (Persistent)',
			persistence: 'Bis zur Abmeldung',
			reAuthRequired: 'Nur bei Abmeldung'
		}
	};

	return configs[tier];
}

/**
 * Security tier comparison helper
 */
export function compareSecurityTiers(tier1: SecurityTier, tier2: SecurityTier): number {
	const order: SecurityTier[] = ['high', 'balanced', 'convenience'];
	return order.indexOf(tier1) - order.indexOf(tier2);
}

/**
 * Check if security tier requires re-authentication
 */
export function requiresReAuth(tier: SecurityTier): boolean {
	return tier === 'high' || tier === 'balanced';
}

/**
 * Validate that the user has the required security level for an action
 */
export function hasRequiredSecurityLevel(
	requiredTier: SecurityTier,
	allowHigher: boolean = true
): boolean {
	const currentTier = authStore.getSecurityTier();
	if (!currentTier) return false;

	if (currentTier === requiredTier) return true;

	if (allowHigher) {
		// If higher security is allowed, check if current is more secure
		return compareSecurityTiers(currentTier, requiredTier) < 0;
	}

	return false;
}

/**
 * Clear sensitive data based on security tier
 */
export function clearSensitiveData(): void {
	if (!browser) return;

	const tier = authStore.getSecurityTier();
	if (!tier) return;

	// Clear DEK
	switch (tier) {
		case 'high':
			sessionStorage.removeItem('dek');
			break;
		case 'balanced':
			sessionStorage.removeItem('client_key_part');
			break;
		case 'convenience':
			localStorage.removeItem('dek');
			break;
	}
}

/**
 * Session warning threshold in milliseconds (5 minutes)
 */
export const SESSION_WARNING_THRESHOLD = 5 * 60 * 1000;

/**
 * Check if session is about to expire
 */
export function isSessionExpiringSoon(): boolean {
	const remaining = getRemainingSessionTime();
	if (!remaining) return false;

	const minRemaining = Math.min(remaining.inactivityRemaining, remaining.maxSessionRemaining);
	return minRemaining < SESSION_WARNING_THRESHOLD && minRemaining > 0;
}
