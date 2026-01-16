import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Eye, EyeOff, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { SystemSetting, APIKeyTestResult } from '../types';

const API_BASE = '/api';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<APIKeyTestResult | null>(null);

  // Form values
  const [apiProvider, setApiProvider] = useState('claude');
  const [claudeApiKey, setClaudeApiKey] = useState('');
  const [manusApiKey, setManusApiKey] = useState('');
  const [showClaudeKey, setShowClaudeKey] = useState(false);
  const [showManusKey, setShowManusKey] = useState(false);

  const getToken = () => localStorage.getItem('auth_token');

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/settings`, {
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });
      if (!response.ok) throw new Error('Failed to fetch settings');
      const data = await response.json();
      setSettings(data.settings);

      // Set form values from settings
      const providerSetting = data.settings.find((s: SystemSetting) => s.key === 'api_provider');
      if (providerSetting?.value) {
        setApiProvider(providerSetting.value);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const saveSetting = async (key: string, value: string) => {
    const response = await fetch(`${API_BASE}/settings/${key}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({ value }),
    });
    if (!response.ok) throw new Error(`Failed to save ${key}`);
    return response.json();
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      // Save API provider
      await saveSetting('api_provider', apiProvider);

      // Save API keys if provided
      if (claudeApiKey) {
        await saveSetting('claude_api_key', claudeApiKey);
      }
      if (manusApiKey) {
        await saveSetting('manus_api_key', manusApiKey);
      }

      setSuccess('Settings saved successfully');
      setClaudeApiKey('');
      setManusApiKey('');
      fetchSettings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const testApiKey = async () => {
    const keyToTest = apiProvider === 'claude' ? claudeApiKey : manusApiKey;
    if (!keyToTest) {
      setError('Please enter an API key to test');
      return;
    }

    try {
      setTesting(true);
      setTestResult(null);
      setError(null);

      const response = await fetch(`${API_BASE}/settings/test-api-key`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          api_key: keyToTest,
          provider: apiProvider,
        }),
      });

      if (!response.ok) throw new Error('API test failed');
      const result: APIKeyTestResult = await response.json();
      setTestResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test API key');
    } finally {
      setTesting(false);
    }
  };

  const getSettingStatus = (key: string) => {
    const setting = settings.find((s) => s.key === key);
    return setting?.has_value;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <SettingsIcon className="w-8 h-8 text-primary" />
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <AlertCircle className="w-5 h-5" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">
            &times;
          </button>
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
          <CheckCircle className="w-5 h-5" />
          {success}
          <button onClick={() => setSuccess(null)} className="ml-auto text-green-500 hover:text-green-700">
            &times;
          </button>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-2">AI Provider Configuration</h2>
        <p className="text-gray-600 text-sm mb-6">
          Configure the AI provider and API keys for agent operations.
        </p>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">AI Provider</label>
          <select
            value={apiProvider}
            onChange={(e) => setApiProvider(e.target.value)}
            className="w-full md:w-96 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          >
            <option value="claude">Anthropic Claude {getSettingStatus('claude_api_key') && '(Configured)'}</option>
            <option value="manus">Manus AI {getSettingStatus('manus_api_key') && '(Configured)'}</option>
          </select>
        </div>

        <hr className="my-6" />

        <h3 className="text-lg font-semibold mb-2">API Keys</h3>
        <p className="text-gray-600 text-sm mb-4">
          Enter your API keys below. Keys are encrypted before being stored.
        </p>

        {/* Claude API Key */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <label className="text-sm font-medium text-gray-700">Claude API Key</label>
            {getSettingStatus('claude_api_key') ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                <CheckCircle className="w-3 h-3" />
                Configured
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">
                <AlertCircle className="w-3 h-3" />
                Not configured
              </span>
            )}
          </div>
          <div className="relative w-full md:w-96">
            <input
              type={showClaudeKey ? 'text' : 'password'}
              placeholder={getSettingStatus('claude_api_key') ? 'Enter new key to update' : 'sk-ant-...'}
              value={claudeApiKey}
              onChange={(e) => setClaudeApiKey(e.target.value)}
              className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
            <button
              type="button"
              onClick={() => setShowClaudeKey(!showClaudeKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
            >
              {showClaudeKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Manus API Key */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <label className="text-sm font-medium text-gray-700">Manus API Key</label>
            {getSettingStatus('manus_api_key') ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                <CheckCircle className="w-3 h-3" />
                Configured
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
                <AlertCircle className="w-3 h-3" />
                Not configured
              </span>
            )}
          </div>
          <div className="relative w-full md:w-96">
            <input
              type={showManusKey ? 'text' : 'password'}
              placeholder={getSettingStatus('manus_api_key') ? 'Enter new key to update' : 'Enter Manus API key'}
              value={manusApiKey}
              onChange={(e) => setManusApiKey(e.target.value)}
              className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
            <button
              type="button"
              onClick={() => setShowManusKey(!showManusKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
            >
              {showManusKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Test Result */}
        {testResult && (
          <div className={`mb-4 p-4 rounded-lg flex items-center gap-2 ${
            testResult.success
              ? 'bg-green-50 border border-green-200 text-green-700'
              : 'bg-red-50 border border-red-200 text-red-700'
          }`}>
            {testResult.success ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            {testResult.message}
            <button onClick={() => setTestResult(null)} className="ml-auto">
              &times;
            </button>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            onClick={testApiKey}
            disabled={testing || (!claudeApiKey && !manusApiKey)}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {testing && <Loader2 className="w-4 h-4 animate-spin" />}
            Test API Key
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Settings
          </button>
        </div>
      </div>

      {/* Current Settings Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Current Configuration</h2>
        <div className="divide-y divide-gray-200">
          {settings.map((setting) => (
            <div key={setting.key} className="py-3 flex justify-between items-center">
              <div>
                <p className="font-medium text-gray-900">{setting.key}</p>
                <p className="text-sm text-gray-500">{setting.description}</p>
              </div>
              <div className="flex items-center gap-2">
                {!setting.is_encrypted && setting.value && (
                  <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                    {setting.value}
                  </span>
                )}
                {setting.has_value ? (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-yellow-500" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Settings;
