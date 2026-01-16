import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import apiClient from '../api/client';
import { DashboardStats } from '../types';
import { Activity, CheckCircle, Clock, XCircle, TrendingUp, AlertCircle } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
    // Refresh stats every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const response = await apiClient.get('/dashboard/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-600 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          Failed to load dashboard stats
        </div>
      </div>
    );
  }

  // Prepare chart data
  const storyStatusData = [
    { name: 'Completed', value: stats.completed_stories, color: '#10B981' },
    { name: 'In Progress', value: stats.in_progress_stories || 0, color: '#3B82F6' },
    { name: 'Pending', value: stats.pending_stories, color: '#F59E0B' },
    { name: 'Failed', value: stats.failed_stories, color: '#EF4444' },
  ].filter(item => item.value > 0);

  const projectActivityData = stats.recent_projects?.map((p: any) => ({
    name: p.name.length > 15 ? p.name.substring(0, 15) + '...' : p.name,
    stories: p.total_stories || 0,
    completed: p.completed_stories || 0,
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">System overview and statistics</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Projects"
          value={stats.total_projects}
          subtitle={`${stats.active_projects} active`}
          icon={<Activity className="w-6 h-6" />}
          color="blue"
          trend={stats.projects_trend}
        />
        <StatCard
          title="Total Features"
          value={stats.total_features}
          subtitle={`${stats.active_features} in progress`}
          icon={<Activity className="w-6 h-6" />}
          color="purple"
          trend={stats.features_trend}
        />
        <StatCard
          title="Completed Stories"
          value={stats.completed_stories}
          subtitle={`of ${stats.total_stories} total`}
          icon={<CheckCircle className="w-6 h-6" />}
          color="green"
          trend={stats.completion_trend}
        />
        <StatCard
          title="Pending Stories"
          value={stats.pending_stories}
          subtitle={`${stats.failed_stories} failed`}
          icon={<Clock className="w-6 h-6" />}
          color="yellow"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Story Status Distribution */}
        {storyStatusData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Story Status Distribution</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={storyStatusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {storyStatusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {storyStatusData.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                  <span className="text-sm text-gray-600">{item.name}: {item.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Project Activity */}
        {projectActivityData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Project Activity</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={projectActivityData}>
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="stories" fill="#3B82F6" name="Total Stories" />
                <Bar dataKey="completed" fill="#10B981" name="Completed" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      {stats.total_stories > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Overall Progress</h2>
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-gray-600">
              <span>Stories Completed</span>
              <span>
                {stats.completed_stories} / {stats.total_stories} (
                {Math.round((stats.completed_stories / stats.total_stories) * 100)}%)
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-green-500 h-4 rounded-full transition-all duration-300"
                style={{
                  width: `${(stats.completed_stories / stats.total_stories) * 100}%`,
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {stats.total_projects === 0 && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Activity className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Welcome to Ralph-Advanced!</h3>
          <p className="text-gray-600 mb-4">
            Get started by creating your first project. Ralph-Advanced will autonomously develop features using specialized AI agents.
          </p>
          <a
            href="/projects"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors"
          >
            Create Your First Project
          </a>
        </div>
      )}
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: number;
  subtitle: string;
  icon: React.ReactNode;
  color: 'blue' | 'purple' | 'green' | 'yellow';
  trend?: number;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, color, trend }) => {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    purple: 'bg-purple-100 text-purple-600',
    green: 'bg-green-100 text-green-600',
    yellow: 'bg-yellow-100 text-yellow-600',
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 font-medium">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          {trend !== undefined && trend !== 0 && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
              <TrendingUp className={`w-4 h-4 ${trend < 0 ? 'rotate-180' : ''}`} />
              <span>{Math.abs(trend)}% from last week</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>{icon}</div>
      </div>
    </div>
  );
};
