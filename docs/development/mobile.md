# Mobile development

Run `corepack pnpm --filter @template/mobile start` on the host. Then choose a development build/device from Expo CLI. This repository does not run simulators in Docker. Set `EXPO_PUBLIC_API_URL` to the API origin: `http://localhost:8000` for iOS simulator, `http://10.0.2.2:8000` for Android emulator, or `http://<host-lan-ip>:8000` for a physical device.

The app's public config is `EXPO_PUBLIC_API_URL`. Never place secrets there. Native access/refresh tokens use SecureStore. Use `corepack pnpm --filter @template/mobile exec expo-doctor`, `corepack pnpm --filter @template/mobile test`, `corepack pnpm --filter @template/mobile typecheck`, and `corepack pnpm --filter @template/mobile exec expo export --platform web` to validate integration without an emulator.
