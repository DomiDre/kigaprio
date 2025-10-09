import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';

interface AuthState {
	token: string | null;
	isLoading: boolean;
	isAuthenticated: boolean;
}

const TOKEN_KEY = 'auth_token';

// Create the auth store
function createAuthStore() {
	// Initialize state from localStorage if in browser
	const initialState: AuthState = {
		token: null,
		isLoading: false,
		isAuthenticated: false
	};

	if (browser) {
		const storedToken = localStorage.getItem(TOKEN_KEY);

		if (storedToken) {
			try {
				initialState.token = storedToken;
				initialState.isAuthenticated = true;
			} catch {
				console.error('Failed to parse stored user data');
				localStorage.removeItem(TOKEN_KEY);
			}
		}
	}

	const { subscribe, set, update } = writable<AuthState>(initialState);

	return {
		subscribe,

		setAuth: (token: string) => {
			if (browser) {
				localStorage.setItem(TOKEN_KEY, token);
			}
			set({
				token,
				isLoading: false,
				isAuthenticated: true
			});
		},

		clearAuth: () => {
			if (browser) {
				localStorage.removeItem(TOKEN_KEY);
			}
			set({
				token: null,
				isLoading: false,
				isAuthenticated: false
			});
		},

		setLoading: (loading: boolean) => {
			update((state) => ({ ...state, isLoading: loading }));
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
		}
	};
}

export const authStore = createAuthStore();
export const isAuthenticated = derived(authStore, ($auth) => $auth.isAuthenticated);
export const authToken = derived(authStore, ($auth) => $auth.token);
