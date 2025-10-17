import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { apiService } from '$lib/services/api';

interface AuthState {
	isLoading: boolean;
	isAuthenticated: boolean;
	userId?: string;
	username?: string;
	role?: string;
}

function createAuthStore() {
	const initialState: AuthState = {
		isLoading: false,
		isAuthenticated: false
	};

	// On page load, check if we have a stored security mode
	// actual auth is verified via API call
	if (browser) {
		const wasAuthenticated = sessionStorage.getItem('was_authenticated');
		if (wasAuthenticated === 'true') {
			initialState.isAuthenticated = true; // Tentative - will verify via API
		}
	}

	const { subscribe, set, update } = writable<AuthState>(initialState);

	return {
		subscribe,

		/**
		 * Set authentication state after successful login
		 */
		setAuth: (userInfo?: { userId: string; username: string; role: string }) => {
			if (browser) {
				sessionStorage.setItem('was_authenticated', 'true');
			}

			set({
				isLoading: false,
				isAuthenticated: true,
				...userInfo
			});
		},

		/**
		 * Clear authentication state and call logout endpoint
		 */
		clearAuth: async () => {
			if (browser) {
				// Clear local state
				sessionStorage.removeItem('was_authenticated');

				// Call logout endpoint to clear httpOnly cookies
				try {
					await apiService.logout();
				} catch (error) {
					console.error('Logout request failed:', error);
					// Continue anyway - clear local state
				}
			}

			set({
				isLoading: false,
				isAuthenticated: false
			});
		},

		/**
		 * Set loading state (for UI spinners)
		 */
		setLoading: (loading: boolean) => {
			update((state) => ({ ...state, isLoading: loading }));
		},

		/**
		 * Verify authentication status with server
		 * Call this on app initialization to check if session is still valid
		 */
		verifyAuth: async () => {
			if (!browser) return false;

			try {
				const data = await apiService.verify();

				set({
					isLoading: false,
					isAuthenticated: true,
					userId: data['user_id'],
					username: data['username']
				});
			} catch (error) {
				console.error('Auth verification failed:', error);
				authStore.clearAuth();
				return false;
			}
		}
	};
}

export const authStore = createAuthStore();

// ============================================================================
// DERIVED STORES
// ============================================================================

export const isAuthenticated = derived(authStore, ($auth) => $auth.isAuthenticated);

export const currentUser = derived(authStore, ($auth) => ({
	userId: $auth.userId,
	username: $auth.username,
	role: $auth.role
}));
