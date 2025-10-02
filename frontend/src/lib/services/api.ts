import { authStore } from '$lib/stores/auth';
import { goto } from '$app/navigation';
import { browser } from '$app/environment';

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

		// Handle rate limiting
		if (response.status === 429) {
			const data = await response.json();
			throw new Error(data.detail || 'Zu viele Anfragen. Bitte versuchen Sie es später erneut.');
		}

		if (!response.ok) {
			const data = await response.json();
			throw new Error(data.detail || 'Ein Fehler ist aufgetreten');
		}

		return response.json();
	}

	async login(identity: string, password: string) {
		const response = await this.request('/login', {
			method: 'POST',
			body: JSON.stringify({ identity, password })
		});

		// Store auth data
		authStore.setAuth(response.token, response.record);

		return response;
	}

	async logout() {
		try {
			await this.request('/logout', {
				method: 'POST'
			});
		} catch (error) {
			console.error('Logout error:', error);
		}

		authStore.clearAuth();
	}

	async refreshToken() {
		const token = authStore.getToken();
		if (!token) {
			throw new Error('Kein Token verfügbar');
		}

		const response = await this.request('/refresh', {
			method: 'POST',
			body: JSON.stringify({ token })
		});

		authStore.setAuth(response.token, response.record);
		return response;
	}

	async verifyMagicWord(magicWord: string) {
		return this.request('/verify-magic-word', {
			method: 'POST',
			body: JSON.stringify({ magic_word: magicWord })
		});
	}

	async register(data: {
		email: string;
		password: string;
		passwordConfirm: string;
		name: string;
		registration_token: string;
	}) {
		return this.request('/register', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async getPriorities(month?: string) {
		const params = new URLSearchParams();
		if (month) {
			params.append('month', month);
		}
		const queryString = params.toString();
		const endpoint = queryString ? `/priorities?${queryString}` : '/priorities';

		return this.request(endpoint, {
			method: 'GET'
		});
	}

	async createPriority(data: {
		userId: string;
		month: string;
		weekNumber: number;
		priorities: any;
		startDate: string;
		endDate: string;
	}) {
		return this.request('/priorities', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async updatePriority(
		id: string,
		data: {
			userId: string;
			month: string;
			weekNumber: number;
			priorities: any;
			startDate: string;
			endDate: string;
		}
	) {
		return this.request(`/priorities/${id}`, {
			method: 'PATCH',
			body: JSON.stringify(data)
		});
	}

	async exportMonthData(month: string): Promise<Blob> {
		const response = await this.request(`/export/${month}`, {
			method: 'GET',
		});

		if (!response.ok) {
			throw new Error('Export failed');
		}

		// Return as Blob directly
		return await response.blob();
	}

	async sendReminders(userIds: string[], message: string): Promise<{
		sent: number;
		failed: number;
		details: Array<{
			userId: string;
			email: string;
			status: 'sent' | 'failed';
			error?: string;
		}>;
	}> {
		const response = await this.request('/reminders/send', {
			method: 'POST',
			body: JSON.stringify({
				userIds,
				message,
			}),
		});

		if (!response.ok) {
			throw new Error('Failed to send reminders');
		}

		return await response.json();
	}
}

// Export singleton instance
export const apiService = new ApiService();
