import { writable, derived } from 'svelte/store';
import type { ScannerState, AnalysisResult } from '../types/scanner.types';

function createScannerStore() {
	const initialState: ScannerState = {
		cameraActive: false,
		capturedImage: null,
		isProcessing: false,
		analysisResult: null,
		error: null,
		paperDetected: false,
		detectionConfidence: 0,
		captureCountdown: 0
	};

	const { subscribe, set, update } = writable<ScannerState>(initialState);

	return {
		subscribe,
		reset: () => set(initialState),

		setError: (error: string | null) =>
			update((state) => ({
				...state,
				error,
				isProcessing: false
			})),

		setCameraActive: (active: boolean) =>
			update((state) => ({
				...state,
				cameraActive: active,
				error: active ? null : state.error
			})),

		setCapturedImage: (image: string | null) =>
			update((state) => ({
				...state,
				capturedImage: image,
				cameraActive: false,
				paperDetected: false,
				detectionConfidence: 0
			})),

		setProcessing: (processing: boolean) =>
			update((state) => ({
				...state,
				isProcessing: processing
			})),

		setAnalysisResult: (result: AnalysisResult | null) =>
			update((state) => ({
				...state,
				analysisResult: result,
				isProcessing: false
			})),

		setDetectionState: (detected: boolean, confidence: number) =>
			update((state) => ({
				...state,
				paperDetected: detected,
				detectionConfidence: confidence
			})),

		setCaptureCountdown: (countdown: number) =>
			update((state) => ({
				...state,
				captureCountdown: countdown
			}))
	};
}

export const scannerStore = createScannerStore();

// Derived stores for specific state slices
export const isReady = derived(
	scannerStore,
	($state) => !$state.cameraActive && !$state.capturedImage && !$state.error
);

export const canCapture = derived(
	scannerStore,
	($state) => $state.cameraActive && !$state.isProcessing
);

export const hasResults = derived(
	scannerStore,
	($state) => $state.analysisResult !== null && !$state.isProcessing
);
