import { authStore, type SecurityTier } from '$lib/stores/auth';
import { goto } from '$app/navigation';
import { browser } from '$app/environment';
import type { PriorityResponse, WeekData } from '$lib/types/priorities';

export class ApiService {
	public baseUrl: string;

	constructor() {
		this.baseUrl = import.meta.env.DEV
			? 'http://localhost:8000/api/v1' // Dev mode - full URL to FastAPI
			: '/api/v1'; // Prod mode - relative path
	}

	// Method to check API health
	async healthCheck(): Promise<boolean> {
		try {
			const response = await fetch(`${this.baseUrl}/health`, {
				method: 'GET',
				signal: AbortSignal.timeout(5000)
			});
			return response.ok;
		} catch {
			return false;
		}
	}

	private async request(endpoint: string, options: RequestInit = {}) {
		const token = authStore.getToken();

		const config: RequestInit = {
			...options,
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			}
		};

		// Add auth token if available
		if (token) {
			config.headers = {
				...config.headers,
				Authorization: `Bearer ${token}`
			};
		}

		// Update activity for balanced mode
		authStore.updateActivity();

		const response = await fetch(`${this.baseUrl}${endpoint}`, config);

		// Check for refreshed token in response header
		const newToken = response.headers.get('X-New-Token');
		if (newToken && newToken !== token) {
			console.debug('Token refreshed, updating local storage');
			authStore.updateToken(newToken);
		}

		// Handle 401 Unauthorized - session expired
		if (response.status === 401) {
			authStore.clearAuth();
			if (browser) {
				goto('/login');
			}
			throw new Error('Sitzung abgelaufen. Bitte melden Sie sich erneut an.');
		}

		// Handle 403 Forbidden - not authorized
		if (response.status === 403) {
			throw new Error('Keine Berechtigung für diese Aktion.');
		}

		// Handle rate limiting
		if (response.status === 429) {
			const data = await response.json();
			throw new Error(data.detail || 'Zu viele Anfragen. Bitte versuchen Sie es später erneut.');
		}

		if (!response.ok) {
			const data = await response.json();
			throw new Error(data.detail || 'Ein Fehler ist aufgetreten');
		}

		return response;
	}

	private async requestJson(endpoint: string, options: RequestInit = {}) {
		const response = await this.request(endpoint, options);
		return response.json();
	}

	// Helper to get DEK based on current security tier
	private getDEKForRequest(): string | null {
		const tier = authStore.getSecurityTier();
		if (!tier) return null;
		return authStore.getDEK(tier);
	}

	// ==================== Authentication ====================

	async login(identity: string, password: string, securityTier: SecurityTier) {
		const response = await this.requestJson('/auth/login', {
			method: 'POST',
			body: JSON.stringify({
				identity,
				password,
				security_tier: securityTier
			})
		});

		// Store auth data
		authStore.setAuth(response.token, securityTier);

		// Store DEK based on security tier
		if (securityTier === 'balanced') {
			// For balanced mode, we get client_key_part
			authStore.storeDEK(response.client_key_part, securityTier);
		} else {
			// For high/convenience, we get the full DEK
			authStore.storeDEK(response.dek, securityTier);
		}

		return response;
	}

	async logout() {
		try {
			await this.requestJson('/auth/logout', {
				method: 'POST'
			});
		} catch (error) {
			console.error('Logout error:', error);
		}

		authStore.clearAuth();
	}

	async register(data: {
		identity: string;
		password: string;
		passwordConfirm: string;
		name: string;
		registration_token: string;
		security_tier: SecurityTier;
	}) {
		const response = await this.requestJson('/auth/register', {
			method: 'POST',
			body: JSON.stringify(data)
		});

		// After registration, user is logged in
		authStore.setAuth(response.token, data.security_tier);

		if (data.security_tier === 'balanced') {
			authStore.storeDEK(response.client_key_part, data.security_tier);
		} else {
			authStore.storeDEK(response.dek, data.security_tier);
		}

		return response;
	}

	async changePassword(currentPassword: string, newPassword: string) {
		const dek = this.getDEKForRequest();
		if (!dek) {
			throw new Error('Keine Verschlüsselungsschlüssel verfügbar');
		}

		const response = await this.requestJson('/auth/change-password', {
			method: 'POST',
			body: JSON.stringify({
				current_password: currentPassword,
				new_password: newPassword,
				dek // Server needs this to rewrap
			})
		});

		// Password change invalidates all sessions
		// User needs to log in again
		authStore.clearAuth();
		if (browser) {
			goto('/login');
		}

		return response;
	}

	// Re-authenticate for expired balanced mode sessions
	async reAuthenticate(password: string) {
		const tier = authStore.getSecurityTier();
		if (!tier) {
			throw new Error('Keine Sicherheitsstufe gesetzt');
		}

		return this.login('', password, tier); // Identity can be retrieved from token
	}

	// ==================== Priorities ====================

	async getPriorities(month?: string): Promise<PriorityResponse> {
		const dek = this.getDEKForRequest();
		if (!dek) {
			throw new Error('Keine Verschlüsselungsschlüssel verfügbar');
		}

		const endpoint = month ? `/priorities/${month}` : '/priorities';

		return this.requestJson(endpoint, {
			method: 'GET',
			headers: { "x-dek": dek }
		});
	}

	async updatePriority(
		month: string,
		priorityData: WeekData[]) {
		const dek = this.getDEKForRequest();
		if (!dek) {
			throw new Error('Keine Verschlüsselungsschlüssel verfügbar');
		}

		return this.requestJson(`/priorities/${month}`, {
			method: 'PUT',
			body: JSON.stringify(priorityData),
			headers: { "x-dek": dek }
		});
	}

	// ==================== Admin Endpoints ====================

	async getMagicWordInfo() {
		return this.requestJson('/admin/magic-word-info', {
			method: 'GET'
		});
	}

	async updateMagicWord(newMagicWord: string) {
		return this.requestJson('/admin/update-magic-word', {
			method: 'POST',
			body: JSON.stringify({ new_magic_word: newMagicWord })
		});
	}

	async getUserSubmissions(month: string) {
		// Admin needs their DEK to decrypt user data
		const dek = this.getDEKForRequest();
		if (!dek) {
			throw new Error('Keine Verschlüsselungsschlüssel verfügbar');
		}

		return this.requestJson(`/admin/users/${month}`, {
			method: 'GET',
		});
	}
}

// Export singleton instance
export const apiService = new ApiService();
