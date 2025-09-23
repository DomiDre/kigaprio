import PocketBase from 'pocketbase';

// In dev, Vite serves the app, so we need the full URL
// In prod, the app is served from the same domain, so we use relative path
const pbUrl = import.meta.env.DEV
	? 'http://localhost:8000/api/v1/pb' // Dev mode - full URL to FastAPI
	: '/api/v1/pb'; // Prod mode - relative path

export const pb = new PocketBase(pbUrl);
pb.autoCancellation(false);
