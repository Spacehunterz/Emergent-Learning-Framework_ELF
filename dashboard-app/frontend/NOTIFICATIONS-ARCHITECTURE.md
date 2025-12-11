# Notification System Architecture

## Component Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         App.tsx                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  const notifications = useNotifications()                  │  │
│  │                                                             │  │
│  │  WebSocket Handler:                                        │  │
│  │    ├─ heuristics → notifications.info()                   │  │
│  │    ├─ heuristic_promoted → notifications.success()        │  │
│  │    ├─ runs (completed) → notifications.success()          │  │
│  │    ├─ runs (failed) → notifications.error()               │  │
│  │    └─ ceo_inbox → notifications.warning()                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  <NotificationPanel                                        │  │
│  │    notifications={notifications.notifications}            │  │
│  │    onDismiss={notifications.removeNotification}           │  │
│  │    onClearAll={notifications.clearAll}                    │  │
│  │    soundEnabled={notifications.soundEnabled}              │  │
│  │    onToggleSound={notifications.toggleSound}              │  │
│  │  />                                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Hook Architecture (useNotifications.ts)

```
┌────────────────────────────────────────────────────────────────┐
│                    useNotifications Hook                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  State:                                                         │
│  ├─ notifications: Notification[]                              │
│  └─ soundEnabled: boolean (localStorage)                       │
│                                                                 │
│  Methods:                                                       │
│  ├─ addNotification(title, message, options)                   │
│  │   ├─ Creates unique ID                                      │
│  │   ├─ Plays sound (if enabled)                               │
│  │   └─ Sets auto-dismiss timer                                │
│  │                                                              │
│  ├─ removeNotification(id)                                     │
│  ├─ clearAll()                                                 │
│  ├─ toggleSound()                                              │
│  │                                                              │
│  └─ Convenience methods:                                       │
│      ├─ info(title, message, autoDismiss=true)                 │
│      ├─ success(title, message, autoDismiss=true)              │
│      ├─ warning(title, message, autoDismiss=true)              │
│      └─ error(title, message, autoDismiss=false)               │
│                                                                 │
│  Sound System (Web Audio API):                                 │
│  └─ playSound(type)                                            │
│      ├─ Info: 440Hz → 550Hz (rising)                           │
│      ├─ Success: 523Hz → 659Hz → 784Hz (ascending)             │
│      ├─ Warning: 392Hz → 523Hz (pattern)                       │
│      └─ Error: 330Hz → 262Hz (descending)                      │
└────────────────────────────────────────────────────────────────┘
```

## Component Architecture (NotificationPanel.tsx)

```
┌────────────────────────────────────────────────────────────────┐
│                    NotificationPanel                            │
│                  (Fixed bottom-right)                           │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────┐          │
│  │  Control Bar (when notifications exist)          │          │
│  │  ├─ [Volume Icon] Mute/Unmute                    │          │
│  │  └─ [Clear all (N)] (if N > 1)                   │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐          │
│  │  NotificationItem (stacked, newest at bottom)    │          │
│  │  ┌────────────────────────────────────────────┐  │          │
│  │  │ [Icon] Title              [X] │  12:34 PM │  │          │
│  │  │ Message text goes here...                 │  │          │
│  │  │ ▓▓▓▓▓▓▓░░░░░░  ← Progress bar             │  │          │
│  │  └────────────────────────────────────────────┘  │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                 │
│  Features:                                                      │
│  ├─ Glass-panel background (theme-aware)                       │
│  ├─ Framer Motion animations (slide in/out)                    │
│  ├─ Auto-dismiss progress bar (5s default)                     │
│  ├─ Click anywhere to dismiss                                  │
│  ├─ Close button (visible on hover)                            │
│  └─ Type-specific colors & icons                               │
└────────────────────────────────────────────────────────────────┘
```

## Notification Types Configuration

```
┌─────────────┬──────────────┬─────────────┬──────────────┬──────────────┐
│    Type     │     Icon     │    Color    │   Glow       │ Auto-Dismiss │
├─────────────┼──────────────┼─────────────┼──────────────┼──────────────┤
│ INFO        │ Info         │ Blue        │ Blue 30%     │ Yes (5s)     │
│ SUCCESS     │ CheckCircle  │ Green       │ Green 30%    │ Yes (5s)     │
│ WARNING     │ AlertTriangle│ Amber       │ Amber 30%    │ Yes (5s)     │
│ ERROR       │ AlertCircle  │ Red         │ Red 30%      │ No           │
└─────────────┴──────────────┴─────────────┴──────────────┴──────────────┘
```

## Data Flow

```
WebSocket Event
      │
      ▼
handleMessage() in App.tsx
      │
      ├─ Parse event type
      │
      ▼
notifications.{type}(title, message)
      │
      ├─ addNotification()
      │   ├─ Create notification object
      │   ├─ Add to state array
      │   ├─ Play sound (if enabled)
      │   └─ Start auto-dismiss timer
      │
      ▼
NotificationPanel receives updated array
      │
      ├─ Render NotificationItem for each
      │   ├─ Animate in (framer-motion)
      │   ├─ Show progress bar (if auto-dismiss)
      │   └─ Listen for dismiss events
      │
      ▼
Auto-dismiss timer expires OR user clicks
      │
      ▼
removeNotification(id)
      │
      ├─ Filter out from state array
      │
      ▼
NotificationPanel re-renders
      │
      └─ Animate out (framer-motion)
```

## Integration Points

### 1. WebSocket Events → Notifications

```typescript
// In App.tsx handleMessage callback
case 'heuristics':
  notifications.info('New Heuristic', data.rule)
  break
```

### 2. Command Palette Integration

```typescript
// Added to commands array in App.tsx
{
  id: 'toggleNotificationSound',
  label: notifications.soundEnabled ? 'Mute' : 'Unmute',
  category: 'Settings',
  action: notifications.toggleSound
}
```

### 3. LocalStorage Persistence

```typescript
// useNotifications.ts
const [soundEnabled, setSoundEnabled] = useState(() => {
  const stored = localStorage.getItem('notifications-sound-enabled')
  return stored !== 'false' // Default to true
})
```

## File Structure

```
dashboard-app/frontend/src/
│
├── hooks/
│   └── useNotifications.ts (157 lines)
│       ├── Notification interface
│       ├── NotificationOptions interface
│       └── useNotifications hook
│           ├── State management
│           ├── Sound system
│           └── CRUD methods
│
├── components/
│   ├── NotificationPanel.tsx (176 lines)
│   │   ├── NotificationPanel component
│   │   ├── NotificationItem component
│   │   └── notificationConfig
│   │
│   └── NotificationPanel.README.md (208 lines)
│       └── Complete documentation
│
└── App.tsx (modified)
    ├── Import useNotifications
    ├── Import NotificationPanel
    ├── Initialize notifications hook
    ├── Enhanced WebSocket handler
    ├── Render NotificationPanel
    └── Add command palette commands
```

## Theme Integration

```css
/* Notification colors use theme CSS variables */

Info (Blue):
  bg: bg-blue-500/10
  border: border-blue-500/30
  glow: shadow-[0_0_20px_rgba(59,130,246,0.3)]

Success (Green):
  bg: bg-green-500/10
  border: border-green-500/30
  glow: shadow-[0_0_20px_rgba(34,197,94,0.3)]

Warning (Amber):
  bg: bg-amber-500/10
  border: border-amber-500/30
  glow: shadow-[0_0_20px_rgba(245,158,11,0.3)]

Error (Red):
  bg: bg-red-500/10
  border: border-red-500/30
  glow: shadow-[0_0_20px_rgba(239,68,68,0.3)]

/* Glass panel effect */
backdrop-blur-sm + bg-slate-800/90
```

## Animation Timeline

```
Notification appears:
├─ opacity: 0 → 1 (300ms)
├─ y: 20px → 0 (300ms)
└─ scale: 0.95 → 1 (300ms)

While visible:
├─ Progress bar: 100% → 0% (5000ms linear)
└─ Hover: opacity of close button 0 → 1

Notification dismissed:
├─ opacity: 1 → 0 (300ms)
├─ x: 0 → 100px (300ms)
└─ scale: 1 → 0.95 (300ms)
```

## Performance Considerations

1. **Auto-dismiss timers**: Cleaned up on unmount
2. **Web Audio API**: Short-lived oscillators (200ms)
3. **LocalStorage**: Minimal writes (only on toggle)
4. **Framer Motion**: GPU-accelerated transforms
5. **State updates**: Filtered arrays (O(n) removal)

## Browser Compatibility

- **Web Audio API**: All modern browsers (Chrome 35+, Firefox 25+, Safari 9+)
- **LocalStorage**: Universal support
- **CSS backdrop-filter**: All modern browsers (with prefixes)
- **Framer Motion**: React 16.8+

## Testing Scenarios

1. **Single notification**: Appears, auto-dismisses after 5s
2. **Multiple notifications**: Stack correctly, independent timers
3. **Sound toggle**: Mutes all future notifications
4. **Manual dismiss**: Click notification or X button
5. **Clear all**: Removes all at once
6. **Error notifications**: Don't auto-dismiss
7. **Theme changes**: Colors update dynamically
8. **WebSocket events**: Trigger appropriate notification types
