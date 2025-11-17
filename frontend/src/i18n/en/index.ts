import type { Translation } from '../i18n-types'

const en = {
	// Common
	common: {
		loading: 'Loading...',
		error: 'Error',
		success: 'Success',
		cancel: 'Cancel',
		save: 'Save',
		delete: 'Delete',
		edit: 'Edit',
		confirm: 'Confirm',
		close: 'Close',
		yes: 'Yes',
		no: 'No',
		submit: 'Submit',
		back: 'Back',
		next: 'Next',
		username: 'Username',
		password: 'Password',
		email: 'Email',
		name: 'Name',
		github: 'GitHub',
		imprint: 'Imprint',
		privacy: 'Privacy'
	},

	// App header/title
	app: {
		title: 'Prio Tag',
		subtitle: 'Set priority days for the month'
	},

	// Authentication
	auth: {
		login: {
			title: 'Login',
			username: 'Username',
			password: 'Password',
			keepLoggedIn: 'Keep me logged in',
			keepLoggedInDesc30Days: 'You will stay logged in for 30 days. Recommended for personal devices.',
			keepLoggedInDesc8Hours: 'You will be logged out after 8 hours or when closing the browser. Recommended for shared computers.',
			loginButton: 'Log in',
			loggingIn: 'Logging in...',
			registerButton: 'Register',
			securityNote: 'Stored data is encrypted server-side. We cannot read your personal information.'
		},
		register: {
			title: 'Sign Up',
			subtitle: 'Create account to enter the priority list',
			subtitleMagicWord: 'Please enter the magic word that is posted in the building',
			accessVerification: 'Access Verification',
			qrCodeDetected: 'QR code detected! You can now register.',
			privacyInfo: 'All data is end-to-end encrypted. Only you have access to your information.',
			username: 'Username',
			password: 'Password',
			passwordConfirm: 'Confirm password',
			fullName: 'Full name',
			magicWord: 'Magic word',
			keepLoggedIn: 'Keep me logged in',
			registerButton: 'Register',
			registering: 'Registering...',
			backToLogin: 'Back to login',
			backToMagicWord: '← Back to magic word entry',
			magicWordPlaceholder: 'Enter magic word',
			usernamePlaceholder: 'Enter username',
			passwordPlaceholder: 'Enter password',
			passwordConfirmPlaceholder: 'Enter password again',
			fullNamePlaceholder: 'Enter full name',
			verifyMagicWord: 'Verify magic word',
			verifying: 'Verifying...',
			verified: 'Magic word verified! You can now register.',
			magicWordInfo: 'The magic word can be found in the entrance area of the building',
			errorPasswordMismatch: 'Passwords do not match',
			errorPasswordTooShort: 'Password must be at least 1 character long',
			errorInvalidMagicWord: 'Invalid magic word',
			qrCodeRegistration: 'QR Code Registration',
			traditionalRegistration: 'Traditional Registration'
		},
		logout: 'Log out',
		reauth: {
			title: 'Re-authentication required',
			message: 'Your session has expired. Please log in again.',
			passwordPlaceholder: 'Enter password',
			loginButton: 'Log in',
			cancelButton: 'Cancel'
		}
	},

	// Priorities
	priorities: {
		title: 'Priorities',
		labels: {
			veryImportant: 'Very important',
			important: 'Important',
			normal: 'Normal',
			lessImportant: 'Less important',
			unimportant: 'Unimportant'
		},
		days: {
			monday: 'Monday',
			tuesday: 'Tuesday',
			wednesday: 'Wednesday',
			thursday: 'Thursday',
			friday: 'Friday'
		},
		selectMonth: 'Select month',
		selectYear: 'Select year',
		currentMonth: 'Current month',
		saveChanges: 'Save changes',
		saving: 'Saving...',
		saved: 'Saved',
		savedSuccess: 'Priorities saved successfully',
		errorSaving: 'Error saving',
		errorSavingRetry: 'Error saving. Please try again.',
		errorUniquePriorities: 'Each weekday must have a unique priority',
		noDataForMonth: 'No data for this month',
		clickToSetPriority: 'Click to set priority',
		holiday: 'Holiday',
		vacation: 'Vacation',
		weekend: 'Weekend'
	},

	// Dashboard
	dashboard: {
		title: 'Dashboard',
		welcome: 'Welcome back!',
		welcomeBack: 'Welcome back',
		overview: 'Overview',
		allWeeksComplete: 'Awesome! All weeks for {month} are prioritized!',
		overviewForMonth: 'Here is your overview for {month}',
		selectMonth: 'Select month:',
		loading: 'Loading Dashboard...',
		statistics: 'Statistics',
		recentActivity: 'Recent activity',
		noPrioritiesSet: 'No priorities set',
		setPriorities: 'Set priorities',
		thisMonth: 'This month',
		thisWeek: 'This week',
		today: 'Today',
		upcomingVacation: 'Upcoming vacation',
		noUpcomingVacation: 'No upcoming vacation',
		progress: 'Progress',
		focusDay: 'Focus Day',
		relaxedDay: 'Relaxed Day',
		oftenHighPriority: 'Often with high priority (4-5)',
		oftenLowPriority: 'Often with low priority (1-2)',
		noData: 'No data',
		daysPrioritized: '{count} of {total} days prioritized',
		weekOverview: 'Week Overview - {month}',
		week: 'Week',
		complete: 'Complete',
		inProgress: 'In Progress',
		nextWeekToWorkOn: 'Next week to work on: <strong>Week {weekNumber}</strong>',
		editNow: 'Edit now →',
		accountManagement: 'Account Management',
		accountManagementDesc: 'Change password, View saved data, Delete account',
		manageAccount: 'Manage account →'
	},

	// Account/Settings
	account: {
		title: 'Account',
		settings: 'Settings',
		profile: 'Profile',
		security: 'Security',
		preferences: 'Preferences',
		language: 'Language',
		selectLanguage: 'Select language',
		changePassword: 'Change password',
		currentPassword: 'Current password',
		newPassword: 'New password',
		confirmNewPassword: 'Confirm new password',
		updateProfile: 'Update profile',
		deleteAccount: 'Delete account',
		deleteAccountConfirm: 'Are you sure you want to delete your account? This action cannot be undone.'
	},

	// Vacation
	vacation: {
		title: 'Vacation',
		addVacation: 'Add vacation',
		editVacation: 'Edit vacation',
		deleteVacation: 'Delete vacation',
		startDate: 'Start date',
		endDate: 'End date',
		days: 'Days',
		totalVacationDays: 'Total vacation days',
		remainingVacationDays: 'Remaining vacation days',
		usedVacationDays: 'Used vacation days'
	},

	// Notifications
	notifications: {
		title: 'Notifications',
		noNotifications: 'No notifications',
		markAsRead: 'Mark as read',
		markAllAsRead: 'Mark all as read',
		clearAll: 'Clear all'
	},

	// Errors
	errors: {
		general: 'An error occurred',
		networkError: 'Network error',
		serverError: 'Server error',
		notFound: 'Not found',
		unauthorized: 'Unauthorized',
		forbidden: 'Forbidden',
		validationError: 'Validation error',
		sessionExpired: 'Session expired',
		loginFailed: 'Login failed',
		registrationFailed: 'Registration failed',
		invalidCredentials: 'Invalid credentials',
		userAlreadyExists: 'User already exists',
		passwordTooShort: 'Password too short',
		passwordMismatch: 'Passwords do not match',
		requiredField: 'This field is required',
		invalidEmail: 'Invalid email address',
		invalidDate: 'Invalid date',
		tryAgain: 'Please try again'
	},

	// Success messages
	success: {
		saved: 'Successfully saved',
		updated: 'Successfully updated',
		deleted: 'Successfully deleted',
		created: 'Successfully created',
		loginSuccess: 'Successfully logged in',
		logoutSuccess: 'Successfully logged out',
		registrationSuccess: 'Successfully registered',
		passwordChanged: 'Password successfully changed',
		profileUpdated: 'Profile successfully updated'
	},

	// Admin (minimal, as admin stays German)
	admin: {
		title: 'Admin',
		dashboard: 'Admin Dashboard'
	}
} satisfies Translation

export default en
