import type { BaseTranslation } from '../i18n-types'

const de = {
	// Common
	common: {
		loading: 'Lade...',
		error: 'Fehler',
		success: 'Erfolg',
		cancel: 'Abbrechen',
		save: 'Speichern',
		delete: 'Löschen',
		edit: 'Bearbeiten',
		confirm: 'Bestätigen',
		close: 'Schließen',
		yes: 'Ja',
		no: 'Nein',
		submit: 'Absenden',
		back: 'Zurück',
		next: 'Weiter',
		username: 'Username',
		password: 'Passwort',
		email: 'E-Mail',
		name: 'Name',
		github: 'GitHub',
		imprint: 'Impressum',
		privacy: 'Datenschutz'
	},

	// App header/title
	app: {
		title: 'Prio Tag',
		subtitle: 'Prio Tage für den Monat festlegen'
	},

	// Authentication
	auth: {
		login: {
			title: 'Anmelden',
			username: 'Username',
			password: 'Passwort',
			keepLoggedIn: 'Angemeldet bleiben',
			keepLoggedInDesc30Days: 'Sie bleiben 30 Tage angemeldet. Empfohlen für persönliche Geräte.',
			keepLoggedInDesc8Hours: 'Sie werden nach 8 Stunden oder beim Schließen des Browsers abgemeldet. Empfohlen für gemeinsam genutzte Computer.',
			loginButton: 'Anmelden',
			loggingIn: 'Wird angemeldet...',
			registerButton: 'Registrieren',
			securityNote: 'Gespeicherte Daten werden Serverseitig verschlüsselt. Wir können Ihre persönlichen Informationen nicht lesen.'
		},
		register: {
			title: 'Anmelden',
			subtitle: 'Account zur Eingabe der Prioliste erstellen',
			subtitleMagicWord: 'Bitte geben Sie das Zauberwort ein, das im Gebäude hinterlegt ist',
			accessVerification: 'Zugangsverifizierung',
			qrCodeDetected: 'QR-Code erkannt! Sie können sich jetzt registrieren.',
			privacyInfo: 'Alle Daten werden End-to-End verschlüsselt. Nur Sie haben Zugang zu Ihren Informationen.',
			username: 'Username',
			password: 'Passwort',
			passwordConfirm: 'Passwort bestätigen',
			fullName: 'Vollständiger Name',
			magicWord: 'Zauberwort',
			keepLoggedIn: 'Angemeldet bleiben',
			registerButton: 'Registrieren',
			registering: 'Wird registriert...',
			backToLogin: 'Zurück zum Login',
			backToMagicWord: '← Zurück zur Zauberwort-Eingabe',
			magicWordPlaceholder: 'Zauberwort eingeben',
			usernamePlaceholder: 'Username eingeben',
			passwordPlaceholder: 'Passwort eingeben',
			passwordConfirmPlaceholder: 'Nochmal Passwort eingeben',
			fullNamePlaceholder: 'Vollständiger Name eingeben',
			verifyMagicWord: 'Zauberwort überprüfen',
			verifying: 'Überprüfe...',
			verified: 'Zauberwort verifiziert! Sie können sich jetzt registrieren.',
			magicWordInfo: 'Das Zauberwort finden Sie im Eingangsbereich des Gebäudes',
			errorPasswordMismatch: 'Passwörter stimmen nicht überein',
			errorPasswordTooShort: 'Password must be at least 1 character long',
			errorInvalidMagicWord: 'Ungültiges Zauberwort',
			qrCodeRegistration: 'QR-Code Registrierung',
			traditionalRegistration: 'Normale Registrierung'
		},
		logout: 'Abmelden',
		reauth: {
			title: 'Erneute Anmeldung erforderlich',
			message: 'Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.',
			passwordPlaceholder: 'Passwort eingeben',
			loginButton: 'Anmelden',
			cancelButton: 'Abbrechen'
		}
	},

	// Priorities
	priorities: {
		title: 'Prioritäten',
		labels: {
			veryImportant: 'Sehr wichtig',
			important: 'Wichtig',
			normal: 'Normal',
			lessImportant: 'Weniger wichtig',
			unimportant: 'Unwichtig'
		},
		days: {
			monday: 'Montag',
			tuesday: 'Dienstag',
			wednesday: 'Mittwoch',
			thursday: 'Donnerstag',
			friday: 'Freitag'
		},
		selectMonth: 'Monat auswählen',
		selectYear: 'Jahr auswählen',
		currentMonth: 'Aktueller Monat',
		saveChanges: 'Änderungen speichern',
		saving: 'Wird gespeichert...',
		saved: 'Gespeichert',
		savedSuccess: 'Prioritäten erfolgreich gespeichert',
		errorSaving: 'Fehler beim Speichern',
		errorSavingRetry: 'Fehler beim Speichern. Bitte versuchen Sie es erneut.',
		errorUniquePriorities: 'Jeder Wochentag muss eine eindeutige Priorität haben',
		noDataForMonth: 'Keine Daten für diesen Monat',
		clickToSetPriority: 'Klicken Sie, um die Priorität zu setzen',
		holiday: 'Feiertag',
		vacation: 'Urlaub',
		weekend: 'Wochenende'
	},

	// Dashboard
	dashboard: {
		title: 'Dashboard',
		welcome: 'Willkommen zurück!',
		welcomeBack: 'Willkommen zurück',
		overview: 'Übersicht',
		allWeeksComplete: 'Super! Alle Wochen für {month:string} sind priorisiert!',
		overviewForMonth: 'Hier ist Ihre Übersicht für {month:string}',
		selectMonth: 'Monat auswählen:',
		loading: 'Lade Dashboard...',
		statistics: 'Statistiken',
		recentActivity: 'Letzte Aktivität',
		noPrioritiesSet: 'Keine Prioritäten gesetzt',
		setPriorities: 'Prioritäten setzen',
		thisMonth: 'Diesen Monat',
		thisWeek: 'Diese Woche',
		today: 'Heute',
		upcomingVacation: 'Kommender Urlaub',
		noUpcomingVacation: 'Kein kommender Urlaub',
		progress: 'Fortschritt',
		focusDay: 'Fokus-Tag',
		relaxedDay: 'Entspannter Tag',
		oftenHighPriority: 'Oft mit hoher Priorität (4-5)',
		oftenLowPriority: 'Oft mit niedriger Priorität (1-2)',
		noData: 'Keine Daten',
		daysPrioritized: '{count:number} von {total:number} Tagen priorisiert',
		weekOverview: 'Wochenübersicht - {month:string}',
		week: 'Woche',
		complete: 'Vollständig',
		inProgress: 'In Bearbeitung',
		nextWeekToWorkOn: 'Nächste zu bearbeitende Woche: <strong>Woche {weekNumber:number}</strong>',
		editNow: 'Jetzt bearbeiten →',
		accountManagement: 'Account-Verwaltung',
		accountManagementDesc: 'Passwort ändern, Gespeicherte Daten einsehen, Account löschen',
		manageAccount: 'Account verwalten →'
	},

	// Account/Settings
	account: {
		title: 'Konto',
		settings: 'Einstellungen',
		profile: 'Profil',
		security: 'Sicherheit',
		preferences: 'Einstellungen',
		language: 'Sprache',
		selectLanguage: 'Sprache auswählen',
		changePassword: 'Passwort ändern',
		currentPassword: 'Aktuelles Passwort',
		newPassword: 'Neues Passwort',
		confirmNewPassword: 'Neues Passwort bestätigen',
		updateProfile: 'Profil aktualisieren',
		deleteAccount: 'Konto löschen',
		deleteAccountConfirm: 'Möchten Sie Ihr Konto wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.'
	},

	// Vacation
	vacation: {
		title: 'Urlaub',
		addVacation: 'Urlaub hinzufügen',
		editVacation: 'Urlaub bearbeiten',
		deleteVacation: 'Urlaub löschen',
		startDate: 'Startdatum',
		endDate: 'Enddatum',
		days: 'Tage',
		totalVacationDays: 'Gesamte Urlaubstage',
		remainingVacationDays: 'Verbleibende Urlaubstage',
		usedVacationDays: 'Genutzte Urlaubstage'
	},

	// Notifications
	notifications: {
		title: 'Benachrichtigungen',
		noNotifications: 'Keine Benachrichtigungen',
		markAsRead: 'Als gelesen markieren',
		markAllAsRead: 'Alle als gelesen markieren',
		clearAll: 'Alle löschen'
	},

	// Errors
	errors: {
		general: 'Ein Fehler ist aufgetreten',
		networkError: 'Netzwerkfehler',
		serverError: 'Serverfehler',
		notFound: 'Nicht gefunden',
		unauthorized: 'Nicht autorisiert',
		forbidden: 'Verboten',
		validationError: 'Validierungsfehler',
		sessionExpired: 'Sitzung abgelaufen',
		loginFailed: 'Anmeldung fehlgeschlagen',
		registrationFailed: 'Registrierung fehlgeschlagen',
		invalidCredentials: 'Ungültige Anmeldedaten',
		userAlreadyExists: 'Benutzer existiert bereits',
		passwordTooShort: 'Passwort zu kurz',
		passwordMismatch: 'Passwörter stimmen nicht überein',
		requiredField: 'Dieses Feld ist erforderlich',
		invalidEmail: 'Ungültige E-Mail-Adresse',
		invalidDate: 'Ungültiges Datum',
		tryAgain: 'Bitte versuchen Sie es erneut'
	},

	// Success messages
	success: {
		saved: 'Erfolgreich gespeichert',
		updated: 'Erfolgreich aktualisiert',
		deleted: 'Erfolgreich gelöscht',
		created: 'Erfolgreich erstellt',
		loginSuccess: 'Erfolgreich angemeldet',
		logoutSuccess: 'Erfolgreich abgemeldet',
		registrationSuccess: 'Erfolgreich registriert',
		passwordChanged: 'Passwort erfolgreich geändert',
		profileUpdated: 'Profil erfolgreich aktualisiert'
	},

	// Admin (minimal, as admin stays German)
	admin: {
		title: 'Admin',
		dashboard: 'Admin Dashboard'
	}
} satisfies BaseTranslation

export default de
