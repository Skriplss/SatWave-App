## Connect frontend and backend

The Expo app posts images and location to the FastAPI backend via `/webhook/photo`.

Configure the API base URL using `EXPO_PUBLIC_API_URL` so the app can reach your backend:

- Web: `http://localhost:8000` (default)
- iOS simulator: `http://localhost:8000`
- Android emulator: `http://10.0.2.2:8000`
- Physical devices: use your computer LAN IP, e.g. `http://192.168.1.10:8000`

Run backend:

```
docker compose up -d api db
# or
python -m satwave.main
```

Run frontend (Expo):

```
EXPO_PUBLIC_API_URL=http://localhost:8000 bunx rork start --tunnel
```

When you share location in the chat flow, the app will POST the selected image + coordinates to the backend and log the response in the console. If it cannot reach the backend, a friendly message is shown in the chat to check API_URL/CORS.

