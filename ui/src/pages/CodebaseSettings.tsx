import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import {
  GitBranch,
  Plus,
  Trash2,
  Edit2,
  CheckCircle,
  XCircle,
  RefreshCw,
  ArrowLeft,
  Server,
  Smartphone,
  Globe,
  Database,
  Package
} from 'lucide-react';
import { Codebase, CodebaseCreate, ConnectionTestResult } from '../types';

const CODEBASE_TYPES = [
  { value: 'backend', label: 'Backend', icon: Server },
  { value: 'frontend', label: 'Frontend', icon: Globe },
  { value: 'mobile', label: 'Mobile', icon: Smartphone },
  { value: 'infrastructure', label: 'Infrastructure', icon: Database },
  { value: 'library', label: 'Library', icon: Package },
];

const COMMON_FRAMEWORKS: Record<string, string[]> = {
  backend: ['Laravel', 'Django', 'Express', 'FastAPI', 'Spring Boot', 'Rails', 'NestJS', 'Go', 'Other'],
  frontend: ['React', 'Vue', 'Angular', 'Next.js', 'Nuxt', 'Svelte', 'Other'],
  mobile: ['React Native', 'Flutter', 'Swift/iOS', 'Kotlin/Android', 'Ionic', 'Other'],
  infrastructure: ['Terraform', 'Kubernetes', 'Docker', 'Ansible', 'CloudFormation', 'Other'],
  library: ['npm', 'pip', 'composer', 'cargo', 'Other'],
};

const COMMON_LANGUAGES: Record<string, string[]> = {
  backend: ['PHP', 'Python', 'JavaScript', 'TypeScript', 'Go', 'Java', 'Ruby', 'C#', 'Rust'],
  frontend: ['TypeScript', 'JavaScript'],
  mobile: ['TypeScript', 'Dart', 'Swift', 'Kotlin', 'Java'],
  infrastructure: ['HCL', 'YAML', 'JSON'],
  library: ['TypeScript', 'Python', 'PHP', 'Rust', 'Go'],
};

export const CodebaseSettings: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [codebases, setCodebases] = useState<Codebase[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCodebase, setEditingCodebase] = useState<Codebase | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResults, setTestResults] = useState<Record<number, ConnectionTestResult>>({});

  useEffect(() => {
    if (projectId) {
      loadCodebases();
    }
  }, [projectId]);

  const loadCodebases = async () => {
    try {
      const response = await apiClient.get(`/projects/${projectId}/codebases`);
      setCodebases(response.data);
    } catch (error) {
      console.error('Failed to load codebases:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (codebaseId: number) => {
    setTestingId(codebaseId);
    try {
      const response = await apiClient.post(`/codebases/${codebaseId}/test-connection`);
      setTestResults((prev) => ({ ...prev, [codebaseId]: response.data }));
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [codebaseId]: { success: false, message: 'Connection test failed' },
      }));
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (codebaseId: number) => {
    if (!confirm('Are you sure you want to delete this codebase?')) return;

    try {
      await apiClient.delete(`/codebases/${codebaseId}`);
      loadCodebases();
    } catch (error) {
      console.error('Failed to delete codebase:', error);
    }
  };

  const getTypeIcon = (type: string) => {
    const typeConfig = CODEBASE_TYPES.find((t) => t.value === type);
    return typeConfig?.icon || Server;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading codebases...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(`/projects/${projectId}`)}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-gray-900">Codebase Settings</h1>
          <p className="text-gray-600 mt-1">
            Configure repositories and their git credentials
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md hover:bg-blue-600"
        >
          <Plus className="w-5 h-5" />
          Add Codebase
        </button>
      </div>

      {codebases.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <GitBranch className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No codebases configured
          </h3>
          <p className="text-gray-600 mb-4">
            Add your first codebase to start managing repositories
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-primary text-white px-6 py-2 rounded-md hover:bg-blue-600"
          >
            Add Codebase
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {codebases.map((codebase) => {
            const Icon = getTypeIcon(codebase.codebase_type);
            const testResult = testResults[codebase.id];

            return (
              <div
                key={codebase.id}
                className="bg-white rounded-lg shadow p-6"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-primary/10 rounded-lg">
                      <Icon className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {codebase.name}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs px-2 py-1 bg-gray-100 rounded-full text-gray-600">
                          {codebase.codebase_type}
                        </span>
                        {codebase.framework && (
                          <span className="text-xs px-2 py-1 bg-blue-100 rounded-full text-blue-600">
                            {codebase.framework}
                          </span>
                        )}
                        {codebase.language && (
                          <span className="text-xs px-2 py-1 bg-green-100 rounded-full text-green-600">
                            {codebase.language}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTestConnection(codebase.id)}
                      disabled={testingId === codebase.id}
                      className="p-2 hover:bg-gray-100 rounded-lg text-gray-600"
                      title="Test Connection"
                    >
                      <RefreshCw
                        className={`w-5 h-5 ${
                          testingId === codebase.id ? 'animate-spin' : ''
                        }`}
                      />
                    </button>
                    <button
                      onClick={() => setEditingCodebase(codebase)}
                      className="p-2 hover:bg-gray-100 rounded-lg text-gray-600"
                      title="Edit"
                    >
                      <Edit2 className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(codebase.id)}
                      className="p-2 hover:bg-red-100 rounded-lg text-red-600"
                      title="Delete"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Repository:</span>
                    <span className="ml-2 text-gray-900 font-mono text-xs">
                      {codebase.repo_url}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Branch:</span>
                    <span className="ml-2 text-gray-900">
                      {codebase.default_branch}
                    </span>
                  </div>
                  {codebase.agent_name && (
                    <div>
                      <span className="text-gray-500">Agent:</span>
                      <span className="ml-2 text-gray-900">
                        {codebase.agent_name}
                      </span>
                    </div>
                  )}
                  {codebase.git_username && (
                    <div>
                      <span className="text-gray-500">Git User:</span>
                      <span className="ml-2 text-gray-900">
                        {codebase.git_username}
                      </span>
                    </div>
                  )}
                </div>

                {testResult && (
                  <div
                    className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
                      testResult.success
                        ? 'bg-green-50 text-green-700'
                        : 'bg-red-50 text-red-700'
                    }`}
                  >
                    {testResult.success ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : (
                      <XCircle className="w-5 h-5" />
                    )}
                    <span>{testResult.message}</span>
                    {testResult.branch_count && (
                      <span className="ml-2 text-sm">
                        ({testResult.branch_count} branches)
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showCreateModal && (
        <CodebaseModal
          projectId={Number(projectId)}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadCodebases();
          }}
        />
      )}

      {editingCodebase && (
        <CodebaseModal
          projectId={Number(projectId)}
          codebase={editingCodebase}
          onClose={() => setEditingCodebase(null)}
          onSuccess={() => {
            setEditingCodebase(null);
            loadCodebases();
          }}
        />
      )}
    </div>
  );
};

interface CodebaseModalProps {
  projectId: number;
  codebase?: Codebase;
  onClose: () => void;
  onSuccess: () => void;
}

const CodebaseModal: React.FC<CodebaseModalProps> = ({
  projectId,
  codebase,
  onClose,
  onSuccess,
}) => {
  const isEdit = !!codebase;
  const [formData, setFormData] = useState<CodebaseCreate>({
    name: codebase?.name || '',
    codebase_type: codebase?.codebase_type || 'backend',
    framework: codebase?.framework || '',
    language: codebase?.language || '',
    repo_url: codebase?.repo_url || '',
    git_access_token: '',
    git_username: codebase?.git_username || '',
    default_branch: codebase?.default_branch || 'main',
    agent_name: codebase?.agent_name || '',
    build_command: codebase?.build_command || '',
    test_command: codebase?.test_command || '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const frameworks = COMMON_FRAMEWORKS[formData.codebase_type] || [];
  const languages = COMMON_LANGUAGES[formData.codebase_type] || [];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isEdit) {
        await apiClient.put(`/codebases/${codebase.id}`, formData);
      } else {
        await apiClient.post(`/projects/${projectId}/codebases`, formData);
      }
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save codebase');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl my-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {isEdit ? 'Edit Codebase' : 'Add New Codebase'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="e.g., backend, mobile-ios"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Type *
              </label>
              <select
                value={formData.codebase_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    codebase_type: e.target.value,
                    framework: '',
                    language: '',
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {CODEBASE_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Framework
              </label>
              <select
                value={formData.framework}
                onChange={(e) =>
                  setFormData({ ...formData, framework: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select Framework</option>
                {frameworks.map((fw) => (
                  <option key={fw} value={fw}>
                    {fw}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Language
              </label>
              <select
                value={formData.language}
                onChange={(e) =>
                  setFormData({ ...formData, language: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select Language</option>
                {languages.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Repository URL *
            </label>
            <input
              type="url"
              value={formData.repo_url}
              onChange={(e) =>
                setFormData({ ...formData, repo_url: e.target.value })
              }
              placeholder="https://github.com/org/repo.git"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Git Username
              </label>
              <input
                type="text"
                value={formData.git_username}
                onChange={(e) =>
                  setFormData({ ...formData, git_username: e.target.value })
                }
                placeholder="oauth2 or username"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Personal Access Token
              </label>
              <input
                type="password"
                value={formData.git_access_token}
                onChange={(e) =>
                  setFormData({ ...formData, git_access_token: e.target.value })
                }
                placeholder={isEdit ? '(unchanged)' : 'ghp_xxx or glpat-xxx'}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <p className="text-xs text-gray-500 mt-1">
                Token is encrypted and stored securely
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Default Branch
              </label>
              <input
                type="text"
                value={formData.default_branch}
                onChange={(e) =>
                  setFormData({ ...formData, default_branch: e.target.value })
                }
                placeholder="main"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Agent Name
              </label>
              <input
                type="text"
                value={formData.agent_name}
                onChange={(e) =>
                  setFormData({ ...formData, agent_name: e.target.value })
                }
                placeholder="e.g., backend, mobile"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <p className="text-xs text-gray-500 mt-1">
                Maps to which AI agent handles this codebase
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Build Command
              </label>
              <input
                type="text"
                value={formData.build_command}
                onChange={(e) =>
                  setFormData({ ...formData, build_command: e.target.value })
                }
                placeholder="npm run build"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Test Command
              </label>
              <input
                type="text"
                value={formData.test_command}
                onChange={(e) =>
                  setFormData({ ...formData, test_command: e.target.value })
                }
                placeholder="npm test"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-4">
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
              className="flex-1 px-4 py-2 bg-primary text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? 'Saving...' : isEdit ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
