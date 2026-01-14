import { create } from 'zustand';
import { User, Project, Feature, Story, SystemLog } from '../types';

interface AppState {
  // Auth
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;

  // Projects
  projects: Project[];
  selectedProject: Project | null;
  setProjects: (projects: Project[]) => void;
  setSelectedProject: (project: Project | null) => void;

  // Features
  features: Feature[];
  selectedFeature: Feature | null;
  setFeatures: (features: Feature[]) => void;
  setSelectedFeature: (feature: Feature | null) => void;

  // Stories
  stories: Story[];
  setStories: (stories: Story[]) => void;
  updateStory: (story: Story) => void;

  // Logs
  logs: SystemLog[];
  addLog: (log: SystemLog) => void;
  clearLogs: () => void;

  // WebSocket
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  // Auth
  user: null,
  isAuthenticated: false,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  logout: () => {
    localStorage.removeItem('auth_token');
    set({ user: null, isAuthenticated: false });
  },

  // Projects
  projects: [],
  selectedProject: null,
  setProjects: (projects) => set({ projects }),
  setSelectedProject: (project) => set({ selectedProject: project }),

  // Features
  features: [],
  selectedFeature: null,
  setFeatures: (features) => set({ features }),
  setSelectedFeature: (feature) => set({ selectedFeature: feature }),

  // Stories
  stories: [],
  setStories: (stories) => set({ stories }),
  updateStory: (story) =>
    set((state) => ({
      stories: state.stories.map((s) => (s.id === story.id ? story : s)),
    })),

  // Logs
  logs: [],
  addLog: (log) =>
    set((state) => ({
      logs: [log, ...state.logs].slice(0, 500), // Keep last 500 logs
    })),
  clearLogs: () => set({ logs: [] }),

  // WebSocket
  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));
