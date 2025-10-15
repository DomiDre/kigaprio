import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { BALANCED_INACTIVITY_TIMEOUT, BALANCED_MAX_SESSION } from '$lib/utils/sessionUtils';

// Security tier types
export type SecurityTier = 'high' | 'balanced' | 'convenience';

interface AuthState {
	token: string | null;
	isLoading: boolean;
	isAuthenticated: boolean;
	securityTier: SecurityTier | null;
	sessionStartTime: number | null;
	lastActivityTime: number | null;
}

const TOKEN_KEY = 'auth_token';
const DEK_KEY = 'dek';
const CLIENT_KEY_PART = 'client_key_part';
const SECURITY_TIER_KEY = 'security_tier';

// Create the auth store
function createAuthStore() {
	// Initialize state from storage if in browser
	const initialState: AuthState = {
		token: null,
		isLoading: false,
		isAuthenticated: false,
		securityTier: null,
		sessionStartTime: null,
		lastActivityTime: null
	};

	if (browser) {
		// Check for existing token in localStorage
		const storedToken = localStorage.getItem(TOKEN_KEY);

		// Check for existing session in sessionStorage (for page reload)
		const storedTier = sessionStorage.getItem(SECURITY_TIER_KEY) as SecurityTier | null;

		if (storedToken && storedTier) {
			// Verify that DEK is actually available for this tier
			let hasDEK = false;
			if (storedTier === 'high') {
				hasDEK = sessionStorage.getItem(DEK_KEY) !== null;
			} else if (storedTier === 'balanced') {
				hasDEK = sessionStorage.getItem(CLIENT_KEY_PART) !== null;
			} else if (storedTier === 'convenience') {
				hasDEK = localStorage.getItem(DEK_KEY) !== null;
			}

			// Only set as authenticated if we have token, tier, and DEK
			if (hasDEK) {
				initialState.token = storedToken;
				initialState.securityTier = storedTier;
				initialState.isAuthenticated = true;
				initialState.sessionStartTime = Date.now();
				initialState.lastActivityTime = Date.now();
			} else {
				// Clear stale session data if DEK is missing
				localStorage.removeItem(TOKEN_KEY);
				sessionStorage.removeItem(SECURITY_TIER_KEY);
			}
		} else if (storedToken && !storedTier) {
			// Have token but no tier - clear token as it's invalid
			localStorage.removeItem(TOKEN_KEY);
		}
	}

	const { subscribe, set, update } = writable<AuthState>(initialState);

	// Activity tracker for balanced mode
	let activityCheckInterval: ReturnType<typeof setInterval> | null = null;

	const startActivityMonitoring = () => {
		if (activityCheckInterval) return;

		activityCheckInterval = setInterval(() => {
			update((state) => {
				if (state.securityTier !== 'balanced' || !state.isAuthenticated) {
					return state;
				}

				const now = Date.now();
				const timeSinceActivity = now - (state.lastActivityTime || 0);
				const timeSinceStart = now - (state.sessionStartTime || 0);

				// Check for timeout
				if (
					timeSinceActivity > BALANCED_INACTIVITY_TIMEOUT ||
					timeSinceStart > BALANCED_MAX_SESSION
				) {
					// Session expired
					authStore.clearAuth();
					return {
						...state,
						isAuthenticated: false,
						securityTier: null
					};
				}

				return state;
			});
		}, 60000); // Check every minute
	};

	const stopActivityMonitoring = () => {
		if (activityCheckInterval) {
			clearInterval(activityCheckInterval);
			activityCheckInterval = null;
		}
	};

	return {
		subscribe,

		setAuth: (token: string, securityTier: SecurityTier) => {
			if (browser) {
				localStorage.setItem(TOKEN_KEY, token);
				sessionStorage.setItem(SECURITY_TIER_KEY, securityTier);
			}

			const now = Date.now();
			set({
				token,
				isLoading: false,
				isAuthenticated: true,
				securityTier,
				sessionStartTime: now,
				lastActivityTime: now
			});

			if (securityTier === 'balanced') {
				startActivityMonitoring();
			}
		},

		clearAuth: () => {
			if (browser) {
				// Clear all storage based on what might exist
				localStorage.removeItem(TOKEN_KEY);
				sessionStorage.removeItem(DEK_KEY);
				sessionStorage.removeItem(CLIENT_KEY_PART);
				sessionStorage.removeItem(SECURITY_TIER_KEY);
				localStorage.removeItem(DEK_KEY);
			}

			stopActivityMonitoring();

			set({
				token: null,
				isLoading: false,
				isAuthenticated: false,
				securityTier: null,
				sessionStartTime: null,
				lastActivityTime: null
			});
		},

		setLoading: (loading: boolean) => {
			update((state) => ({ ...state, isLoading: loading }));
		},

		updateActivity: () => {
			update((state) => {
				if (state.securityTier === 'balanced' && state.isAuthenticated) {
					return { ...state, lastActivityTime: Date.now() };
				}
				return state;
			});
		},

		// DEK Management Methods
		storeDEK: (dek: string, tier: SecurityTier) => {
			if (!browser) return;

			switch (tier) {
				case 'high':
					// Store in sessionStorage only
					sessionStorage.setItem(DEK_KEY, dek);
					break;
				case 'balanced':
					// This should be the client part only
					sessionStorage.setItem(CLIENT_KEY_PART, dek);
					break;
				case 'convenience':
					// Store in localStorage for persistence
					localStorage.setItem(DEK_KEY, dek);
					break;
			}
		},

		getDEK: (tier: SecurityTier): string | null => {
			if (!browser) return null;

			switch (tier) {
				case 'high':
					return sessionStorage.getItem(DEK_KEY);
				case 'balanced':
					return sessionStorage.getItem(CLIENT_KEY_PART);
				case 'convenience':
					return localStorage.getItem(DEK_KEY);
				default:
					return null;
			}
		},

		// Check if DEK is available
		hasDEK: (tier: SecurityTier): boolean => {
			return authStore.getDEK(tier) !== null;
		},

		getToken: (): string | null => {
			if (browser) {
				return localStorage.getItem(TOKEN_KEY);
			}
			return null;
		},

		updateToken: (newToken: string) => {
			if (browser) {
				localStorage.setItem(TOKEN_KEY, newToken);
			}
			update((state) => ({
				...state,
				token: newToken
			}));
		},

		getSecurityTier: (): SecurityTier | null => {
			if (browser) {
				return sessionStorage.getItem(SECURITY_TIER_KEY) as SecurityTier | null;
			}
			return null;
		}
	};
}

export const authStore = createAuthStore();

// Derived stores
export const isAuthenticated = derived(authStore, ($auth) => $auth.isAuthenticated);
export const authToken = derived(authStore, ($auth) => $auth.token);
export const securityTier = derived(authStore, ($auth) => $auth.securityTier);
export const sessionInfo = derived(authStore, ($auth) => ({
	startTime: $auth.sessionStartTime,
	lastActivity: $auth.lastActivityTime
}));
