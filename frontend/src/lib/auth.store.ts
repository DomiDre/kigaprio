import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { apiService } from '$lib/api.service';

interface AuthState {
	isAuthenticated: boolean;
	userId?: string;
	username?: string;
	role?: string;
}

function createAuthStore() {
	const initialState: AuthState = {
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

	const { subscribe, set } = writable<AuthState>(initialState);

	// Track if we're currently verifying to prevent concurrent calls
	let isVerifying = false;

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
				isAuthenticated: true,
				...userInfo
			});
		},

		/**
		 * Clear authentication state and optionally call logout endpoint
		 * @param callLogoutEndpoint - Whether to call the API logout endpoint (default: true)
		 */
		clearAuth: async (callLogoutEndpoint: boolean = true) => {
			if (browser) {
				// Clear local state
				sessionStorage.removeItem('was_authenticated');

				// Call logout endpoint to clear httpOnly cookies
				// Only if explicitly requested (not on failed auth verification)
				if (callLogoutEndpoint) {
					try {
						await apiService.logout();
					} catch (error) {
						console.error('Logout request failed:', error);
						// Continue anyway - clear local state
					}
				}
			}

			set({
				isAuthenticated: false
			});
		},

		/**
		 * Verify authentication status with server
		 * Call this on app initialization to check if session is still valid
		 */
		verifyAuth: async () => {
			if (!browser) return false;

			// Prevent concurrent verification calls
			if (isVerifying) {
				console.log('Auth verification already in progress, skipping');
				return false;
			}

			isVerifying = true;

			try {
				const data = await apiService.verify();

				set({
					isAuthenticated: true,
					userId: data['user_id'],
					username: data['username']
				});
				sessionStorage.setItem('was_authenticated', 'true');
				return true;
			} catch (error) {
				console.error('Auth verification failed:', error);
				// Don't call logout endpoint on failed verification (already logged out)
				await authStore.clearAuth(false);
				return false;
			} finally {
				isVerifying = false;
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
