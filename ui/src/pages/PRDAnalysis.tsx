import React, { useState } from 'react';
import apiClient from '../api/client';
import {
  FileText,
  CheckCircle,
  XCircle,
  AlertTriangle,
  BarChart3,
  GitBranch,
  Play,
  Lightbulb,
  ArrowRight
} from 'lucide-react';
import {
  PRDAnalysisResult,
  PRDValidationResult,
  PRDEvaluationResult,
  PRDPlanningResult,
  ExecutionPhase
} from '../types';

export const PRDAnalysis: React.FC = () => {
  const [prdJson, setPrdJson] = useState('');
  const [projectId, setProjectId] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PRDAnalysisResult | null>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'validation' | 'evaluation' | 'planning'>('validation');

  const handleAnalyze = async () => {
    setError('');
    setLoading(true);
    setResult(null);

    try {
      // Validate JSON first
      JSON.parse(prdJson);

      const response = await apiClient.post('/prd/analyze', {
        project_id: projectId || null,
        prd_json: prdJson,
      });
      setResult(response.data);
    } catch (err: any) {
      if (err instanceof SyntaxError) {
        setError('Invalid JSON format. Please check your PRD structure.');
      } else {
        setError(err.response?.data?.detail || 'Analysis failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadSamplePRD = () => {
    const sample = {
      project: "Sample Project",
      feature: "User Authentication",
      branchName: "feature/user-auth",
      userStories: [
        {
          id: "US-001",
          title: "Implement user registration endpoint",
          description: "Create a REST API endpoint for user registration with email and password validation.",
          repo: "backend",
          priority: 1,
          dependencies: [],
          acceptanceCriteria: [
            "API accepts email and password",
            "Email must be unique",
            "Password must be at least 8 characters",
            "Returns JWT token on success"
          ]
        },
        {
          id: "US-002",
          title: "Create login endpoint",
          description: "Create a login endpoint that validates credentials and returns JWT token.",
          repo: "backend",
          priority: 1,
          dependencies: ["US-001"],
          acceptanceCriteria: [
            "API accepts email and password",
            "Returns JWT token on valid credentials",
            "Returns 401 on invalid credentials"
          ]
        },
        {
          id: "US-003",
          title: "Build registration form UI",
          description: "Create a responsive registration form with client-side validation.",
          repo: "frontend",
          priority: 2,
          dependencies: ["US-001"],
          acceptanceCriteria: [
            "Form has email and password fields",
            "Client-side validation for all fields",
            "Shows loading state during submission",
            "Handles API errors gracefully"
          ]
        }
      ]
    };
    setPrdJson(JSON.stringify(sample, null, 2));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">PRD Analysis</h1>
        <p className="text-gray-600 mt-1">
          Validate, evaluate, and plan your Product Requirements Document
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">PRD JSON Input</h2>
            <button
              onClick={loadSamplePRD}
              className="text-sm text-primary hover:underline"
            >
              Load Sample PRD
            </button>
          </div>

          <textarea
            value={prdJson}
            onChange={(e) => setPrdJson(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-mono text-sm"
            rows={20}
            placeholder='Paste your PRD JSON here...\n\n{\n  "userStories": [...]\n}'
          />

          <div className="mt-4 flex gap-4">
            <input
              type="number"
              value={projectId || ''}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : undefined)}
              placeholder="Project ID (optional)"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <button
              onClick={handleAnalyze}
              disabled={loading || !prdJson.trim()}
              className="flex items-center gap-2 px-6 py-2 bg-primary text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? (
                'Analyzing...'
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Analyze
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Results Section */}
        <div className="bg-white rounded-lg shadow">
          {!result ? (
            <div className="p-12 text-center">
              <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">
                Enter a PRD and click Analyze to see results
              </p>
            </div>
          ) : (
            <>
              {/* Tab Headers */}
              <div className="flex border-b border-gray-200">
                <TabButton
                  active={activeTab === 'validation'}
                  onClick={() => setActiveTab('validation')}
                  icon={result.validation.is_valid ? CheckCircle : XCircle}
                  iconColor={result.validation.is_valid ? 'text-green-500' : 'text-red-500'}
                  label="Validation"
                />
                <TabButton
                  active={activeTab === 'evaluation'}
                  onClick={() => setActiveTab('evaluation')}
                  icon={BarChart3}
                  iconColor="text-blue-500"
                  label={`Score: ${result.evaluation.score}`}
                />
                <TabButton
                  active={activeTab === 'planning'}
                  onClick={() => setActiveTab('planning')}
                  icon={GitBranch}
                  iconColor="text-purple-500"
                  label={`${result.planning.phases.length} Phases`}
                />
              </div>

              {/* Tab Content */}
              <div className="p-6">
                {activeTab === 'validation' && (
                  <ValidationView result={result.validation} />
                )}
                {activeTab === 'evaluation' && (
                  <EvaluationView result={result.evaluation} />
                )}
                {activeTab === 'planning' && (
                  <PlanningView result={result.planning} />
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.FC<{ className?: string }>;
  iconColor: string;
  label: string;
}

const TabButton: React.FC<TabButtonProps> = ({
  active,
  onClick,
  icon: Icon,
  iconColor,
  label,
}) => (
  <button
    onClick={onClick}
    className={`flex-1 flex items-center justify-center gap-2 py-3 border-b-2 transition-colors ${
      active
        ? 'border-primary text-primary'
        : 'border-transparent text-gray-500 hover:text-gray-700'
    }`}
  >
    <Icon className={`w-5 h-5 ${iconColor}`} />
    <span className="font-medium">{label}</span>
  </button>
);

const ValidationView: React.FC<{ result: PRDValidationResult }> = ({ result }) => (
  <div className="space-y-4">
    <div
      className={`p-4 rounded-lg flex items-center gap-3 ${
        result.is_valid ? 'bg-green-50' : 'bg-red-50'
      }`}
    >
      {result.is_valid ? (
        <>
          <CheckCircle className="w-8 h-8 text-green-500" />
          <div>
            <h3 className="font-semibold text-green-800">PRD is Valid</h3>
            <p className="text-sm text-green-600">
              No blocking errors found. Ready for execution.
            </p>
          </div>
        </>
      ) : (
        <>
          <XCircle className="w-8 h-8 text-red-500" />
          <div>
            <h3 className="font-semibold text-red-800">Validation Failed</h3>
            <p className="text-sm text-red-600">
              {result.errors.length} error(s) must be fixed before execution.
            </p>
          </div>
        </>
      )}
    </div>

    {result.errors.length > 0 && (
      <div>
        <h4 className="font-semibold text-red-800 mb-2">Errors</h4>
        <div className="space-y-2">
          {result.errors.map((error, idx) => (
            <div
              key={idx}
              className="p-3 bg-red-50 border border-red-200 rounded text-sm"
            >
              <div className="flex items-start gap-2">
                <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-mono text-xs text-red-600">
                    {error.path}
                  </span>
                  <p className="text-red-800">{error.message}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}

    {result.warnings.length > 0 && (
      <div>
        <h4 className="font-semibold text-yellow-800 mb-2">Warnings</h4>
        <div className="space-y-2">
          {result.warnings.map((warning, idx) => (
            <div
              key={idx}
              className="p-3 bg-yellow-50 border border-yellow-200 rounded text-sm"
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-mono text-xs text-yellow-600">
                    {warning.path}
                  </span>
                  <p className="text-yellow-800">{warning.message}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

const EvaluationView: React.FC<{ result: PRDEvaluationResult }> = ({ result }) => {
  const gradeColors: Record<string, string> = {
    A: 'bg-green-500',
    B: 'bg-blue-500',
    C: 'bg-yellow-500',
    D: 'bg-orange-500',
    F: 'bg-red-500',
  };

  return (
    <div className="space-y-6">
      {/* Score Display */}
      <div className="flex items-center gap-6">
        <div className="text-center">
          <div
            className={`w-20 h-20 rounded-full ${
              gradeColors[result.grade]
            } flex items-center justify-center`}
          >
            <span className="text-3xl font-bold text-white">{result.grade}</span>
          </div>
        </div>
        <div>
          <div className="text-4xl font-bold text-gray-900">{result.score}/100</div>
          <p className="text-gray-600">Overall Quality Score</p>
        </div>
      </div>

      {/* Breakdown */}
      <div className="space-y-3">
        <h4 className="font-semibold text-gray-700">Score Breakdown</h4>
        <ScoreBar label="Clarity" score={result.breakdown.clarity} weight={40} />
        <ScoreBar label="Dependencies" score={result.breakdown.dependencies} weight={30} />
        <ScoreBar label="Feasibility" score={result.breakdown.feasibility} weight={30} />
      </div>

      {/* Issues */}
      {result.issues.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-700 mb-3">
            Improvement Suggestions ({result.issues.length})
          </h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {result.issues.map((issue, idx) => (
              <div
                key={idx}
                className="p-3 bg-gray-50 border border-gray-200 rounded text-sm"
              >
                <div className="flex items-start gap-2">
                  <Lightbulb className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs px-2 py-0.5 bg-gray-200 rounded">
                        {issue.category}
                      </span>
                      {issue.story_id && (
                        <span className="text-xs text-gray-500">
                          {issue.story_id}
                        </span>
                      )}
                      <span className="text-xs text-red-500">-{issue.impact}pts</span>
                    </div>
                    <p className="text-gray-800">{issue.issue}</p>
                    <p className="text-gray-600 text-xs mt-1">
                      Suggestion: {issue.suggestion}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const ScoreBar: React.FC<{ label: string; score: number; weight: number }> = ({
  label,
  score,
  weight,
}) => {
  const getBarColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">
          {label} <span className="text-gray-400">({weight}%)</span>
        </span>
        <span className="font-medium">{score}/100</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${getBarColor(score)} transition-all`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
};

const PlanningView: React.FC<{ result: PRDPlanningResult }> = ({ result }) => (
  <div className="space-y-6">
    {/* Execution Order */}
    <div>
      <h4 className="font-semibold text-gray-700 mb-2">Execution Order</h4>
      <div className="flex flex-wrap items-center gap-2">
        {result.execution_order.map((storyId, idx) => (
          <React.Fragment key={storyId}>
            <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-medium">
              {storyId}
            </span>
            {idx < result.execution_order.length - 1 && (
              <ArrowRight className="w-4 h-4 text-gray-400" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>

    {/* Phases */}
    <div>
      <h4 className="font-semibold text-gray-700 mb-3">Execution Phases</h4>
      <div className="space-y-3">
        {result.phases.map((phase) => (
          <PhaseCard key={phase.phase_number} phase={phase} />
        ))}
      </div>
    </div>

    {/* Critical Path */}
    {result.critical_path.length > 0 && (
      <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
        <h4 className="font-semibold text-orange-800 mb-2">
          Critical Path (Length: {result.critical_path_length})
        </h4>
        <div className="flex flex-wrap items-center gap-2">
          {result.critical_path.map((storyId, idx) => (
            <React.Fragment key={storyId}>
              <span className="px-2 py-1 bg-orange-200 text-orange-800 rounded text-sm">
                {storyId}
              </span>
              {idx < result.critical_path.length - 1 && (
                <ArrowRight className="w-4 h-4 text-orange-400" />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    )}

    {/* Recommendations */}
    {result.recommendations.length > 0 && (
      <div>
        <h4 className="font-semibold text-gray-700 mb-2">Recommendations</h4>
        <div className="space-y-2">
          {result.recommendations.map((rec, idx) => (
            <div
              key={idx}
              className="p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800"
            >
              {rec}
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

const PhaseCard: React.FC<{ phase: ExecutionPhase }> = ({ phase }) => (
  <div className="p-4 border border-gray-200 rounded-lg">
    <div className="flex items-center justify-between mb-2">
      <span className="font-medium text-gray-900">Phase {phase.phase_number}</span>
      {phase.can_parallelize && (
        <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
          Can Parallelize
        </span>
      )}
    </div>
    <div className="flex flex-wrap gap-2 mb-2">
      {phase.stories.map((storyId) => (
        <span
          key={storyId}
          className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm"
        >
          {storyId}
        </span>
      ))}
    </div>
    <p className="text-sm text-gray-600">{phase.rationale}</p>
  </div>
);
