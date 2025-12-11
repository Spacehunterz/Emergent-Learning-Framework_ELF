/**
 * Notification System Usage Examples
 *
 * This file demonstrates various ways to use the notification system
 * in the Emergent Learning Dashboard.
 */

import { useNotifications } from '../hooks/useNotifications'
import { NotificationPanel } from './NotificationPanel'

// ============================================================================
// EXAMPLE 1: Basic Usage
// ============================================================================

export function BasicNotificationExample() {
  const notifications = useNotifications()

  const handleClick = () => {
    // Simple info notification
    notifications.info('Hello', 'This is an info notification')
  }

  return <button onClick={handleClick}>Show Info</button>
}

// ============================================================================
// EXAMPLE 2: All Notification Types
// ============================================================================

export function AllTypesExample() {
  const notifications = useNotifications()

  return (
    <div className="space-x-2">
      <button onClick={() => notifications.info('Info', 'This is informational')}>
        Info
      </button>
      <button onClick={() => notifications.success('Success', 'Operation completed')}>
        Success
      </button>
      <button onClick={() => notifications.warning('Warning', 'Please review')}>
        Warning
      </button>
      <button onClick={() => notifications.error('Error', 'Something went wrong')}>
        Error
      </button>
    </div>
  )
}

// ============================================================================
// EXAMPLE 3: WebSocket Integration
// ============================================================================

export function WebSocketExample() {
  const notifications = useNotifications()

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'heuristics':
        notifications.info(
          'New Heuristic Created',
          data.rule || 'A new heuristic has been added to the system'
        )
        break

      case 'heuristic_promoted':
        notifications.success(
          'Heuristic Promoted to Golden Rule',
          data.rule || 'A heuristic has been promoted'
        )
        break

      case 'runs':
        if (data.status === 'completed') {
          notifications.success(
            'Workflow Run Completed',
            `${data.workflow_name || 'Workflow'} finished successfully`
          )
        } else if (data.status === 'failed') {
          notifications.error(
            'Workflow Run Failed',
            `${data.workflow_name || 'Workflow'} encountered an error`
          )
        }
        break

      case 'ceo_inbox':
        notifications.warning(
          'New CEO Decision Required',
          data.message || 'A new item requires your attention'
        )
        break
    }
  }

  return (
    <div>
      <p>WebSocket handler example</p>
      <button onClick={() => handleWebSocketMessage({ type: 'heuristics', rule: 'Test rule' })}>
        Test Handler
      </button>
    </div>
  )
}

// ============================================================================
// EXAMPLE 4: Custom Auto-dismiss Control
// ============================================================================

export function CustomAutoDismissExample() {
  const notifications = useNotifications()

  const showPersistentNotification = () => {
    // This notification won't auto-dismiss
    notifications.info('Important', 'Please read this carefully', false)
  }

  const showQuickNotification = () => {
    // This will auto-dismiss (default behavior)
    notifications.info('Quick Update', 'This will disappear in 5 seconds', true)
  }

  return (
    <div className="space-x-2">
      <button onClick={showPersistentNotification}>
        Show Persistent
      </button>
      <button onClick={showQuickNotification}>
        Show Quick
      </button>
    </div>
  )
}

// ============================================================================
// EXAMPLE 5: Sound Control
// ============================================================================

export function SoundControlExample() {
  const notifications = useNotifications()

  return (
    <div className="space-y-2">
      <div>
        Sound is currently: {notifications.soundEnabled ? 'ON' : 'OFF'}
      </div>
      <button onClick={notifications.toggleSound}>
        Toggle Sound
      </button>
      <button onClick={() => notifications.info('Test', 'Listen for the sound')}>
        Test Notification
      </button>
    </div>
  )
}

// ============================================================================
// EXAMPLE 6: Clear All Notifications
// ============================================================================

export function ClearAllExample() {
  const notifications = useNotifications()

  const showMultiple = () => {
    notifications.info('First', 'Notification 1')
    notifications.success('Second', 'Notification 2')
    notifications.warning('Third', 'Notification 3')
  }

  return (
    <div className="space-x-2">
      <button onClick={showMultiple}>
        Show Multiple
      </button>
      <button onClick={notifications.clearAll}>
        Clear All
      </button>
    </div>
  )
}

// ============================================================================
// EXAMPLE 7: Error Handling with Notifications
// ============================================================================

export function ErrorHandlingExample() {
  const notifications = useNotifications()

  const handleApiCall = async () => {
    try {
      notifications.info('Processing', 'Starting API call...')

      const response = await fetch('/api/some-endpoint')

      if (!response.ok) {
        throw new Error('API call failed')
      }

      const data = await response.json()

      notifications.success(
        'Success',
        'Data loaded successfully'
      )

      return data
    } catch (error) {
      notifications.error(
        'API Error',
        error instanceof Error ? error.message : 'Unknown error occurred'
      )
    }
  }

  return <button onClick={handleApiCall}>Make API Call</button>
}

// ============================================================================
// EXAMPLE 8: Progressive Workflow Updates
// ============================================================================

export function ProgressiveUpdatesExample() {
  const notifications = useNotifications()

  const runWorkflow = async () => {
    // Start
    notifications.info('Workflow Started', 'Beginning data processing')

    await new Promise(resolve => setTimeout(resolve, 2000))

    // Progress update
    notifications.info('Processing', 'Step 1 of 3 complete')

    await new Promise(resolve => setTimeout(resolve, 2000))

    // Another update
    notifications.info('Processing', 'Step 2 of 3 complete')

    await new Promise(resolve => setTimeout(resolve, 2000))

    // Complete
    notifications.success('Workflow Complete', 'All steps finished successfully')
  }

  return <button onClick={runWorkflow}>Run Workflow</button>
}

// ============================================================================
// EXAMPLE 9: Context-Aware Notifications
// ============================================================================

export function ContextAwareExample() {
  const notifications = useNotifications()

  const handleAction = (context: string, success: boolean) => {
    if (success) {
      notifications.success(
        `${context} Successful`,
        `The ${context.toLowerCase()} operation completed`
      )
    } else {
      notifications.error(
        `${context} Failed`,
        `The ${context.toLowerCase()} operation encountered an error`
      )
    }
  }

  return (
    <div className="space-x-2">
      <button onClick={() => handleAction('Save', true)}>
        Save (Success)
      </button>
      <button onClick={() => handleAction('Delete', false)}>
        Delete (Error)
      </button>
      <button onClick={() => handleAction('Update', true)}>
        Update (Success)
      </button>
    </div>
  )
}

// ============================================================================
// EXAMPLE 10: Notification with Dynamic Data
// ============================================================================

export function DynamicDataExample() {
  const notifications = useNotifications()

  const handleHeuristicUpdate = (heuristic: {
    id: number
    rule: string
    confidence: number
    is_golden: boolean
  }) => {
    if (heuristic.is_golden) {
      notifications.success(
        'Golden Rule Active',
        `"${heuristic.rule}" is now a golden rule with ${(heuristic.confidence * 100).toFixed(0)}% confidence`
      )
    } else if (heuristic.confidence > 0.8) {
      notifications.warning(
        'High Confidence Heuristic',
        `"${heuristic.rule}" has ${(heuristic.confidence * 100).toFixed(0)}% confidence. Consider promoting to golden rule.`
      )
    } else {
      notifications.info(
        'Heuristic Updated',
        `"${heuristic.rule}" confidence: ${(heuristic.confidence * 100).toFixed(0)}%`
      )
    }
  }

  return (
    <div className="space-y-2">
      <button onClick={() => handleHeuristicUpdate({
        id: 1,
        rule: 'Always validate inputs',
        confidence: 0.95,
        is_golden: true
      })}>
        Golden Rule Example
      </button>
      <button onClick={() => handleHeuristicUpdate({
        id: 2,
        rule: 'Check permissions first',
        confidence: 0.85,
        is_golden: false
      })}>
        High Confidence Example
      </button>
    </div>
  )
}

// ============================================================================
// EXAMPLE 11: Integration with Command Palette
// ============================================================================

export function CommandPaletteIntegrationExample() {
  const notifications = useNotifications()

  // These commands would be added to the command palette
  const notificationCommands = [
    {
      id: 'toggleNotificationSound',
      label: notifications.soundEnabled ? 'Mute Notifications' : 'Unmute Notifications',
      category: 'Settings',
      action: notifications.toggleSound
    },
    {
      id: 'clearNotifications',
      label: 'Clear All Notifications',
      category: 'Actions',
      action: notifications.clearAll
    },
    {
      id: 'testNotification',
      label: 'Test Notification',
      category: 'Debug',
      action: () => notifications.info('Test', 'This is a test notification')
    }
  ]

  return <div>Command palette commands: {notificationCommands.length}</div>
}

// ============================================================================
// EXAMPLE 12: Complete App Integration
// ============================================================================

export function CompleteAppExample() {
  const notifications = useNotifications()

  // This is how it's used in App.tsx
  return (
    <>
      {/* 1. Use the hook */}
      {/* const notifications = useNotifications() */}

      {/* 2. Integrate with WebSocket handler */}
      {/* handleMessage callback uses notifications */}

      {/* 3. Render the panel */}
      <NotificationPanel
        notifications={notifications.notifications}
        onDismiss={notifications.removeNotification}
        onClearAll={notifications.clearAll}
        soundEnabled={notifications.soundEnabled}
        onToggleSound={notifications.toggleSound}
      />

      <div className="p-4">
        <h2>Complete Integration Example</h2>
        <p>See App.tsx for the full implementation</p>
      </div>
    </>
  )
}
