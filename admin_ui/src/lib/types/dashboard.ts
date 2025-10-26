// Types for admin user submission data
export interface UserPriorityRecord {
	adminWrappedDek: string;
	userName: string;
	month: string;
	userEncryptedFields: string;
	prioritiesEncryptedFields: string;
}

// Extended type for UI display with computed properties
export interface UserSubmissionDisplay extends UserPriorityRecord {
	submitted: boolean;
	encrypted: boolean;
	// These will be populated after decryption
	decryptedName?: string;
	decryptedPriorities?: any;
}

export interface UserDisplay {
	id: number;
	name: string;
	submitted: boolean;
	encrypted: boolean;
	hasData: boolean;
	adminWrappedDek?: string;
	userEncryptedFields?: string;
	prioritiesEncryptedFields?: string;
}

export interface Stats {
	totalUsers: number;
	submitted: number;
	pending: number;
	submissionRate: number;
}

export interface DecryptedData {
	userName: string;
	userData: any;
	priorities: any;
}
