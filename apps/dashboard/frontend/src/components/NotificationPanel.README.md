# Notification System

## Overview

The notification system provides toast-style alerts for important events in the Emergent Learning Dashboard. Notifications appear in the bottom-right corner of the screen and automatically dismiss after 5 seconds (configurable).

## Components

### NotificationPanel.tsx

Main component that renders all active notifications with:
- Toast-style layout in bottom-right corner
- Auto-dismiss after 5 seconds with progress bar
- Click-to-dismiss functionality
- Different colors for each notification type (info/success/warning/error)
- Glass-panel styling matching the dashboard theme
- Sound toggle and clear all controls

### useNotifications.ts

Custom hook for managing notification state:
- Add notifications with `info()`, `success()`, `warning()`, `error()`
- Remove individual notifications
- Clear all notifications
- Toggle notification sounds
- Sound preferences persist in localStorage

## Usage

### Basic Example

```tsx
import { useNotifications } from '../hooks/useNotifications'

function MyComponent() {
  const notifications = useNotifications()

  // Show different types of notifications
  notifications.info('Title', 'Message')
  notifications.success('Success', 'Operation completed')
  notifications.warning('Warning', 'Something to be aware of')
  notifications.error('Error', 'Something went wrong')
}
```

### Integration in App.tsx

```tsx
import { useNotifications } from './hooks/useNotifications'
import { NotificationPanel } from './components/NotificationPanel'

function App() {
  const notifications = useNotifications()

  // Trigger notifications from WebSocket events
  const handleMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'heuristics':
        notifications.info('New Heuristic', data.rule)
        break
      case 'heuristic_promoted':
        notifications.success('Promoted to Golden Rule', data.rule)
        break
      // ... etc
    }
  }, [notifications])

  return (
    <>
      <NotificationPanel
        notifications={notifications.notifications}
        onDismiss={notifications.removeNotification}
        onClearAll={notifications.clearAll}
        soundEnabled={notifications.soundEnabled}
        onToggleSound={notifications.toggleSound}
      />
      {/* ... rest of app */}
    </>
  )
}
```

## Notification Types

### Info (Blue)
- **Use for:** Informational messages, new heuristics, general updates
- **Icon:** Info circle
- **Color:** Blue accent
- **Auto-dismiss:** Yes (5s)

### Success (Green)
- **Use for:** Successful operations, completed workflows, promotions
- **Icon:** Check circle
- **Color:** Green accent
- **Auto-dismiss:** Yes (5s)

### Warning (Amber)
- **Use for:** Important notices, CEO inbox items, potential issues
- **Icon:** Alert triangle
- **Color:** Amber/orange accent
- **Auto-dismiss:** Yes (5s)

### Error (Red)
- **Use for:** Failed operations, errors, critical issues
- **Icon:** Alert circle
- **Color:** Red accent
- **Auto-dismiss:** No (requires manual dismiss)

## Features

### Auto-dismiss Progress Bar
- Visual progress bar at the bottom of each notification
- Shows time remaining before auto-dismiss
- Smooth animation using framer-motion

### Sound Notifications
- Simple beeps using Web Audio API
- Different tones for each notification type:
  - Info: Two-note rising (440Hz → 550Hz)
  - Success: Three-note ascending (523Hz → 659Hz → 784Hz)
  - Warning: Two-note pattern (392Hz → 523Hz)
  - Error: Two-note descending (330Hz → 262Hz)
- Mute/unmute toggle in notification panel
- Preference persists in localStorage

### Styling
- Matches dashboard theme with glass-panel effects
- Uses theme CSS variables for colors
- Responsive animations with framer-motion
- Hover states reveal close button
- Glow effects matching notification type

### Accessibility
- Click anywhere on notification to dismiss
- Clear all button when multiple notifications present
- Sound toggle with visual indicator (Volume2/VolumeX icons)
- Keyboard accessible (inherits from button elements)

## WebSocket Event Mapping

The system listens for these WebSocket events and triggers notifications:

| Event Type | Notification Type | Title | Auto-dismiss |
|------------|-------------------|-------|--------------|
| `heuristics` | Info | "New Heuristic Created" | Yes |
| `heuristic_promoted` | Success | "Heuristic Promoted to Golden Rule" | Yes |
| `runs` (completed) | Success | "Workflow Run Completed" | Yes |
| `runs` (failed) | Error | "Workflow Run Failed" | No |
| `ceo_inbox` | Warning | "New CEO Decision Required" | Yes |

## Customization

### Change Auto-dismiss Duration

```tsx
// In useNotifications.ts, modify the default duration:
const addNotification = useCallback(
  (title: string, message: string, options: NotificationOptions = {}) => {
    const { duration = 5000 } = options // Change this value
    // ...
  }
)
```

### Disable Auto-dismiss for Specific Notification

```tsx
notifications.info('Title', 'Message', false) // Won't auto-dismiss
```

### Custom Notification Sound

Modify the `playSound` function in `useNotifications.ts` to use custom frequencies or patterns.

## Dependencies

- `framer-motion`: Smooth animations for notification entry/exit
- `lucide-react`: Icons for notification types and controls
- Web Audio API: Built-in browser API for notification sounds

## File Structure

```
dashboard-app/frontend/src/
├── components/
│   ├── NotificationPanel.tsx        # Main notification component
│   └── NotificationPanel.README.md  # This file
└── hooks/
    └── useNotifications.ts           # Notification state management hook
```

## Future Enhancements

Potential improvements:
- [ ] Click notification to navigate to related view
- [ ] Notification history panel
- [ ] Custom sound uploads
- [ ] Notification grouping (e.g., "3 new heuristics")
- [ ] Desktop notifications API integration
- [ ] Notification filtering preferences
- [ ] Undo actions from notifications
