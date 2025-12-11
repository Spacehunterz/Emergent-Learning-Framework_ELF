import { useState } from 'react'
import { useAPI } from '../hooks/useAPI'
import { Download, FileJson, FileText, Table, Github, MessageSquare, Check, Loader2 } from 'lucide-react'

interface ExportPanelProps {
  onClose: () => void
}

type ExportFormat = 'json' | 'csv' | 'markdown'
type ExportType = 'heuristics' | 'runs' | 'learnings' | 'full'

const exportFormats = [
  { id: 'json', label: 'JSON', icon: FileJson, description: 'Full data structure' },
  { id: 'csv', label: 'CSV', icon: Table, description: 'Spreadsheet compatible' },
  { id: 'markdown', label: 'Markdown', icon: FileText, description: 'Human readable' },
]

const exportTypes = [
  { id: 'heuristics', label: 'Heuristics', description: 'All rules and golden rules' },
  { id: 'runs', label: 'Agent Runs', description: 'Execution history' },
  { id: 'learnings', label: 'Learnings', description: 'Failures and observations' },
  { id: 'full', label: 'Full Export', description: 'Everything including metrics' },
]

const integrations = [
  { id: 'github', label: 'GitHub Issue', icon: Github, description: 'Create issue from learnings' },
  { id: 'slack', label: 'Slack', icon: MessageSquare, description: 'Send summary to channel' },
]

export default function ExportPanel({ onClose }: ExportPanelProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('json')
  const [selectedType, setSelectedType] = useState<ExportType>('heuristics')
  const [isExporting, setIsExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState(false)
  const api = useAPI()

  const handleExport = async () => {
    setIsExporting(true)
    setExportSuccess(false)

    try {
      const response = await api.get(`/api/export/${selectedType}?format=${selectedFormat}`)

      // Create download
      let content: string
      let mimeType: string
      let extension: string

      if (selectedFormat === 'json') {
        content = JSON.stringify(response, null, 2)
        mimeType = 'application/json'
        extension = 'json'
      } else if (selectedFormat === 'csv') {
        content = convertToCSV(response)
        mimeType = 'text/csv'
        extension = 'csv'
      } else {
        content = convertToMarkdown(response, selectedType)
        mimeType = 'text/markdown'
        extension = 'md'
      }

      const blob = new Blob([content], { type: mimeType })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `cosmic-dashboard-${selectedType}-${new Date().toISOString().split('T')[0]}.${extension}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      setExportSuccess(true)
      setTimeout(() => setExportSuccess(false), 3000)
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setIsExporting(false)
    }
  }

  const convertToCSV = (data: any): string => {
    if (!Array.isArray(data) || data.length === 0) {
      return ''
    }
    const headers = Object.keys(data[0])
    const rows = data.map(item =>
      headers.map(h => {
        const val = item[h]
        if (typeof val === 'string' && val.includes(',')) {
          return `"${val.replace(/"/g, '""')}"`
        }
        return val ?? ''
      }).join(',')
    )
    return [headers.join(','), ...rows].join('\n')
  }

  const convertToMarkdown = (data: any, type: string): string => {
    const lines: string[] = [
      `# Cosmic Dashboard Export: ${type}`,
      `Generated: ${new Date().toISOString()}`,
      '',
    ]

    if (Array.isArray(data)) {
      data.forEach((item, idx) => {
        if (type === 'heuristics') {
          lines.push(`## ${idx + 1}. ${item.rule}`)
          lines.push(`- **Domain:** ${item.domain}`)
          lines.push(`- **Confidence:** ${(item.confidence * 100).toFixed(0)}%`)
          lines.push(`- **Validated:** ${item.times_validated} times`)
          lines.push(`- **Golden:** ${item.is_golden ? 'Yes' : 'No'}`)
          if (item.explanation) lines.push(`- **Explanation:** ${item.explanation}`)
          lines.push('')
        } else {
          lines.push(`### ${JSON.stringify(item, null, 2)}`)
          lines.push('')
        }
      })
    }

    return lines.join('\n')
  }

  const handleIntegration = async (integration: string) => {
    // Placeholder for integration logic
    console.log(`Triggering integration: ${integration}`)
  }

  return (
    <div className="fixed inset-0 bg-black/50 modal-backdrop flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center space-x-2">
            <Download className="w-5 h-5 text-sky-400" />
            <h2 className="text-lg font-semibold text-white">Export & Integrations</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition"
          >
            &times;
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Export Type */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-3 block">What to Export</label>
            <div className="grid grid-cols-2 gap-2">
              {exportTypes.map(type => (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id as ExportType)}
                  className={`p-3 rounded-lg border text-left transition
                    ${selectedType === type.id
                      ? 'border-sky-500 bg-sky-500/10'
                      : 'border-slate-600 hover:border-slate-500'
                    }`}
                >
                  <div className="font-medium text-white">{type.label}</div>
                  <div className="text-xs text-slate-400">{type.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Export Format */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-3 block">Format</label>
            <div className="flex space-x-2">
              {exportFormats.map(format => {
                const Icon = format.icon
                return (
                  <button
                    key={format.id}
                    onClick={() => setSelectedFormat(format.id as ExportFormat)}
                    className={`flex-1 p-3 rounded-lg border text-center transition
                      ${selectedFormat === format.id
                        ? 'border-sky-500 bg-sky-500/10'
                        : 'border-slate-600 hover:border-slate-500'
                      }`}
                  >
                    <Icon className={`w-6 h-6 mx-auto mb-1 ${selectedFormat === format.id ? 'text-sky-400' : 'text-slate-400'}`} />
                    <div className="font-medium text-white">{format.label}</div>
                    <div className="text-xs text-slate-400">{format.description}</div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Export Button */}
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-sky-500 text-white rounded-lg font-medium hover:bg-sky-400 disabled:opacity-50 transition"
          >
            {isExporting ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : exportSuccess ? (
              <Check className="w-5 h-5" />
            ) : (
              <Download className="w-5 h-5" />
            )}
            <span>{isExporting ? 'Exporting...' : exportSuccess ? 'Downloaded!' : 'Download Export'}</span>
          </button>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-700"></div>
            </div>
            <div className="relative flex justify-center">
              <span className="bg-slate-800 px-3 text-sm text-slate-400">or send to</span>
            </div>
          </div>

          {/* Integrations */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-3 block">Integrations</label>
            <div className="flex space-x-2">
              {integrations.map(integration => {
                const Icon = integration.icon
                return (
                  <button
                    key={integration.id}
                    onClick={() => handleIntegration(integration.id)}
                    className="flex-1 flex items-center justify-center space-x-2 p-3 rounded-lg border border-slate-600 hover:border-slate-500 transition"
                  >
                    <Icon className="w-5 h-5 text-slate-400" />
                    <div>
                      <div className="font-medium text-white">{integration.label}</div>
                      <div className="text-xs text-slate-400">{integration.description}</div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
