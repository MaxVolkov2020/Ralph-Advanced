import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import apiClient from '../api/client';
import { DashboardStats } from '../types';
import { Activity, CheckCircle, Clock, XCircle } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
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
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-600">Failed to load dashboard stats</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
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
        />
        <StatCard
          title="Total Features"
          value={stats.total_features}
          subtitle={`${stats.active_features} in progress`}
          icon={<Activity className="w-6 h-6" />}
          color="purple"
        />
        <StatCard
          title="Completed Stories"
          value={stats.completed_stories}
          subtitle={`of ${stats.total_stories} total`}
          icon={<CheckCircle className="w-6 h-6" />}
          color="green"
        />
        <StatCard
          title="Pending Stories"
          value={stats.pending_stories}
          subtitle={`${stats.failed_stories} failed`}
          icon={<Clock className="w-6 h-6" />}
          color="yellow"
        />
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
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: number;
  subtitle: string;
  icon: React.ReactNode;
  color: 'blue' | 'purple' | 'green' | 'yellow';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, color }) => {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    purple: 'bg-purple-100 text-purple-600',
    green: 'bg-green-100 text-green-600',
    yellow: 'bg-yellow-100 text-yellow-600',
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>{icon}</div>
      </div>
    </div>
  );
};
