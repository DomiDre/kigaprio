import PocketBase from 'pocketbase';

export const pb = new PocketBase('http://pocketbase:8090');
pb.autoCancellation(false);

