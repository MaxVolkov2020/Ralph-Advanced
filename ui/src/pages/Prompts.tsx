import React, { useEffect, useState } from 'react';
import apiClient from '../api/client';
import {
  FileText,
  Plus,
  Edit2,
  History,
  CheckCircle,
  Clock,
  Bot,
  ChevronDown,
  ChevronRight,
  Save
} from 'lucide-react';
import { AgentPrompt, AgentPromptCreate } from '../types';

const AGENT_TYPES = [
  { name: 'backend', label: 'Backend Agent', description: 'Handles backend/API development' },
  { name: 'mobile', label: 'Mobile Agent', description: 'Handles mobile app development' },
  { name: 'frontend', label: 'Frontend Agent', description: 'Handles web frontend development' },
  { name: 'qa', label: 'QA Agent', description: 'Quality assurance and testing' },
  { name: 'code_review', label: 'Code Review Agent', description: 'Reviews code for quality and best practices' },
  { name: 'security', label: 'Security Agent', description: 'Security analysis and vulnerability detection' },
];

export const Prompts: React.FC = () => {
  const [prompts, setPrompts] = useState<AgentPrompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [showHistory, setShowHistory] = useState<string | null>(null);
  const [historyPrompts, setHistoryPrompts] = useState<AgentPrompt[]>([]);

  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      const response = await apiClient.get('/prompts?active_only=true');
      setPrompts(response.data);
    } catch (error) {
      console.error('Failed to load prompts:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async (agentName: string) => {
    try {
      const response = await apiClient.get(`/prompts/${agentName}/history`);
      setHistoryPrompts(response.data);
      setShowHistory(agentName);
    } catch (error) {
      console.error('Failed to load prompt history:', error);
    }
  };

  const handleActivateVersion = async (agentName: string, version: number) => {
    try {
      await apiClient.put(`/prompts/${agentName}/activate/${version}`);
      loadPrompts();
      loadHistory(agentName);
    } catch (error) {
      console.error('Failed to activate version:', error);
    }
  };

  const getActivePrompt = (agentName: string): AgentPrompt | undefined => {
    return prompts.find((p) => p.agent_name === agentName && p.is_active);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading prompts...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Agent Prompts</h1>
          <p className="text-gray-600 mt-1">
            Configure and manage AI agent prompts
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {AGENT_TYPES.map((agent) => {
          const activePrompt = getActivePrompt(agent.name);
          const isExpanded = showHistory === agent.name;

          return (
            <div key={agent.name} className="bg-white rounded-lg shadow">
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <Bot className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {agent.label}
                      </h3>
                      <p className="text-sm text-gray-500">{agent.description}</p>
                    </div>
                  </div>
                  {activePrompt && (
                    <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
                      v{activePrompt.version}
                    </span>
                  )}
                </div>

                {activePrompt ? (
                  <div className="mt-4">
                    <div className="bg-gray-50 rounded-lg p-3 max-h-32 overflow-hidden">
                      <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono">
                        {activePrompt.content.substring(0, 300)}
                        {activePrompt.content.length > 300 && '...'}
                      </pre>
                    </div>
                    <div className="flex items-center gap-2 mt-3 text-sm text-gray-500">
                      <Clock className="w-4 h-4" />
                      <span>
                        Updated:{' '}
                        {new Date(activePrompt.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 bg-yellow-50 rounded-lg p-3 text-sm text-yellow-700">
                    No prompt configured. Using default filesystem prompt.
                  </div>
                )}

                <div className="flex gap-2 mt-4">
                  <button
                    onClick={() => {
                      setSelectedAgent(agent.name);
                      setShowEditor(true);
                    }}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    {activePrompt ? (
                      <>
                        <Edit2 className="w-4 h-4" />
                        Edit
                      </>
                    ) : (
                      <>
                        <Plus className="w-4 h-4" />
                        Create
                      </>
                    )}
                  </button>
                  <button
                    onClick={() =>
                      isExpanded
                        ? setShowHistory(null)
                        : loadHistory(agent.name)
                    }
                    className="flex items-center justify-center gap-2 px-3 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    <History className="w-4 h-4" />
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {isExpanded && historyPrompts.length > 0 && (
                <div className="border-t border-gray-200 p-4 bg-gray-50">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">
                    Version History
                  </h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {historyPrompts.map((prompt) => (
                      <div
                        key={prompt.id}
                        className={`flex items-center justify-between p-2 rounded ${
                          prompt.is_active ? 'bg-green-100' : 'bg-white'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {prompt.is_active && (
                            <CheckCircle className="w-4 h-4 text-green-600" />
                          )}
                          <span className="text-sm font-medium">
                            v{prompt.version}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(prompt.created_at).toLocaleDateString()}
                          </span>
                          {prompt.notes && (
                            <span className="text-xs text-gray-400 truncate max-w-[150px]">
                              - {prompt.notes}
                            </span>
                          )}
                        </div>
                        {!prompt.is_active && (
                          <button
                            onClick={() =>
                              handleActivateVersion(agent.name, prompt.version)
                            }
                            className="text-xs text-primary hover:underline"
                          >
                            Activate
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {showEditor && selectedAgent && (
        <PromptEditor
          agentName={selectedAgent}
          existingPrompt={getActivePrompt(selectedAgent)}
          onClose={() => {
            setShowEditor(false);
            setSelectedAgent(null);
          }}
          onSuccess={() => {
            setShowEditor(false);
            setSelectedAgent(null);
            loadPrompts();
          }}
        />
      )}
    </div>
  );
};

interface PromptEditorProps {
  agentName: string;
  existingPrompt?: AgentPrompt;
  onClose: () => void;
  onSuccess: () => void;
}

const PromptEditor: React.FC<PromptEditorProps> = ({
  agentName,
  existingPrompt,
  onClose,
  onSuccess,
}) => {
  const agentInfo = AGENT_TYPES.find((a) => a.name === agentName);
  const [formData, setFormData] = useState<AgentPromptCreate>({
    agent_name: agentName,
    content: existingPrompt?.content || getDefaultPromptTemplate(agentName),
    notes: '',
    is_active: true,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await apiClient.post('/prompts', formData);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save prompt');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl my-8 mx-4">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">
            {existingPrompt ? 'Edit' : 'Create'} Prompt - {agentInfo?.label}
          </h2>
          <p className="text-gray-600 mt-1">
            {existingPrompt
              ? `Creating new version (current: v${existingPrompt.version})`
              : 'Create the first prompt version for this agent'}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-4">
            <div className="flex gap-2 mb-4">
              <button
                type="button"
                onClick={() => setShowPreview(false)}
                className={`px-4 py-2 rounded-md ${
                  !showPreview
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                <Edit2 className="w-4 h-4 inline mr-2" />
                Edit
              </button>
              <button
                type="button"
                onClick={() => setShowPreview(true)}
                className={`px-4 py-2 rounded-md ${
                  showPreview
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                <FileText className="w-4 h-4 inline mr-2" />
                Preview
              </button>
            </div>

            {showPreview ? (
              <div className="bg-gray-50 rounded-lg p-4 min-h-[400px] max-h-[500px] overflow-y-auto">
                <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono">
                  {formData.content}
                </pre>
              </div>
            ) : (
              <textarea
                value={formData.content}
                onChange={(e) =>
                  setFormData({ ...formData, content: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-mono text-sm"
                rows={20}
                placeholder="Enter prompt content in markdown format..."
                required
              />
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Change Notes (optional)
              </label>
              <input
                type="text"
                value={formData.notes}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
                placeholder="e.g., Added better error handling instructions"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {error && (
              <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
                {error}
              </div>
            )}
          </div>

          <div className="p-6 border-t border-gray-200 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {loading ? 'Saving...' : 'Save & Activate'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

function getDefaultPromptTemplate(agentName: string): string {
  const templates: Record<string, string> = {
    backend: `# Backend Agent Prompt

You are a backend development agent specialized in building robust APIs and server-side logic.

## Story Information
- **ID**: {{story.id}}
- **Title**: {{story.title}}
- **Description**: {{story.description}}

## Acceptance Criteria
{{#each story.acceptanceCriteria}}
- {{this}}
{{/each}}

## Instructions
1. Analyze the requirements carefully
2. Implement clean, maintainable code
3. Follow the existing code patterns
4. Write appropriate tests
5. Handle errors gracefully

## Response Format
Respond with a JSON object containing:
- files: Array of file changes
- summary: Brief description of what was done
- reason: Why this approach was chosen
- learnings: Any insights for future work`,

    mobile: `# Mobile Agent Prompt

You are a mobile development agent specialized in building cross-platform mobile applications.

## Story Information
- **ID**: {{story.id}}
- **Title**: {{story.title}}
- **Description**: {{story.description}}

## Acceptance Criteria
{{#each story.acceptanceCriteria}}
- {{this}}
{{/each}}

## Instructions
1. Follow platform design guidelines
2. Ensure responsive layouts
3. Handle offline scenarios
4. Optimize performance
5. Maintain accessibility

## Response Format
Respond with a JSON object containing:
- files: Array of file changes
- summary: Brief description of what was done
- reason: Why this approach was chosen
- learnings: Any insights for future work`,

    qa: `# QA Agent Prompt

You are a quality assurance agent responsible for validating implementations.

## Story Information
- **ID**: {{story.id}}
- **Title**: {{story.title}}
- **Description**: {{story.description}}

## Acceptance Criteria
{{#each story.acceptanceCriteria}}
- {{this}}
{{/each}}

## File Changes to Review
{{#each story.file_changes}}
- {{this.path}} ({{this.action}})
{{/each}}

## Instructions
1. Verify all acceptance criteria are met
2. Check for edge cases
3. Validate error handling
4. Ensure code quality standards

## Response Format
Respond with a JSON object containing:
- status: "pass" or "fail"
- issues: Array of issues found (if any)
- suggestions: Improvement recommendations`,
  };

  return templates[agentName] || templates.backend;
}
