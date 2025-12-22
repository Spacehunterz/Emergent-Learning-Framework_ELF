# Workspace Rules for ELF & Spacehunterz

To ensure high-quality code and consistent architecture for the **Emergent Learning Framework (ELF)** and the **Spacehunterz** game, follow these guidelines.

## 1. Tech Stack & Standards
- **Framework**: React 18+ (TypeScript), Vite.
- **Styling**: Tailwind CSS (Primary), standard CSS modules if needed for complex animations.
- **3D Engine**: React Three Fiber (R3F) / Three.js.
- **State Management**: 
  - **Zustand**: For high-frequency game state (Enemies, Projectiles, World).
  - **React Context**: For UI state (Theme, Auth, Routes).

## 2. Spacehunterz Game Architecture
The game follows a **hybrid ECS (Entity-Component-System)** pattern:
- **Systems (`/systems`)**: Pure logic, no UI. Handles physics, collision, AI.
  - *Example*: `EnemySystem.ts`, `CollisionManager.tsx` (Logic Loop).
  - *Rule*: Logic updates happen in `useFrame` inside a Manager/System, updating a Zustand store.
- **Components (`/game/cockpit`)**: Visuals only.
  - *Example*: `GameEnemy.tsx`, `PlayerShip.tsx`.
  - *Rule*: Components read from the store (or props) and update their `ref` visual. Do NOT put game logic (movement/collision) inside the visual component.

## 3. Performance Best Practices
- **No `useState` in Game Loop**: Avoid `useState` for values that change every frame (position, rotation). Use `useRef` or direct Store access.
- **Object Pooling**: For projectiles and particles, use pooling or fixed arrays to avoid Garbage Collection spikes.
- **Ref-Based Animation**: Animate `THREE.Mesh` via `ref.current.position` inside `useFrame`, never via React Props re-renders.

## 4. Visual Aesthetic
- **Dashboard**: "Holographic High-Tech". Glass panels (`bg-black/40`, `backdrop-blur`), thin borders, cyan/purple accents.
- **Game**: "Arcade Sim". Neon trails, wireframe enemies, immersive cockpit.
- **Feedback**: Every action (hit, kill, hover) must have visual (particle, glow) or audio feedback.

## 5. File Structure
- `src/components/game/systems/`: Logical systems (WaveManager, WeaponSystem).
- `src/components/game/cockpit/`: 3D visual components (Ship, Enemy, Scene).
- `src/context/`: Global app state.

## 6. Coding Workflow
- **Verify**: Always verify 3D changes by looking for "Visual Disconnects" (e.g., Hitbox vs Visual).
- **Consolidate**: If two things control one value (e.g., Player Position), move control to a Single Source of Truth (Store).

